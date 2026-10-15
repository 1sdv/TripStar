"""HTTP 层端到端验证：真实提交任务 → 确认指标被收集 → 清理测试数据。

这是唯一能同时验证「接口注册 + 指标埋点 + 任务生命周期」的方式。
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000"
TASKS_DIR = Path(__file__).resolve().parents[1] / "data" / "trip_tasks"


def _post(path, payload):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(path):
    with urllib.request.urlopen(BASE + path, timeout=600) as resp:
        return json.loads(resp.read().decode("utf-8"))


payload = {
    "city": "",
    "cities": [{"city": "大理", "days": 2}],
    "start_date": "2026-06-01",
    "end_date": "2026-06-02",
    "travel_days": 2,
    "transportation": "公共交通",
    "accommodation": "特色民宿",
    "preferences": ["自然风光"],
    "free_text_input": "",
    "language": "zh",
}

print("=" * 74)
print("1) 提交任务")
submit = _post("/api/trip/plan", payload)
task_id = submit["task_id"]
print(f"   task_id = {task_id}  status = {submit['status']}")

print("\n2) 轮询直到完成（真实 LLM 调用，可能 20~90s）")
t0 = time.time()
final = None
while time.time() - t0 < 300:
    status = _get(f"/api/trip/status/{task_id}")
    if status.get("status") in ("completed", "failed"):
        final = status
        break
    print(f"   [{time.time() - t0:5.1f}s] {status.get('stage')} "
          f"{status.get('progress')}% {status.get('progress_text', '')[:40]}")
    time.sleep(5)

assert final, "任务超时未结束"
print(f"   终态 = {final['status']}，耗时 {time.time() - t0:.1f}s")

if final["status"] == "completed":
    plan = final["result"]["data"]
    sources = getattr(plan, "get", lambda k, d=None: None)
    print(f"   城市={plan.get('city')} 天数={len(plan.get('days') or [])}")

print("\n3) 查询运行指标（验证埋点是否落库）")
metrics = _get("/api/trip/metrics?limit=5")
agg = metrics["aggregate"]
print(f"   tasks={agg.get('tasks')}  avg_llm_calls={agg.get('avg_llm_calls')} "
      f"avg_total={agg.get('avg_total_seconds')}s")
print(f"   数据源分布={agg.get('source_distribution')}")
print(f"   状态分布={agg.get('status_distribution')}")
assert agg.get("tasks", 0) >= 1, "指标未被收集"
assert agg.get("avg_llm_calls", 0) > 0, "LLM 调用次数未记录"
print("   ✅ 指标已通过 HTTP 接口正确导出")

print("\n4) 清理本次测试任务（不污染历史计划列表）")
removed = []
for path in TASKS_DIR.glob(f"{task_id}.json"):
    path.unlink()
    removed.append(path.name)
print(f"   已删除: {removed or '（无文件）'}")

print("\n" + "=" * 74)
print("[OK] HTTP 端到端 + 指标导出验证通过")
print("=" * 74)
