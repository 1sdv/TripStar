"""云南知识库灌入 CLI。

用法：
    # 1) 先干跑，只解析不写库（强烈建议先跑这一步）
    python backend/scripts/ingest_yunnan.py <素材目录> --dry-run

    # 2) 正式灌入
    python backend/scripts/ingest_yunnan.py <素材目录>

    # 3) 追加模式（不删同 post_id 旧块，一般不用）
    python backend/scripts/ingest_yunnan.py <素材目录> --no-replace

支持的素材格式见 app/services/rag/ingest.py 的模块文档。
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.rag.ingest import ingest_documents, load_documents


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}

    if not args:
        print(__doc__)
        return 2

    source = Path(args[0])
    if not source.exists():
        print(f"❌ 路径不存在: {source}")
        return 2

    dry_run = "--dry-run" in flags
    replace = "--no-replace" not in flags

    print("=" * 76)
    print(f"素材来源: {source}")
    print(f"模式: {'干跑（不写库）' if dry_run else '正式灌入'}"
          f"{' / 覆盖式重灌' if replace and not dry_run else ''}")
    print("=" * 76)

    docs = load_documents(source)
    if not docs:
        print("❌ 未解析到任何文档（检查目录内容与后缀：.md / .txt / .jsonl）")
        return 1

    # ---- 解析结果预览与告警 ----
    by_dest = Counter(d.destination or "(未识别，将跳过)" for d in docs)
    print(f"\n📄 解析到 {len(docs)} 篇文档，目的地分布：")
    for dest, count in by_dest.most_common():
        print(f"   {dest:<16}{count:>5} 篇")

    warned = [d for d in docs if d.warnings]
    if warned:
        print(f"\n⚠️  {len(warned)} 篇文档有告警：")
        for doc in warned[:10]:
            print(f"   《{doc.title[:30]}》 -> {'；'.join(doc.warnings)}")
        if len(warned) > 10:
            print(f"   …… 其余 {len(warned) - 10} 篇省略")

    valid = [d for d in docs if d.destination]
    if not valid:
        print("\n❌ 没有任何文档能归入云南目的地白名单，终止。")
        return 1

    print(f"\n✅ 可入库 {len(valid)} 篇 / 跳过 {len(docs) - len(valid)} 篇")

    stats = ingest_documents(docs, dry_run=dry_run, replace=replace)

    print("\n" + "=" * 76)
    if dry_run:
        print(f"干跑完成：将写入 {stats['docs']} 篇 / {stats['chunks']} 个 chunk"
              f"（跳过 {stats['skipped']} 篇）")
        print("确认无误后去掉 --dry-run 正式灌入。")
    else:
        print(f"灌入完成：成功 {stats['docs']} 篇 / {stats['chunks']} 个 chunk，"
              f"跳过 {stats['skipped']} 篇，失败 {stats['failed']} 篇")
        print("提示：目的地缓存已自动失效，无需重启后端即可检索到新城市。")

        # 灌完直接自检一次，确认检索真的能命中
        try:
            from app.services.rag import get_store, retrieve_notes_for_city
            from app.services.rag.retriever import COLLECTION_POSTS

            total = get_store().count(COLLECTION_POSTS)
            print(f"\n🔎 自检：posts 现共 {total} 个 chunk")
            sample_city = by_dest.most_common(1)[0][0].replace("云南", "")
            block = retrieve_notes_for_city(sample_city, top_k=3)
            print(f"   以「{sample_city}」试检索 -> {'命中' if block else '未命中'}")
            if block:
                print("   " + block.replace("\n", "\n   ")[:300])
        except Exception as e:
            print(f"   ⚠️ 自检失败（不影响已写入数据）: {type(e).__name__}: {e}")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
