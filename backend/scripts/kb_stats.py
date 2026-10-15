"""盘点 RAG 知识库的城市覆盖分布。

用法：python backend/scripts/kb_stats.py [topN]
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.rag import get_store
from app.services.rag.retriever import COLLECTION_AUTHORITY, COLLECTION_POSTS


def group_by_destination(collection: str):
    """返回 (destination -> chunk 数, destination -> 去重帖子数) 两个 Counter。"""
    metas = get_store().get_all(collection)
    chunk_counter: Counter = Counter()
    posts: dict = defaultdict(set)
    for item in metas:
        meta = item.get("meta") or {}
        dest = str(meta.get("destination") or "(空)").strip() or "(空)"
        chunk_counter[dest] += 1
        posts[dest].add(meta.get("post_id") or item["id"])
    return chunk_counter, {k: len(v) for k, v in posts.items()}


def main() -> None:
    top_n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    store = get_store()

    print("=" * 76)
    print(f"知识库总量：posts={store.count(COLLECTION_POSTS)} chunks, "
          f"authority={store.count(COLLECTION_AUTHORITY)} 条")
    print("=" * 76)

    for label, collection in (("posts（UGC 游记）", COLLECTION_POSTS),
                              ("authority（权威底库）", COLLECTION_AUTHORITY)):
        chunks, posts = group_by_destination(collection)
        total_dest = len(chunks)
        print(f"\n### {label} —— 覆盖 {total_dest} 个目的地，共 {sum(chunks.values())} chunks")
        print(f"{'目的地':<16}{'chunks':>8}{'去重条目':>10}{'占比':>9}   条形")
        print("-" * 76)
        grand_total = sum(chunks.values()) or 1
        for dest, count in chunks.most_common(top_n):
            n_posts = posts[dest]
            pct = count / grand_total * 100
            bar = "█" * max(1, int(pct / 2))
            print(f"{dest:<16}{count:>8}{n_posts:>10}{pct:>8.1f}%   {bar}")

        if total_dest > top_n:
            rest = sum(c for _, c in chunks.most_common()[top_n:])
            print(f"{'（其余 %d 个目的地）' % (total_dest - top_n):<16}{rest:>8}{'':>10}"
                  f"{rest / grand_total * 100:>8.1f}%")

        # 单条最少的尾部，说明长尾情况
        tail = [d for d, c in chunks.items() if c <= 2]
        print(f"\n长尾：chunks<=2 的目的地有 {len(tail)} 个 —— {sorted(tail)[:12]}")


if __name__ == "__main__":
    main()
