"""混合检索：向量 + 关键词 RRF 融合（社区热度破平局）→ rerank 精排 → 去重 → 权威兜底。

算法与原「觅途」项目 rag_service 保持一致，仅做 TripStar 适配：
- 关键词检索改为「Chroma where_document 下推筛选 + 2-gram 命中打分」，
  不再把全量 chunk 拉进内存；
- 新增目的地过滤：多城市场景下只检索当前城市的游记，避免张冠李戴；
- 新增 retrieve_notes_for_city()，把检索结果格式化为可直接拼进 Planner Prompt 的文本块。

RAG 是增强项：库为空 / 未配 Key / rerank 失败都会降级或返回空，绝不抛出到主流程。
"""

import math
import re
import threading
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ...config import get_settings
from .embedding import embed_text
from .rerank import rerank as do_rerank
from .vectorstore import (
    COLLECTION_AUTHORITY,
    COLLECTION_POSTS,
    get_store,
)

# RRF 融合常数：rank 越大权重衰减越缓
RRF_K = 60
# 精排候选池倍数（相对 top_k）
RERANK_CANDIDATE_MULT = 4
# 热度平局打破粒度：< 1 个排名差，保证相关性主导、热度只破平局
HEAT_BUCKET = 0.0002
# 关键词检索召回上限与 where_document 预筛上限
KEYWORD_RECALL_LIMIT = 40
LITERAL_PREFILTER_LIMIT = 5000
# 目的地映射缓存（库内容在运行期不变，缓存可安全复用）
_DEST_MAP_CACHE: Dict[str, Dict[str, List[str]]] = {}
_DEST_MAP_LOCK = threading.Lock()

# 目的地名里需要忽略的行政区后缀，用于「重庆」↔「重庆市区」之类的宽松匹配
_ADMIN_SUFFIXES = (
    "特别行政区", "自治区", "自治州", "自治县", "地区", "盟",
    "省", "市", "县", "区", "州",
)


def _normalize_name(value: str) -> str:
    """去掉空白与行政区后缀，便于城市名与库内目的地做宽松比较。"""
    text = re.sub(r"\s+", "", str(value or ""))
    for suffix in _ADMIN_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
    return text


def reset_destination_cache() -> None:
    """清空目的地的进程内缓存。

    必须在「运行期往库里新增数据」之后调用，否则新写入的目的地不会进入
    `resolve_destinations` 的映射，`retrieve(city=...)` 会一直过滤不到它们，
    看起来就像"灌进去了但检索不到"。灌库脚本收尾会自动调用。
    """
    with _DEST_MAP_LOCK:
        _DEST_MAP_CACHE.clear()


def _destination_map(collection: str) -> Dict[str, List[str]]:
    """{归一化目的地: [库内原始目的地形态...]}，带进程内缓存。"""
    with _DEST_MAP_LOCK:
        cached = _DEST_MAP_CACHE.get(collection)
    if cached is not None:
        return cached

    mapping: Dict[str, List[str]] = {}
    try:
        for raw in get_store().destinations(collection):
            mapping.setdefault(_normalize_name(raw), []).append(raw)
    except Exception as exc:  # 库不可用时不应阻塞检索
        print(f"⚠️ [rag] 读取目的地列表失败: {type(exc).__name__}: {exc}")
        mapping = {}

    with _DEST_MAP_LOCK:
        _DEST_MAP_CACHE[collection] = mapping
    return mapping


def resolve_destinations(city: str) -> List[str]:
    """把城市名匹配到库内真实的目的地取值（如 "大理" → ["云南大理"]）。"""
    target = _normalize_name(city)
    if not target:
        return []

    mapping = _destination_map(COLLECTION_POSTS)
    matched: List[str] = list(mapping.get(target, []))

    # 宽松匹配：库内目的地可能带省份前缀（云南大理）或后缀（重庆市区）
    for norm, raws in mapping.items():
        if not norm or norm == target:
            continue
        if norm.endswith(target) or target.endswith(norm):
            for raw in raws:
                if raw not in matched:
                    matched.append(raw)
    return matched


