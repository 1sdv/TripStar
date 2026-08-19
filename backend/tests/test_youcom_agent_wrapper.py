"""针对 trip_planner_agent.py 中 You.com 工具包装器 (YoucomNativeTool) 的测试。

这是"锦上添花"的补充测试：验证 [TOOL_CALL:youcom_*:...] 解析 -> 分发 -> 调用
YoucomService 的链路是否与 GoogleMapsNativeTool 的既有模式完全一致。

注意: trip_planner_agent.py 顶层 import 了 hello_agents（以及 huggingface_hub
等其依赖）。本测试文件因此需要这些包已安装，不属于 youcom_service 本身的最小
测试基线（test_youcom_service.py 完全不依赖它们）。如果 hello_agents 在某个
环境里装不上，这层覆盖会跳过，只用现场 e2e 脚本验证包装器行为即可（已在
logfile 中记录该取舍）。

不会真正初始化 MultiAgentTripPlanner（会尝试拉起高德/Google 的地图工具，
涉及子进程与外部依赖）；而是直接对 `_init_youcom_tool` 这个未绑定方法调用，
传入一个"裸"占位 self 对象，只验证 You.com 工具本身的行为，不触碰
amap/google 供应商选择逻辑。
"""

import unittest
from unittest.mock import MagicMock, patch

try:
    from backend.app.agents.trip_planner_agent import MultiAgentTripPlanner
    HELLO_AGENTS_AVAILABLE = True
    IMPORT_ERROR = None
except Exception as e:  # pragma: no cover - environment-dependent skip
    MultiAgentTripPlanner = None
    HELLO_AGENTS_AVAILABLE = False
    IMPORT_ERROR = e


class _BareSelf:
    """占位对象：只需要能承载 self._youcom_tool 属性即可。"""
    pass


@unittest.skipUnless(
    HELLO_AGENTS_AVAILABLE,
    f"hello_agents 及其依赖未安装，跳过 YoucomNativeTool 包装器测试: {IMPORT_ERROR}",
)
class TestYoucomToolRegistrationGuard(unittest.TestCase):
    def test_no_key_leaves_tool_none(self):
        settings = MagicMock(youcom_api_key="")
        fake = _BareSelf()
        MultiAgentTripPlanner._init_youcom_tool(fake, settings)
        self.assertIsNone(fake._youcom_tool)

    def test_key_present_creates_tool_with_expected_shape(self):
        settings = MagicMock(youcom_api_key="fake-key-for-wrapper-test")
        fake = _BareSelf()
        with patch(
            "backend.app.services.youcom_service.YoucomService"
        ) as MockSvc:
            MockSvc.return_value = MagicMock()
            MultiAgentTripPlanner._init_youcom_tool(fake, settings)
            MockSvc.assert_called_once_with(api_key="fake-key-for-wrapper-test")

        tool = fake._youcom_tool
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "youcom")
        self.assertTrue(tool.expandable)
        names = [t["name"] for t in tool._available_tools]
        self.assertEqual(names, ["youcom_web_search", "youcom_research"])


@unittest.skipUnless(
    HELLO_AGENTS_AVAILABLE,
    f"hello_agents 及其依赖未安装，跳过 YoucomNativeTool 包装器测试: {IMPORT_ERROR}",
)
class TestYoucomToolDispatch(unittest.TestCase):
    def setUp(self):
        settings = MagicMock(youcom_api_key="fake-key")
        fake = _BareSelf()
        with patch(
            "backend.app.services.youcom_service.YoucomService"
        ) as MockSvc:
            self.mock_svc_instance = MagicMock()
            MockSvc.return_value = self.mock_svc_instance
            MultiAgentTripPlanner._init_youcom_tool(fake, settings)
        self.tool = fake._youcom_tool

    def test_run_parses_tool_call_string_and_routes_to_search(self):
        self.mock_svc_instance.search.return_value = "搜索结果文本"
        out = self.tool.run("[TOOL_CALL:youcom_web_search:query=东京樱花,count=3]")
        self.assertEqual(out, "搜索结果文本")
        self.mock_svc_instance.search.assert_called_once()
        _, kwargs = self.mock_svc_instance.search.call_args
        self.assertEqual(kwargs.get("count"), "3")

    def test_run_parses_tool_call_string_and_routes_to_research(self):
        self.mock_svc_instance.research.return_value = "研究结果文本"
        out = self.tool.run("[TOOL_CALL:youcom_research:query=多城市行程规划建议]")
        self.assertEqual(out, "研究结果文本")
        self.mock_svc_instance.research.assert_called_once_with("多城市行程规划建议")

    def test_run_with_dict_input(self):
        self.mock_svc_instance.search.return_value = "字典输入结果"
        out = self.tool.run({
            "tool_name": "youcom_web_search",
            "arguments": {"query": "签证要求"},
        })
        self.assertEqual(out, "字典输入结果")

    def test_run_unparsable_string_returns_error_no_crash(self):
        out = self.tool.run("not a tool call at all")
        self.assertIn("无法解析工具调用", out)
        self.mock_svc_instance.search.assert_not_called()
        self.mock_svc_instance.research.assert_not_called()

    def test_run_unsupported_input_type_no_crash(self):
        out = self.tool.run(12345)
        self.assertIn("不支持的输入类型", out)

    def test_dispatch_unknown_tool_name(self):
        out = self.tool._dispatch("youcom_unknown_tool", {})
        self.assertIn("未知的 You.com 工具", out)

    def test_dispatch_swallows_service_exception(self):
        self.mock_svc_instance.search.side_effect = RuntimeError("boom")
        out = self.tool._dispatch("youcom_web_search", {"query": "q"})
        self.assertIn("You.com 工具调用失败", out)

    def test_get_expanded_tools_returns_two_subtools_that_delegate(self):
        self.mock_svc_instance.search.return_value = "子工具搜索结果"
        subtools = self.tool.get_expanded_tools()
        self.assertEqual(len(subtools), 2)
        sub_names = {t.name for t in subtools}
        self.assertEqual(sub_names, {"youcom_web_search", "youcom_research"})
        web_search_subtool = next(t for t in subtools if t.name == "youcom_web_search")
        self.assertFalse(web_search_subtool.expandable)
        out = web_search_subtool.run("[TOOL_CALL:youcom_web_search:query=q]")
        self.assertEqual(out, "子工具搜索结果")


if __name__ == "__main__":
    unittest.main()
