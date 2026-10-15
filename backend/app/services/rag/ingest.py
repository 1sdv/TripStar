"""RAG 知识库灌入管线：把外部获取的游记/攻略文本入库供 Agent 检索。

设计要点（决定了检索能不能命中，比脚本本身更重要）
------------------------------------------------
1. **`destination` 必须规范成「省+市」原子值**（如 `云南大理`）。
   检索侧的按城市过滤是对 `destination` 做元数据匹配（`resolve_destinations`），
   写错或写杂（`大理市` / `云南-大理` / `大理白族自治州`）会导致该城市**永远检索不到**。
   因此本模块用 `云南*` 白名单归一化，不接受任意字符串。

2. **切块参数可与现有库不同**。现有 751 条是「100 字/25 字重叠」的历史切块，
   偏碎（常从句子中间断开）。新灌数据用更大的块更利于 LLM 提纯，
   只要 embedding 模型一致（BGE-M3），两者可以在同一 collection 共存。

3. **`post_id` 必须是整数且每篇唯一**。检索结果按 `post_id` 去重
   （`retrieve()` 里 `int(meta.get("post_id") or 0)`），若为 0 会退化成按 chunk 去重，
   同一篇游记会重复占坑。

4. **幂等**：chunk id 为 `{post_id}-{i}`，覆盖式重灌前先按 `post_id` 删旧 chunk，
   避免文档变短后残留旧块。

5. **灌完必须清目的地缓存**，否则运行中的进程看不到新城市。

输入格式
--------
目录下三类文件任选：
* `*.md`  —— 带 frontmatter（推荐，手工整理）
    ```
    ---
    title: 大理环洱海骑行攻略
    destination: 大理
    source_url: https://example.com/xxx
    like_count: 210
    ---
    正文……
    ```
* `*.txt` —— 纯文本，无 title/destination 时按内容自动判定
* `*.jsonl` —— 爬虫直出，每行一个对象，键同 frontmatter

用法
----
    python backend/scripts/ingest_yunnan.py <目录> [--dry-run] [--use-llm] [--replace]
"""

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ---------- 云南目的地白名单：库内统一命名 = 省 + 市/州 ----------
_YUNNAN_CITIES = [
    "昆明", "大理", "丽江", "香格里拉", "迪庆", "西双版纳", "腾冲", "保山",
    "曲靖", "玉溪", "昭通", "普洱", "临沧", "楚雄", "红河", "文山",
    "怒江", "德宏", "剑川", "建水", "元阳", "泸沽湖", "德钦", "普者黑",
    "石屏", "通海", "抚仙湖", "沙溪", "和顺", "坝美",
]

# 常见别名 → 白名单标准名（检索的宽松匹配也能兜住一部分，但写入时就要规范化）
_ALIAS = {
    "大理市": "大理", "大理白族自治州": "大理", "大理古城": "大理",
    "丽江市": "丽江", "丽江古城": "丽江",
    "昆明市": "昆明",
    "香格里拉市": "香格里拉", "香格里拉县": "香格里拉",
    "西双版纳傣族自治州": "西双版纳", "景洪": "西双版纳", "勐海": "西双版纳", "勐腊": "西双版纳",
    "腾冲市": "腾冲", "腾越": "腾冲",
    "迪庆藏族自治州": "迪庆", "中甸": "香格里拉",
    "泸沽湖镇": "泸沽湖", "宁蒗": "泸沽湖",
    "元阳县": "元阳", "建水县": "建水", "剑川县": "剑川", "沙溪古镇": "沙溪",
    "普者黑景区": "普者黑", "抚仙湖景区": "抚仙湖", "和顺古镇": "和顺", "坝美村": "坝美",
    "红河哈尼族彝族自治州": "红河", "文山壮族苗族自治州": "文山",
    "楚雄彝族自治州": "楚雄", "德宏傣族景颇族自治州": "德宏",
    "怒江傈僳族自治州": "怒江", "玉溪市": "玉溪", "曲靖市": "曲靖",
    "保山市": "保山", "昭通市": "昭通", "普洱市": "普洱", "临沧市": "临沧",
}

# 切块参数（新数据用更大的块，减少句子被拦腰截断）
CHUNK_SIZE = 400
CHUNK_OVERLAP = 80
# 标题 + 正文太短则丢弃，避免灌入噪声
MIN_CONTENT_LENGTH = 60
EMBED_BATCH_SIZE = 16


@dataclass
class IngestDoc:
    """一篇待入库的文档。"""
    title: str
    content: str
    destination: str
    post_id: int
    source_url: str = ""
    like_count: int = 0
    source_file: str = ""
    warnings: List[str] = field(default_factory=list)


