"""运行指标收集测试。

指标本身不影响业务逻辑，但它是「优化有基线」的前提。
这里验证聚合与容错行为，不依赖任何外部服务。
"""

import pytest


@pytest.fixture(autouse=True)
def _clean_metrics():
    from app.services import metrics

    metrics.reset()
    yield
    metrics.reset()


class TestAccumulator:

    def test_未开始任务时埋点不报错(self):
        from app.services import metrics

        # 没有活动任务时，所有埋点都应静默忽略而不是抛异常
        metrics.record_llm_call(1.0)
        metrics.record_source("attraction", "小红书")
        metrics.record_retrieval()
        metrics.record_degradation("x")
        metrics.record_json_repair("截断修复")
        assert metrics.current_task_id() is None
        assert metrics.finish_task("completed") is None

    def test_计数与耗时累计(self):
        from app.services import metrics

        metrics.start_task("t1")
        assert metrics.current_task_id() == "t1"
        metrics.record_llm_call(1.5, prompt_tokens=100, completion_tokens=50)
        metrics.record_llm_call(0.5, prompt_tokens=20, completion_tokens=10)
        metrics.record_llm_call(9.0, error=True)
        metrics.record_retrieval()
        metrics.record_retrieval()
        metrics.record_degradation("xhs 过期")

        summary = metrics.finish_task("completed")
        assert summary["llm_calls"] == 3
        assert summary["llm_seconds"] == pytest.approx(11.0)
        assert summary["llm_prompt_tokens"] == 120
        assert summary["llm_completion_tokens"] == 60
        assert summary["llm_errors"] == 1
        assert summary["retrievals"] == 2
        assert summary["degradations"] == 1
        assert summary["status"] == "completed"
        assert summary["total_seconds"] >= 0

    def test_结束后上下文被清空(self):
        from app.services import metrics

        metrics.start_task("t1")
        metrics.finish_task("completed")
        assert metrics.current_task_id() is None

    def test_数据源分布按类别聚合(self):
        from app.services import metrics

        metrics.start_task("t2")
        metrics.record_source("attraction", "本地知识库")
        metrics.record_source("weather", "高德 REST")
        metrics.record_source("weather", "高德 REST")
        summary = metrics.finish_task("completed")
        assert summary["sources"]["attraction:本地知识库"] == 1
        assert summary["sources"]["weather:高德 REST"] == 2

    def test_JSON_修复命中被单独归类(self):
        from app.services import metrics

        metrics.start_task("t3")
        metrics.record_json_repair("截断修复")
        metrics.record_json_repair("截断修复")
        metrics.record_json_repair("LLM 修复")
        summary = metrics.finish_task("completed")
        assert summary["json_repairs"] == 3
        assert summary["sources"]["json_fix:截断修复"] == 2

    def test_阶段计时累计同名阶段(self):
        import time

        from app.services import metrics

        metrics.start_task("t4")
        with metrics.stage_timer("attraction_search"):
            time.sleep(0.01)
        with metrics.stage_timer("attraction_search"):
            time.sleep(0.01)
        with metrics.stage_timer("planning"):
            time.sleep(0.01)
        summary = metrics.finish_task("completed")
        assert summary["stages"]["attraction_search"]["count"] == 2
        assert summary["stages"]["attraction_search"]["seconds"] > 0.015
        assert summary["stages"]["planning"]["count"] == 1

    def test_没有活动任务时阶段计时也不报错(self):
        from app.services import metrics

        with metrics.stage_timer("x"):
            pass


class TestAggregate:

    def test_空历史返回_tasks_0(self):
        from app.services import metrics

        assert metrics.aggregate() == {"tasks": 0}

    def test_聚合平均值与分布(self):
        from app.services import metrics

        for i, status in enumerate(["completed", "completed", "failed"]):
            metrics.start_task(f"t{i}")
            metrics.record_llm_call(1.0 * (i + 1))
            metrics.record_source("attraction", "本地知识库")
            metrics.record_degradation()
            metrics.finish_task(status)

        agg = metrics.aggregate(10)
        assert agg["tasks"] == 3
        assert agg["avg_llm_calls"] == 1.0
        assert agg["avg_llm_seconds"] == pytest.approx(2.0)
        assert agg["avg_degradations"] == 1.0
        assert agg["status_distribution"] == {"completed": 2, "failed": 1}
        assert agg["source_distribution"] == {"attraction:本地知识库": 3}

    def test_历史按限制截断且最新在前(self):
        from app.services import metrics

        for i in range(5):
            metrics.start_task(f"t{i}")
            metrics.finish_task("completed")

        recent = metrics.history(2)
        assert len(recent) == 2
        assert recent[0]["task_id"] == "t4"   # 最新在前
        assert recent[1]["task_id"] == "t3"

    def test_环形缓冲有上限(self):
        from app.services import metrics

        for i in range(60):
            metrics.start_task(f"t{i}")
            metrics.finish_task("completed")
        # _MAX_HISTORY = 50
        assert len(metrics.history(100)) == 50
        assert metrics.history(1)[0]["task_id"] == "t59"


class TestFormatSummary:

    def test_摘要包含关键信息(self):
        from app.services import metrics

        metrics.start_task("t9")
        metrics.record_llm_call(2.0, prompt_tokens=10, completion_tokens=5)
        metrics.record_source("attraction", "小红书")
        metrics.record_retrieval()
        summary = metrics.finish_task("completed")
        text = metrics.format_summary(summary)
        assert "t9" in text
        assert "LLM 调用 1 次" in text
        assert "小红书" in text

    def test_空指标不报错(self):
        from app.services import metrics

        assert metrics.format_summary(None) == "（无指标数据）"
