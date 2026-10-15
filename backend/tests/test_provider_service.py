"""工具失败判定的误判防护测试。

回归背景：原实现把「抱歉」「没有找到」等泛化词当作失败特征，
导致包含这类措辞的**真实结果**被误判为工具失败，触发无谓降级。
"""

import pytest


class TestLooksLikeFailure:

    @pytest.mark.parametrize(
        "text",
        [
            "❌ 错误：未找到工具 'amap_maps_weather'",
            "未找到名为 amap_maps_text_search 的工具",
            "工具当前不可用，请稍后重试",
            "系统返回的错误提示是未找到工具",
            "Tool not found: amap_maps_weather",
        ],
    )
    def test_明确的工具失败被判为失败(self, text):
        from app.services.provider_service import _looks_like_failure

        assert _looks_like_failure(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "   ",
            "抱歉，天气查询工具暂时无法使用，因此无法获取大理天气。",
            "无法查询到该城市的天气信息。",
        ],
    )
    def test_无真实数据的软失败被判为失败(self, text):
        from app.services.provider_service import _looks_like_failure

        assert _looks_like_failure(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            # 真实天气：含日期与温度
            "2026-10-15: 白天晴 23°C, 夜间多云 10°C, 西南风 1-3",
            "【大理 未来天气（高德官方预报，最多 4 天）】\n2026-10-15: 白天晴 23°C",
            # 真实酒店：含价格/评分
            "1. 大理观山听海楼客栈 | 地址：南门新村71号 | 评分：4.7 | 人均：380元",
        ],
    )
    def test_真实数据不被误判(self, text):
        from app.services.provider_service import _looks_like_failure

        assert _looks_like_failure(text) is False

    def test_含抱歉但带真实温度不算失败(self):
        """关键回归：措辞里有道歉，但同时给出了真实数据 → 应视为成功。"""
        from app.services.provider_service import _looks_like_failure

        text = "抱歉让您久等。大理未来天气：2026-10-15 白天晴 23°C，夜间多云 10°C。"
        assert _looks_like_failure(text) is False

    def test_软失败词加真实数据不算失败(self):
        """边界：出现「无法」但同时给了真实价格/评分 → 视为有效结果，不降级。"""
        from app.services.provider_service import _looks_like_failure

        text = "抱歉，部分民宿无法确认评分。可用结果：大理客来居客栈 | 地址：古城南门 | 评分：4.4 | 人均：260元"
        assert _looks_like_failure(text) is False

    def test_简单抱歉不算失败(self):
        """仅「抱歉」不构成失败特征，避免把正常措辞误判掉。"""
        from app.services.provider_service import _looks_like_failure

        assert _looks_like_failure("抱歉让您久等，大理的住宿建议如下：古城周边民宿 300 元起") is False

    def test_软失败词无数据特征判为失败(self):
        from app.services.provider_service import _looks_like_failure

        assert _looks_like_failure("抱歉，我无法获取该城市的住宿信息。") is True

    def test_普通推荐文本不算失败(self):
        from app.services.provider_service import _looks_like_failure

        text = "建议住在大理古城周边，交通便利，民宿价格约 300-500 元。"
        assert _looks_like_failure(text) is False


class TestProbeMcpTools:

    def _agent(self, names):
        class _A:
            def list_tools(self_inner):
                return names

        return _A()

    def test_展开成功视为就绪(self):
        from app.services.provider_service import probe_mcp_tools

        assert probe_mcp_tools(self._agent(["amap_maps_weather", "amap_maps_text_search"])) is True

    def test_只剩父工具名视为未就绪(self):
        from app.services.provider_service import probe_mcp_tools

        assert probe_mcp_tools(self._agent(["amap"])) is False

    def test_空工具列表视为未就绪(self):
        from app.services.provider_service import probe_mcp_tools

        assert probe_mcp_tools(self._agent([])) is False

    def test_异常时视为未就绪(self):
        from app.services.provider_service import probe_mcp_tools

        class _Boom:
            def list_tools(self):
                raise RuntimeError("boom")

        assert probe_mcp_tools(_Boom()) is False


class TestStageProgress:

    def test_阶段顺序单调递增(self):
        from app.agents.trip_planner_agent import CITY_COLLECTION_STAGES, _stage_progress

        values = [_stage_progress(s, 0, 1) for s in CITY_COLLECTION_STAGES]
        assert values == sorted(values)
        assert len(set(values)) == len(values), "各阶段进度不应重复"

    def test_多城市区间不重叠且递增(self):
        from app.agents.trip_planner_agent import (
            CITY_COLLECTION_STAGES,
            _COLLECTION_PROGRESS_END,
            _COLLECTION_PROGRESS_START,
            _stage_progress,
        )

        seq = [
            _stage_progress(stage, city_index, 3)
            for city_index in range(3)
            for stage in CITY_COLLECTION_STAGES
        ]
        assert seq == sorted(seq), "跨城市进度必须单调递增，否则进度条会倒退"
        assert all(_COLLECTION_PROGRESS_START <= v <= _COLLECTION_PROGRESS_END for v in seq)

    def test_单城市覆盖完整区间(self):
        from app.agents.trip_planner_agent import (
            CITY_COLLECTION_STAGES,
            _COLLECTION_PROGRESS_END,
            _COLLECTION_PROGRESS_START,
            _stage_progress,
        )

        first = _stage_progress(CITY_COLLECTION_STAGES[0], 0, 1)
        last = _stage_progress(CITY_COLLECTION_STAGES[-1], 0, 1)
        assert first == _COLLECTION_PROGRESS_START
        assert last < _COLLECTION_PROGRESS_END

    def test_未知阶段回退到起始(self):
        from app.agents.trip_planner_agent import _stage_progress

        assert _stage_progress("不存在", 0, 1) >= 0
