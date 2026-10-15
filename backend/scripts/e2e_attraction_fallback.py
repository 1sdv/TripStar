"""端到端：真实触发景点降级链的完整行程生成。

不替换任何数据源——小红书 Cookie 已过期，正好用真实降级路径跑通。
"""
import asyncio
import sys
import time

sys.path.insert(0, r"E:\Deepseek_harness_workspace\trip\TripStar\backend")

from app.agents.trip_planner_agent import get_trip_planner_agent
from app.models.schemas import CityStay, TripRequest

STAGES = []


async def progress(stage, message, pct):
    STAGES.append((stage, message))
    print(f"  [{pct:>3}%] {stage:<18} {message}")


async def main():
    req = TripRequest(
        city="", cities=[CityStay(city="大理", days=3)],
        start_date="2026-05-01", end_date="2026-05-03", travel_days=3,
        transportation="公共交通", accommodation="特色民宿",
        preferences=["自然风光", "摄影"], free_text_input="想去小众一点的地方",
        language="zh",
    )
    print("=" * 78)
    print("完整行程生成（景点走真实降级链：小红书 → 知识库 → 通用常识）")
    print("=" * 78)
    # 与生产路径一致：开启任务级指标收集
    from app.services import metrics
    metrics.start_task("e2e-check")

    t0 = time.time()
    agent = get_trip_planner_agent()
    plan = await agent.plan_trip(req, progress_callback=progress)
    cost = time.time() - t0

    print("\n" + "=" * 78)
    print(f"完成，耗时 {cost:.1f}s")
    print("=" * 78)
    print(f"城市: {plan.city} / {plan.cities}    天数: {len(plan.days)}    天气条目: {len(plan.weather_info)}")
    print(f"总建议: {(plan.overall_suggestions or '')[:200]}")
    if plan.budget:
        b = plan.budget
        print(f"预算: 门票{b.total_attractions} 住宿{b.total_hotels} 餐饮{b.total_meals} 交通{b.total_transportation} = 总{b.total}")
    for day in plan.days:
        print(f"\n  [第{day.day_index+1}天 {day.date} {day.city}] {day.description[:80]}")
        for a in day.attractions:
            loc = f"{a.location.longitude:.3f},{a.location.latitude:.3f}" if a.location else "无坐标"
            print(f"    · {a.name} | {a.visit_duration}min | 门票{a.ticket_price} | {loc} | 预约={a.reservation_required}")
        print(f"    酒店: {day.hotel.name if day.hotel else '无'}")

    print("\n### 进度消息序列")
    for s, m in STAGES:
        print(f"  {s:<18} {m}")

    assert any("知识库" in m for _, m in STAGES), "未看到降级到知识库的进度提示"

    print("\n" + "=" * 78)
    print("运行指标（可用来建立基线）")
    print("=" * 78)
    summary = metrics.finish_task("completed")
    print(metrics.format_summary(summary))
    print("\n聚合视图:", metrics.aggregate(10))
    print("\n[OK] 真实降级链已跑通，行程生成成功")


asyncio.run(main())
