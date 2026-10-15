"""验证景点数据源三级降级链。

当前 XHS Cookie 已过期，正好可以真实触发降级。
"""
import sys
import time

sys.path.insert(0, r"E:\Deepseek_harness_workspace\trip\TripStar\backend")

from app.services.attraction_service import search_attractions


def show(city, keywords="自然风光"):
    print("\n" + "=" * 78)
    print(f"search_attractions({city!r}, {keywords!r})")
    print("=" * 78)
    t0 = time.time()
    text, source = search_attractions(city, keywords, "zh")
    cost = time.time() - t0
    print(f"\n>>> 数据来源 = 【{source}】  耗时 {cost:.1f}s  文本长度 {len(text)}")
    print("-" * 78)
    print(text[:900])
    return source


s1 = show("大理")
s2 = show("火星市")

print("\n" + "=" * 78)
print("断言")
print("=" * 78)
assert s1 == "本地知识库", f"大理 应走知识库，实际 {s1}"
assert s2 == "通用常识", f"火星市 应走通用常识，实际 {s2}"
print("[OK] 降级链行为符合预期：XHS 不可用 → 知识库命中 / 库外 → 通用常识兜底")
