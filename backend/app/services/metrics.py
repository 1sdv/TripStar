"""任务级运行指标收集。

为什么要它
----------
优化没有基线就只是感觉。这个模块给「一次行程生成」装上仪表盘：

* LLM 调用次数与 token 用量（成本）
* 各数据源命中分布（小红书 / 知识库 / REST / 通用常识，即降级链实际走了哪条路）
* 各阶段耗时（找瓶颈：是 LLM 慢还是外部 API 慢）
* 检索与降级次数
* 终态（成功 / 兜底 / 失败）

设计取舍
--------
* **进程内、按 task 隔离**：用 `contextvars`，异步并发下各任务互不串味。
* **不引入依赖**：不接 Prometheus/OpenTelemetry，避免为一个单实例应用加运维负担；
  需要时通过 `/api/trip/metrics` 导出，或直接看日志汇总。
* **环形缓冲**：只保留最近 N 次任务，防止长跑进程内存增长。
* **失败安全**：任何指标代码异常都不得影响主流程，全部内部吞掉。
"""

import contextvars
import statistics
import time
from collections import Counter, deque
from typing import Any, Deque, Dict, List, Optional

# 当前任务的指标累加器（异步上下文隔离）
_current: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
    "trip_metrics_current", default=None
)

# 最近完成的任务摘要（环形缓冲）
_MAX_HISTORY = 50
_history: Deque[Dict[str, Any]] = deque(maxlen=_MAX_HISTORY)


def _new_accumulator(task_id: str) -> Dict[str, Any]:
    return {
        "task_id": task_id,
        "started_at": time.time(),
        "llm_calls": 0,
        "llm_seconds": 0.0,
        "llm_prompt_tokens": 0,
        "llm_completion_tokens": 0,
        "llm_errors": 0,
        "sources": Counter(),          # 数据源命中分布
        "retrievals": 0,               # RAG 检索次数
        "degradations": 0,             # 降级次数
        "json_repairs": 0,             # JSON 修复命中次数
        "stages": {},                  # 阶段耗时
        "errors": [],
    }


def start_task(task_id: str) -> None:
    """开始记录一个任务的指标。"""
    try:
        _current.set(_new_accumulator(task_id))
    except Exception:
        pass


def current_task_id() -> Optional[str]:
    acc = _current.get()
    return acc.get("task_id") if acc else None


def record_llm_call(
    seconds: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    error: bool = False,
) -> None:
    """记录一次 LLM 调用（由 llm_service 埋点）。"""
    acc = _current.get()
    if not acc:
        return
    try:
        acc["llm_calls"] += 1
        acc["llm_seconds"] += float(seconds)
        acc["llm_prompt_tokens"] += int(prompt_tokens or 0)
        acc["llm_completion_tokens"] += int(completion_tokens or 0)
        if error:
            acc["llm_errors"] += 1
    except Exception:
        pass


def record_source(category: str, source: str) -> None:
    """记录一次数据源命中，如 record_source("attraction", "本地知识库")。"""
    acc = _current.get()
    if not acc:
        return
    try:
        acc["sources"][f"{category}:{source}"] += 1
    except Exception:
        pass


def record_retrieval(count: int = 1) -> None:
    acc = _current.get()
    if acc:
        try:
            acc["retrievals"] += count
        except Exception:
            pass


def record_degradation(reason: str = "") -> None:
    acc = _current.get()
    if acc:
        try:
            acc["degradations"] += 1
            if reason:
                acc["errors"].append(f"degrade: {reason}")
        except Exception:
            pass


def record_json_repair(attempt_name: str) -> None:
    """记录 JSON 是靠哪一级修复成功的——用它可以量化容错链的价值。"""
    acc = _current.get()
    if acc:
        try:
            acc["json_repairs"] += 1
            acc["sources"][f"json_fix:{attempt_name}"] += 1
        except Exception:
            pass