def normalize_destination(raw: str, content: str = "", title: str = "") -> Tuple[str, Optional[str]]:
    """归一化目的地到「云南X」标准名。

    Returns:
        (标准目的地, 警告信息或 None)；无法归入云南时返回 ("", 原因)。
    """
    text = re.sub(r"[\s　]+", "", str(raw or ""))
    text = text.replace("云南省", "").replace("云南-", "").replace("-", "")
    text = text.replace("中国", "")

    if not text:
        # 从标题与正文前 200 字里找**最先出现**的云南城市。
        # 注意必须按「首次出现位置」而非「名称长度」来选：正文常出现
        # 「建水比大理安静」这种对比句，若按长度排序会把大理误判成本篇目的地。
        haystack = f"{title}{content[:200]}"
        positions = []
        for city in _YUNNAN_CITIES:
            pos = haystack.find(city)
            if pos >= 0:
                # 同位置时优先更长的名称，避免「大理」抢走「大理古城」
                positions.append((pos, -len(city), city))
        if positions:
            positions.sort()
            city = positions[0][2]
            return f"云南{_ALIAS.get(city, city)}", f"目的地缺失，按内容推断为 {city}"
        return "", "无法判定目的地（未在云南白名单内命中）"

    canonical = _ALIAS.get(text, text)
    for city in _YUNNAN_CITIES:
        if canonical == city or canonical == _ALIAS.get(city):
            return f"云南{city}", None

    # 允许已经是「云南大理」这种形态
    if text.startswith("云南"):
        bare = text[2:]
        if bare in _YUNNAN_CITIES:
            return f"云南{bare}", None

    return "", f"目的地「{raw}」不属于云南白名单，已跳过（避免污染按城市过滤）"


def make_post_id(*candidates: str) -> int:
    """由稳定标识生成正整数 post_id（检索按 post_id 去重，必须唯一且非 0）。"""
    seed = next((str(c).strip() for c in candidates if str(c or "").strip()), "")
    if not seed:
        raise ValueError("post_id 生成失败：缺少任何可用标识")
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    # 取 12 位十六进制 → 正整数，避开 0
    return int(digest[:12], 16)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """固定长度切块，相邻块重叠 overlap 字（与既有 chunk_text 同构）。"""
    text = (text or "").strip()
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunks.append(text[start:end])
        if end == length:
            break
        start = end - overlap
    return chunks


# ---------- 解析 ----------

def _parse_frontmatter(raw: str) -> Tuple[Dict[str, Any], str]:
    """解析 `---` 包裹的 frontmatter，返回 (元数据, 正文)。"""
    if not raw.lstrip().startswith("---"):
        return {}, raw
    lines = raw.lstrip().splitlines()
    meta: Dict[str, Any] = {}
    body_start = 0
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body_start = index + 1
            break
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"').strip("'")
    else:
        return {}, raw
    return meta, "\n".join(lines[body_start:])


def parse_markdown(path: Path) -> Optional[IngestDoc]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    meta, body = _parse_frontmatter(raw)

    title = str(meta.get("title") or "").strip()
    if not title:
        # 退而取第一个一级标题
        for line in body.splitlines():
            if line.strip().startswith("#"):
                title = line.lstrip("#").strip()
                break
    title = title or path.stem

    content = body.strip()
    destination, warn = normalize_destination(
        str(meta.get("destination") or ""), content=content, title=title
    )
    doc = IngestDoc(
        title=title,
        content=content,
        destination=destination,
        post_id=make_post_id(meta.get("source_id", ""), meta.get("source_url", ""), title),
        source_url=str(meta.get("source_url") or ""),
        like_count=int(meta.get("like_count") or 0),
        source_file=str(path),
    )
    if warn:
        doc.warnings.append(warn)
    return doc


def parse_txt(path: Path) -> Optional[IngestDoc]:
    content = path.read_text(encoding="utf-8", errors="replace").strip()
    title = path.stem
    destination, warn = normalize_destination("", content=content, title=title)
    doc = IngestDoc(
        title=title,
        content=content,
        destination=destination,
        post_id=make_post_id(str(path.resolve())),
        source_file=str(path),
    )
    if warn:
        doc.warnings.append(warn)
    return doc


def parse_jsonl(path: Path) -> List[IngestDoc]:
    docs: List[IngestDoc] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"  ⚠️ {path.name}:{line_no} JSON 解析失败，跳过: {e}")
            continue

        title = str(obj.get("title") or obj.get("name") or "").strip() or f"{path.stem}-{line_no}"
        content = str(obj.get("content") or obj.get("text") or obj.get("desc") or "").strip()
        destination, warn = normalize_destination(
            str(obj.get("destination") or obj.get("city") or ""), content=content, title=title
        )
        doc = IngestDoc(
            title=title,
            content=content,
            destination=destination,
            post_id=make_post_id(obj.get("post_id", ""), obj.get("id", ""),
                                 obj.get("url", ""), f"{path.name}:{line_no}"),
            source_url=str(obj.get("url") or obj.get("source_url") or ""),
            like_count=int(obj.get("like_count") or obj.get("likeCount") or 0),
            source_file=f"{path.name}:{line_no}",
        )
        if warn:
            doc.warnings.append(warn)
        docs.append(doc)
    return docs