def _keyword_score(question: str, chunk_text: str) -> int:
    """关键词命中分：问题 2-gram 在 chunk 中出现的个数（字面重叠近似关键词匹配）。"""
    text = re.sub(r"[^\w\u4e00-\u9fff]", "", question)
    grams = {text[i : i + 2] for i in range(len(text) - 1)}
    return sum(1 for g in grams if g in chunk_text)


def _vector_search(
    question: str,
    top_k: int,
    collection: str = COLLECTION_POSTS,
    filter_destinations: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """向量检索，按相似度降序返回 [{id, doc, meta, distance}]。"""
    query_embedding = embed_text(question)
    result = get_store().search(
        query_embedding,
        top_k=top_k,
        collection=collection,
        filter_destinations=filter_destinations,
    )
    ids = (result.get("ids") or [[]])[0]
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    dists = (result.get("distances") or [[]])[0]
    return [
        {"id": ids[i], "doc": docs[i], "meta": metas[i], "distance": dists[i]}
        for i in range(len(docs))
    ]


def _literal_prefilter(question: str, filter_destinations: Optional[List[str]]) -> List[Dict[str, Any]]:
    """用 2-gram 里的字面片段向 Chroma 下推过滤，缩小关键词打分范围。

    where_document 只支持 $contains，所以挑几个最长（最具体）的 2-gram 分别预筛后合并；
    任何异常都退回全量（小库场景完全可接受）。
    """
    text = re.sub(r"[^\w\u4e00-\u9fff]", "", question)
    grams = sorted({text[i : i + 2] for i in range(len(text) - 1)}, key=len, reverse=True)[:6]

    store = get_store()
    merged: Dict[str, Dict[str, Any]] = {}
    for gram in grams:
        try:
            found = store.search_document(
                gram,
                limit=LITERAL_PREFILTER_LIMIT,
                filter_destinations=filter_destinations,
            )
        except Exception as exc:
            print(f"⚠️ [rag] 字面预筛失败，退回全量关键词检索: {type(exc).__name__}: {exc}")
            return store.get_all(COLLECTION_POSTS, filter_destinations=filter_destinations)
        for item in found:
            merged.setdefault(item["id"], item)
    return list(merged.values())


def _keyword_search(question: str, top_k: int, filter_destinations: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """关键词检索：候选池按 2-gram 命中分降序，返回 [{id, doc, meta, score}]。"""
    scored: List[Dict[str, Any]] = []
    for item in _literal_prefilter(question, filter_destinations):
        meta = item.get("meta") or {}
        text = f"{meta.get('title', '')} {item.get('doc', '')}"
        score = _keyword_score(question, text)
        if score > 0:
            scored.append({"id": item["id"], "doc": item["doc"], "meta": meta, "score": score})
    scored.sort(key=lambda x: -x["score"])
    return scored[:top_k]


def _heat_value(meta: Dict[str, Any]) -> float:
    """候选的热度原始值：游记用 like_count，权威条目用 heat。"""
    for key in ("like_count", "heat"):
        try:
            value = float(meta.get(key) or 0)
        except (TypeError, ValueError):
            value = 0.0
        if value > 0:
            return value
    return 0.0


def _heat_factor(items: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    """候选池内热度归一化：log1p(heat)/log1p(max_heat)，返回 {id: 值}。"""
    items = list(items)
    max_heat = max((_heat_value(item.get("meta") or {}) for item in items), default=0.0)
    if max_heat <= 0:
        return {}
    denom = math.log1p(max_heat)
    return {
        item["id"]: math.log1p(_heat_value(item.get("meta") or {})) / denom
        for item in items
    }


def _rrf_fuse(
    vector_items: List[Dict[str, Any]],
    keyword_items: List[Dict[str, Any]],
    top_k: int,
    use_heat: bool = True,
) -> List[Dict[str, Any]]:
    """RRF 融合：score = Σ 1/(k + rank)，两路排名互补。

    热度只用于破平局：RRF 分量化到 HEAT_BUCKET 粒度后按桶排序，桶内比热度，
    保证相关性主导排序，热度仅在相关性相近时优先热门游记。
    """
    scores: Dict[str, float] = {}
    meta_map: Dict[str, Dict[str, Any]] = {}
    for rank, item in enumerate(vector_items):
        cid = item["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
        meta_map[cid] = {"doc": item["doc"], "meta": item["meta"]}
    for rank, item in enumerate(keyword_items):
        cid = item["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
        meta_map[cid] = {"doc": item["doc"], "meta": item["meta"]}

    ranked = sorted(scores.items(), key=lambda x: -x[1])
    fused = [
        {"id": cid, "doc": meta_map[cid]["doc"], "meta": meta_map[cid]["meta"], "rrf": score}
        for cid, score in ranked[:top_k]
    ]
    if use_heat:
        factors = _heat_factor(fused)
        if factors:
            fused.sort(
                key=lambda item: (
                    -round(item["rrf"] / HEAT_BUCKET) * HEAT_BUCKET,
                    -factors.get(item["id"], 0.0),
                )
            )
    return fused


def _rerank_items(question: str, candidates: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    """精排收窄到 top_k；rerank 失败降级返回 RRF 结果。"""
    try:
        docs = [f"{item['meta'].get('title', '')} {item['doc']}" for item in candidates]
        order = do_rerank(question, docs, top_n=top_k)
        ranked = [candidates[i] for i in order if 0 <= i < len(candidates)]
        # 服务端可能只返回部分下标，补齐剩余候选避免结果变少
        taken = {id(item) for item in ranked}
        ranked.extend(item for item in candidates if id(item) not in taken)
        return ranked[:top_k]
    except Exception as exc:
        print(f"⚠️ [rag] rerank 失败，降级用 RRF 融合结果: {type(exc).__name__}: {exc}")
        return candidates[:top_k]


def retrieve(
    question: str,
    top_k: int = 5,
    *,
    city: str = "",
    use_rerank: Optional[bool] = None,
    use_heat: bool = True,
    use_authority: bool = True,
    collection: str = COLLECTION_POSTS,
    candidate_mult: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """混合检索主入口。

    流程：目的地过滤 → 向量 + 关键词 RRF 融合（热度破平局）粗召回
    → 可选 rerank 精排 → 按 post_id 去重 → UGC 不足 top_k 时权威底库兜底。

    Args:
        city: 非空时只检索该城市（宽松匹配库内目的地）；多城市行程必须逐城传入。
        candidate_mult: 粗召回候选池倍数（默认取配置 rag_candidate_mult）。
            「RAG 当数据源」挖景点时可调大，以提高候选覆盖。

    Returns:
        [{post_id, title, destination, snippet, is_authority}]，检索不可用时返回 []。
    """
    settings = get_settings()
    if use_rerank is None:
        use_rerank = settings.rerank_enabled

    destinations = resolve_destinations(city) if city else []
    mult = candidate_mult or settings.rag_candidate_mult or RERANK_CANDIDATE_MULT
    candidate_k = max(top_k, top_k * max(1, mult))

    vector_items = _vector_search(question, candidate_k, collection=collection, filter_destinations=destinations or None)
    keyword_items = _keyword_search(question, candidate_k, filter_destinations=destinations or None)
    fused = _rrf_fuse(vector_items, keyword_items, candidate_k, use_heat=use_heat)

    fused = _rerank_items(question, fused, top_k) if use_rerank else fused[:top_k]

    results: List[Dict[str, Any]] = []
    seen_post_ids: set = set()
    for item in fused:
        meta = item.get("meta") or {}
        try:
            post_id = int(meta.get("post_id") or 0)
        except (TypeError, ValueError):
            post_id = 0
        key = post_id if post_id else item["id"]
        if key in seen_post_ids:
            continue
        seen_post_ids.add(key)
        results.append(
            {
                "post_id": post_id,
                "title": str(meta.get("title") or ""),
                "destination": str(meta.get("destination") or ""),
                "snippet": str(item.get("doc") or ""),
                "is_authority": False,
            }
        )

    # 权威底库兜底：UGC 结果不足时用景点/路线知识补位（冷启动 / 冷门城市）
    if use_authority and len(results) < top_k:
        missing = top_k - len(results)
        try:
            authority_items = _vector_search(
                question, missing, collection=COLLECTION_AUTHORITY, filter_destinations=destinations or None
            )
        except Exception as exc:
            print(f"⚠️ [rag] 权威底库兜底不可用，跳过: {type(exc).__name__}: {exc}")
            authority_items = []

        for item in authority_items:
            meta = item.get("meta") or {}
            name = str(meta.get("name") or "")
            if not name:
                continue
            key = f"auth-{meta.get('type', '')}-{meta.get('source_id', '')}"
            if key in seen_post_ids:
                continue
            seen_post_ids.add(key)
            results.append(
                {
                    "post_id": 0,
                    "title": f"{name}（权威底库）",
                    "destination": str(meta.get("destination") or ""),
                    "snippet": str(item.get("doc") or ""),
                    "is_authority": True,
                }
            )
            if len(results) >= top_k:
                break

    return results[:top_k]


def rag_available() -> Tuple[bool, str]:
    """RAG 可用性自检，返回 (是否可用, 原因)。用于启动日志与诊断接口。"""
    settings = get_settings()
    if not settings.embedding_api_key:
        return False, "未配置 EMBEDDING_API_KEY"
    try:
        count = get_store().count(COLLECTION_POSTS)
    except Exception as exc:
        return False, f"知识库打开失败: {type(exc).__name__}: {exc}"
    if count <= 0:
        return False, "知识库为空（posts collection 无数据）"
    return True, f"可用（posts={count}, embedding={settings.embedding_model}）"


def collect_city_notes(
    city: str,
    preferences: Optional[List[str]] = None,
    free_text: str = "",
    top_k: Optional[int] = None,
    candidate_mult: Optional[int] = None,
) -> str:
    """检索某城市的游记并拼接为纯文本（不带格式化抬头），供 LLM 二次提纯。

    与 retrieve_notes_for_city 的区别：那个产出「给人看/给 Planner 读」的格式化块，
    这个产出「给提纯模型读」的原始片段拼接。检索不可用 / 无命中返回空字符串。
    """
    settings = get_settings()
    top_k = top_k or settings.rag_top_k

    keyword = " ".join([p for p in (preferences or []) if p]).strip()
    question = f"{city} {keyword} 旅游攻略 游记 景点 避坑".strip()
    if free_text:
        question = f"{question} {free_text.strip()}"

    results = retrieve(question, top_k=top_k, city=city, candidate_mult=candidate_mult)
    if not results:
        return ""

    blocks = []
    for item in results:
        title = item["title"] or "（无标题）"
        snippet = re.sub(r"\s+", " ", item["snippet"]).strip()
        blocks.append(f"《{title}》{snippet}")
    return "\n".join(blocks)


def retrieve_notes_for_city(
    city: str,
    preferences: Optional[List[str]] = None,
    free_text: str = "",
    top_k: Optional[int] = None,
) -> str:
    """检索某城市的游记并格式化为可注入 Planner Prompt 的文本块。

    检索不可用 / 无命中时返回空字符串，调用方保持原流程不变。
    """
    settings = get_settings()
    top_k = top_k or settings.rag_top_k

    keyword = " ".join([p for p in (preferences or []) if p]).strip()
    question = f"{city} {keyword} 旅游攻略 游记 景点 避坑".strip()
    if free_text:
        question = f"{question} {free_text.strip()}"

    results = retrieve(question, top_k=top_k, city=city)
    if not results:
        return ""

    lines = [
        f"【{city} 真实游记检索结果】（来自社区游记/权威底库，可作为避坑、预约、游览时长的事实依据）"
    ]
    for index, item in enumerate(results, start=1):
        title = item["title"] or "（无标题）"
        snippet = re.sub(r"\s+", " ", item["snippet"]).strip()
        if len(snippet) > 220:
            snippet = snippet[:220] + "…"
        lines.append(f"{index}. 《{title}》{snippet}")

    return "\n".join(lines)