class stage_timer:
    """`with stage_timer("attraction_search"):` —— 累计同名阶段的总耗时。"""

    def __init__(self, name: str):
        self.name = name
        self._t0 = 0.0

    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        acc = _current.get()
        if not acc:
            return False
        try:
            elapsed = time.perf_counter() - self._t0
            slot = acc["stages"].setdefault(self.name, {"count": 0, "seconds": 0.0})
            slot["count"] += 1
            slot["seconds"] += elapsed
        except Exception:
            pass
        return False


def finish_task(status: str, note: str = "") -> Optional[Dict[str, Any]]:
    """结束记录并归档摘要，返回本次任务的指标字典。"""
    acc = _current.get()
    if not acc:
        return None
    try:
        acc["status"] = status
        acc["note"] = note
        acc["total_seconds"] = time.time() - acc["started_at"]
        acc["sources"] = dict(acc["sources"])
        summary = dict(acc)
        _history.append(summary)
        _current.set(None)
        return summary
    except Exception:
        return None


def format_summary(acc: Optional[Dict[str, Any]]) -> str:
    """把指标整理成适合打日志/展示的多行文本。"""
    if not acc:
        return "（无指标数据）"

    lines = [
        f"任务 {acc.get('task_id')} 状态={acc.get('status')} "
        f"总耗时={acc.get('total_seconds', 0):.1f}s",
        f"  LLM 调用 {acc.get('llm_calls', 0)} 次 / 耗时 {acc.get('llm_seconds', 0):.1f}s"
        f"（占 {_pct(acc.get('llm_seconds', 0), acc.get('total_seconds', 0))}）"
        f" / tokens 入 {acc.get('llm_prompt_tokens', 0)} 出 {acc.get('llm_completion_tokens', 0)}",
        f"  RAG 检索 {acc.get('retrievals', 0)} 次 / 降级 {acc.get('degradations', 0)} 次"
        f" / JSON 修复 {acc.get('json_repairs', 0)} 次",
    ]
    sources = acc.get("sources") or {}
    if sources:
        lines.append("  数据源分布: " + "，".join(f"{k}×{v}" for k, v in sorted(sources.items())))
    stages = acc.get("stages") or {}
    if stages:
        parts = [f"{name} {v['seconds']:.1f}s×{v['count']}" for name, v in sorted(stages.items())]
        lines.append("  阶段耗时: " + "，".join(parts))
    return "\n".join(lines)


def _pct(part: float, total: float) -> str:
    if not total:
        return "-"
    return f"{part / total * 100:.0f}%"


def history(limit: int = 10) -> List[Dict[str, Any]]:
    """最近完成任务的摘要（最新在前）。"""
    items = list(_history)[-limit:]
    items.reverse()
    return items


def aggregate(limit: int = 20) -> Dict[str, Any]:
    """对最近若干任务做聚合，回答「平均几次 LLM 调用 / 多少次降级」。"""
    items = list(_history)[-limit:]
    if not items:
        return {"tasks": 0}

    def _avg(key: str) -> float:
        values = [float(i.get(key) or 0) for i in items]
        return round(statistics.fmean(values), 2) if values else 0.0

    status_counter: Counter = Counter(str(i.get("status")) for i in items)
    total_sources: Counter = Counter()
    json_fix: Counter = Counter()
    for item in items:
        for key, value in (item.get("sources") or {}).items():
            if key.startswith("json_fix:"):
                json_fix[key.split(":", 1)[1]] += value
            else:
                total_sources[key] += value

    return {
        "tasks": len(items),
        "avg_llm_calls": _avg("llm_calls"),
        "avg_llm_seconds": _avg("llm_seconds"),
        "avg_total_seconds": _avg("total_seconds"),
        "avg_retrievals": _avg("retrievals"),
        "avg_degradations": _avg("degradations"),
        "status_distribution": dict(status_counter),
        "source_distribution": dict(total_sources),
        "json_fix_distribution": dict(json_fix),
    }


def reset() -> None:
    """清空历史（测试或人工重置用）。"""
    _history.clear()
    _current.set(None)