def load_documents(source: Path) -> List[IngestDoc]:
    """加载目录（或单个文件）下的全部候选文档。"""
    files: List[Path] = []
    if source.is_file():
        files = [source]
    else:
        files = sorted(
            p for p in source.rglob("*")
            if p.is_file() and p.suffix.lower() in {".md", ".markdown", ".txt", ".jsonl"}
        )

    docs: List[IngestDoc] = []
    for path in files:
        suffix = path.suffix.lower()
        try:
            if suffix == ".jsonl":
                docs.extend(parse_jsonl(path))
            elif suffix in {".md", ".markdown"}:
                doc = parse_markdown(path)
                if doc:
                    docs.append(doc)
            else:
                doc = parse_txt(path)
                if doc:
                    docs.append(doc)
        except Exception as e:
            print(f"  ⚠️ 解析 {path.name} 失败: {type(e).__name__}: {e}")
    return docs


# ---------- 写入 ----------

def ingest_documents(
    docs: List[IngestDoc],
    *,
    dry_run: bool = False,
    replace: bool = True,
) -> Dict[str, int]:
    """切块 → 向量化 → 写入 ChromaDB。

    Args:
        dry_run: 只做解析与统计，不调 embedding、不写库
        replace: True 时先删除同 post_id 的旧 chunk（覆盖式重灌，避免残留）
    """
    from app.services.rag.embedding import embed_texts
    from app.services.rag.retriever import COLLECTION_POSTS, reset_destination_cache
    from app.services.rag.vectorstore import get_store

    stats = {"docs": 0, "skipped": 0, "chunks": 0, "failed": 0}
    store = get_store() if not dry_run else None

    # 收集全部 chunk，便于批量向量化
    pending: List[Tuple[IngestDoc, List[str]]] = []
    for doc in docs:
        if not doc.destination:
            stats["skipped"] += 1
            continue
        if len(doc.content) < MIN_CONTENT_LENGTH:
            print(f"  ⚠️ 跳过过短文档《{doc.title}》（{len(doc.content)} 字）")
            stats["skipped"] += 1
            continue
        chunks = chunk_text(doc.content)
        if not chunks:
            stats["skipped"] += 1
            continue
        pending.append((doc, chunks))

    if dry_run:
        stats["docs"] = len(pending)
        stats["chunks"] = sum(len(c) for _, c in pending)
        return stats

    flat_texts: List[str] = []
    owners: List[Tuple[IngestDoc, int]] = []  # (doc, chunk_index)
    for doc, chunks in pending:
        for index, chunk in enumerate(chunks):
            flat_texts.append(chunk)
            owners.append((doc, index))

    if not flat_texts:
        return stats

    print(f"\n🧮 共 {len(flat_texts)} 个 chunk 待向量化（模型 {_embedding_model_name()}）...")
    embeddings: List[List[float]] = []
    for start in range(0, len(flat_texts), EMBED_BATCH_SIZE):
        batch = flat_texts[start:start + EMBED_BATCH_SIZE]
        try:
            embeddings.extend(embed_texts(batch))
        except Exception as e:
            print(f"  ❌ 向量化失败（batch {start}-{start + len(batch)}）: {type(e).__name__}: {e}")
            stats["failed"] += len(batch)
            # 用零向量占位会让检索结果失真，因此这批直接跳过
            embeddings.extend([None] * len(batch))  # type: ignore[list-item]
        done = min(start + EMBED_BATCH_SIZE, len(flat_texts))
        print(f"  向量化进度 {done}/{len(flat_texts)}", end="\r")
    print()

    # 按文档分组写入（先删旧块，再 upsert 新块）
    by_doc: Dict[int, List[int]] = {}
    for flat_index, (doc, _) in enumerate(owners):
        by_doc.setdefault(doc.post_id, []).append(flat_index)

    doc_by_id = {doc.post_id: doc for doc, _ in pending}
    for post_id, flat_indices in by_doc.items():
        doc = doc_by_id[post_id]
        valid = [i for i in flat_indices if embeddings[i] is not None]
        if not valid:
            stats["failed"] += 1
            continue

        if replace:
            removed = store.delete_by_post_id(post_id, COLLECTION_POSTS)
            if removed:
                print(f"  ♻️ 覆盖重灌《{doc.title}》：清除旧 chunk {removed} 个")

        ids = [f"{post_id}-{owners[i][1]}" for i in valid]
        metadatas = [
            {
                "post_id": post_id,
                "title": doc.title,
                "destination": doc.destination,
                "like_count": doc.like_count,
                "source_url": doc.source_url,
            }
            for i in valid
        ]
        store.upsert_chunks(
            ids=ids,
            embeddings=[embeddings[i] for i in valid],  # type: ignore[misc]
            documents=[flat_texts[i] for i in valid],
            metadatas=metadatas,
            collection=COLLECTION_POSTS,
        )
        stats["docs"] += 1
        stats["chunks"] += len(valid)

    # 关键：清掉目的地缓存，否则运行中的进程看不到新城市
    reset_destination_cache()
    return stats


def _embedding_model_name() -> str:
    try:
        from app.config import get_settings

        return get_settings().embedding_model
    except Exception:
        return "?"
