"""深度单元测试：backend.app.services.youcom_service.YoucomService

设计要点：
  - 完全离线：使用 unittest.mock 替换 YoucomService._client 的 get/post 方法，
    不发起任何真实网络请求。
  - 不 import hello_agents / config / 完整应用，服务模块本身也不依赖它们。
  - 覆盖：请求构造、响应映射、每一种错误路径、对抗性输入，并在所有场景下
    断言 API Key 原文绝不会出现在任何返回值中。

运行方式:
  python3 -m unittest backend.tests.test_youcom_service -v
  (或 python3 -m unittest discover -s backend/tests -v，需将仓库根目录加入 PYTHONPATH)
"""

import json
import unittest
from unittest.mock import MagicMock

import httpx

from backend.app.services.youcom_service import YoucomService


SECRET_KEY = "ydc-super-secret-key-1234567890"


def make_response(json_data=None, status_code=200, json_raises=None):
    """构造一个可用于替换 httpx 响应对象的 MagicMock。"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status.return_value = None
    if json_raises is not None:
        resp.json.side_effect = json_raises
    else:
        resp.json.return_value = json_data
    return resp


def make_http_status_error(status_code, message="http error"):
    resp = MagicMock()
    resp.status_code = status_code
    exc = httpx.HTTPStatusError(message, request=MagicMock(), response=resp)
    resp.raise_for_status.side_effect = exc
    return resp


class YoucomServiceTestCase(unittest.TestCase):
    """公共 setUp：构造一个带假 client 的服务实例。"""

    def setUp(self):
        self.svc = YoucomService(api_key=SECRET_KEY)
        # 用 Mock 替换真实的 httpx.Client 实例方法，杜绝任何网络调用
        self.svc._client.get = MagicMock()
        self.svc._client.post = MagicMock()

    def assertKeyNotLeaked(self, text):
        self.assertNotIn(SECRET_KEY, text)


# =====================================================================
# 1. search() 请求构造
# =====================================================================
class TestSearchRequestConstruction(YoucomServiceTestCase):
    def test_url_and_header(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        self.svc.search("东京 樱花")
        args, kwargs = self.svc._client.get.call_args
        self.assertEqual(args[0], YoucomService.SEARCH_URL)
        self.assertEqual(kwargs["headers"]["X-API-Key"], SECRET_KEY)

    def test_query_param_passed(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        self.svc.search("最佳旅行时间")
        _, kwargs = self.svc._client.get.call_args
        self.assertEqual(kwargs["params"]["query"], "最佳旅行时间")

    def test_default_count(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        self.svc.search("q")
        _, kwargs = self.svc._client.get.call_args
        self.assertEqual(kwargs["params"]["count"], 5)

    def test_custom_count(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        self.svc.search("q", count=10)
        _, kwargs = self.svc._client.get.call_args
        self.assertEqual(kwargs["params"]["count"], 10)

    def test_count_capped_at_20(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        self.svc.search("q", count=999)
        _, kwargs = self.svc._client.get.call_args
        self.assertEqual(kwargs["params"]["count"], 20)

    def test_count_exactly_20_not_capped_down(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        self.svc.search("q", count=20)
        _, kwargs = self.svc._client.get.call_args
        self.assertEqual(kwargs["params"]["count"], 20)

    def test_count_zero_falls_back_to_default(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        self.svc.search("q", count=0)
        _, kwargs = self.svc._client.get.call_args
        self.assertEqual(kwargs["params"]["count"], 5)

    def test_count_negative_falls_back_to_default(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        self.svc.search("q", count=-3)
        _, kwargs = self.svc._client.get.call_args
        self.assertEqual(kwargs["params"]["count"], 5)

    def test_count_non_numeric_string_falls_back_to_default(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        self.svc.search("q", count="abc")
        _, kwargs = self.svc._client.get.call_args
        self.assertEqual(kwargs["params"]["count"], 5)

    def test_count_none_falls_back_to_default(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        self.svc.search("q", count=None)
        _, kwargs = self.svc._client.get.call_args
        self.assertEqual(kwargs["params"]["count"], 5)

    def test_count_numeric_string_is_accepted(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        self.svc.search("q", count="7")
        _, kwargs = self.svc._client.get.call_args
        self.assertEqual(kwargs["params"]["count"], 7)

    def test_count_float_truncated(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        self.svc.search("q", count=3.9)
        _, kwargs = self.svc._client.get.call_args
        self.assertEqual(kwargs["params"]["count"], 3)

    def test_freshness_and_country_passthrough(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        self.svc.search("q", freshness="pastDay", country="CN")
        _, kwargs = self.svc._client.get.call_args
        self.assertEqual(kwargs["params"]["freshness"], "pastDay")
        self.assertEqual(kwargs["params"]["country"], "CN")

    def test_freshness_and_country_absent_by_default(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        self.svc.search("q")
        _, kwargs = self.svc._client.get.call_args
        self.assertNotIn("freshness", kwargs["params"])
        self.assertNotIn("country", kwargs["params"])


# =====================================================================
# 2. search() 响应映射
# =====================================================================
class TestSearchResponseMapping(YoucomServiceTestCase):
    def test_web_present_numbered_fields(self):
        self.svc._client.get.return_value = make_response({
            "results": {
                "web": [
                    {
                        "title": "东京樱花攻略",
                        "url": "https://example.com/a",
                        "description": "详细攻略",
                        "snippets": ["3月下旬最佳", "上野公园推荐"],
                    }
                ]
            }
        })
        out = self.svc.search("q")
        self.assertIn("1. 东京樱花攻略", out)
        self.assertIn("链接: https://example.com/a", out)
        self.assertIn("简介: 详细攻略", out)
        self.assertIn("摘要: 3月下旬最佳", out)
        self.assertIn("摘要: 上野公园推荐", out)

    def test_news_present_after_web_with_divider(self):
        self.svc._client.get.return_value = make_response({
            "results": {
                "web": [{"title": "A", "url": "u1", "description": "d1", "snippets": []}],
                "news": [{"title": "B", "url": "u2", "description": "d2", "snippets": []}],
            }
        })
        out = self.svc.search("q")
        self.assertIn("1. A", out)
        self.assertIn("相关资讯:", out)
        self.assertIn("2. B", out)
        # 相关资讯必须出现在 web 之后
        self.assertLess(out.index("1. A"), out.index("相关资讯:"))
        self.assertLess(out.index("相关资讯:"), out.index("2. B"))

    def test_both_web_and_news_absent(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        out = self.svc.search("q")
        self.assertEqual(out, "未找到相关信息")

    def test_missing_title_shows_placeholder(self):
        self.svc._client.get.return_value = make_response({
            "results": {"web": [{"url": "u1", "description": "d1"}]}
        })
        out = self.svc.search("q")
        self.assertIn("1. (无标题)", out)

    def test_missing_url_omits_link_line(self):
        self.svc._client.get.return_value = make_response({
            "results": {"web": [{"title": "T", "description": "d1"}]}
        })
        out = self.svc.search("q")
        self.assertNotIn("链接:", out)

    def test_missing_description_omits_line(self):
        self.svc._client.get.return_value = make_response({
            "results": {"web": [{"title": "T", "url": "u1"}]}
        })
        out = self.svc.search("q")
        self.assertNotIn("简介:", out)

    def test_blank_and_empty_snippets_filtered(self):
        self.svc._client.get.return_value = make_response({
            "results": {
                "web": [
                    {"title": "T", "url": "u1", "snippets": ["", "   ", "真实摘要", None, 123]}
                ]
            }
        })
        out = self.svc.search("q")
        self.assertIn("摘要: 真实摘要", out)
        self.assertEqual(out.count("摘要:"), 1)

    def test_results_null(self):
        self.svc._client.get.return_value = make_response({"results": None})
        out = self.svc.search("q")
        self.assertEqual(out, "未找到相关信息")

    def test_web_null_defensive(self):
        self.svc._client.get.return_value = make_response({"results": {"web": None, "news": None}})
        out = self.svc.search("q")
        self.assertEqual(out, "未找到相关信息")

    def test_web_null_but_news_present(self):
        self.svc._client.get.return_value = make_response({
            "results": {"web": None, "news": [{"title": "N", "url": "u"}]}
        })
        out = self.svc.search("q")
        self.assertIn("1. N", out)

    def test_data_not_dict(self):
        self.svc._client.get.return_value = make_response("not-a-dict")
        out = self.svc.search("q")
        self.assertEqual(out, "未找到相关信息")

    def test_non_dict_items_in_list_are_skipped_without_crash(self):
        self.svc._client.get.return_value = make_response({
            "results": {"web": [{"title": "Good", "url": "u"}, "garbage", None, 42]}
        })
        out = self.svc.search("q")
        self.assertIn("1. Good", out)
        # 只有一条有效结果，编号不应跳到 2
        self.assertNotIn("2.", out)

    def test_unicode_preserved(self):
        self.svc._client.get.return_value = make_response({
            "results": {"web": [{"title": "东京🌸花见 2026", "url": "u", "description": "签证/护照信息"}]}
        })
        out = self.svc.search("q")
        self.assertIn("东京🌸花见 2026", out)
        self.assertIn("签证/护照信息", out)

    def test_empty_web_list(self):
        self.svc._client.get.return_value = make_response({"results": {"web": []}})
        out = self.svc.search("q")
        self.assertEqual(out, "未找到相关信息")


# =====================================================================
# 3. search() 错误路径
# =====================================================================
class TestSearchErrors(YoucomServiceTestCase):
    def test_missing_key_returns_clean_message_and_does_not_call_network(self):
        svc = YoucomService(api_key="")
        svc._client.get = MagicMock()
        out = svc.search("q")
        self.assertIn("未配置 You.com API Key", out)
        svc._client.get.assert_not_called()

    def _assert_status_error(self, status_code):
        self.svc._client.get.return_value = make_http_status_error(status_code)
        out = self.svc.search("q")
        self.assertIn(str(status_code), out)
        self.assertKeyNotLeaked(out)
        return out

    def test_401_unauthorized(self):
        out = self._assert_status_error(401)
        self.assertIn("失败", out)

    def test_403_forbidden(self):
        self._assert_status_error(403)

    def test_422_bad_params(self):
        self._assert_status_error(422)

    def test_429_rate_limited(self):
        self._assert_status_error(429)

    def test_500_server_error(self):
        self._assert_status_error(500)

    def test_503_server_error(self):
        self._assert_status_error(503)

    def test_timeout(self):
        self.svc._client.get.side_effect = httpx.TimeoutException("timed out")
        out = self.svc.search("q")
        self.assertIn("超时", out)
        self.assertKeyNotLeaked(out)

    def test_malformed_json(self):
        self.svc._client.get.return_value = make_response(
            json_raises=json.JSONDecodeError("Expecting value", "doc", 0)
        )
        out = self.svc.search("q")
        self.assertIn("解析失败", out)
        self.assertKeyNotLeaked(out)

    def test_empty_body(self):
        # 空响应体典型表现为 json() 抛出 JSONDecodeError
        self.svc._client.get.return_value = make_response(
            json_raises=json.JSONDecodeError("Expecting value", "", 0)
        )
        out = self.svc.search("q")
        self.assertIsInstance(out, str)
        self.assertTrue(out)
        self.assertKeyNotLeaked(out)

    def test_generic_connection_error_no_crash(self):
        self.svc._client.get.side_effect = httpx.ConnectError("dns failure")
        out = self.svc.search("q")
        self.assertIn("网络请求失败", out)
        self.assertKeyNotLeaked(out)

    def test_unexpected_exception_no_crash(self):
        self.svc._client.get.side_effect = RuntimeError("boom")
        out = self.svc.search("q")
        self.assertIsInstance(out, str)
        self.assertKeyNotLeaked(out)

    def test_key_never_leaked_even_if_exception_message_contains_it(self):
        # 极端情况：异常消息本身意外包含了 key（例如第三方库回显了请求参数）
        self.svc._client.get.side_effect = RuntimeError(f"failed with key {SECRET_KEY}")
        out = self.svc.search("q")
        self.assertKeyNotLeaked(out)


# =====================================================================
# 4. research() 请求构造
# =====================================================================
class TestResearchRequestConstruction(YoucomServiceTestCase):
    def test_url_and_header(self):
        self.svc._client.post.return_value = make_response({"output": {"content": "c"}})
        self.svc.research("规划东京五日游")
        args, kwargs = self.svc._client.post.call_args
        self.assertEqual(args[0], YoucomService.RESEARCH_URL)
        self.assertEqual(kwargs["headers"]["X-API-Key"], SECRET_KEY)

    def test_request_body(self):
        self.svc._client.post.return_value = make_response({"output": {"content": "c"}})
        self.svc.research("规划东京五日游")
        _, kwargs = self.svc._client.post.call_args
        self.assertEqual(kwargs["json"]["input"], "规划东京五日游")
        self.assertEqual(kwargs["json"]["research_effort"], "lite")


# =====================================================================
# 5. research() 响应映射
# =====================================================================
class TestResearchResponseMapping(YoucomServiceTestCase):
    def test_content_and_sources(self):
        self.svc._client.post.return_value = make_response({
            "output": {
                "content": "东京樱花季建议3月下旬到访。",
                "sources": [
                    {"title": "官方旅游局", "url": "https://a.example"},
                    {"title": "", "url": "https://b.example"},
                ],
            }
        })
        out = self.svc.research("q")
        self.assertIn("东京樱花季建议3月下旬到访。", out)
        self.assertIn("参考来源:", out)
        self.assertIn("1. 官方旅游局 - https://a.example", out)
        self.assertIn("2. https://b.example", out)

    def test_sources_as_plain_strings(self):
        self.svc._client.post.return_value = make_response({
            "output": {"content": "内容", "sources": ["https://a", "https://b"]}
        })
        out = self.svc.research("q")
        self.assertIn("1. https://a", out)
        self.assertIn("2. https://b", out)

    def test_missing_content(self):
        self.svc._client.post.return_value = make_response({"output": {"sources": []}})
        out = self.svc.research("q")
        self.assertIn("未获取到研究内容", out)

    def test_missing_output(self):
        self.svc._client.post.return_value = make_response({})
        out = self.svc.research("q")
        self.assertIn("未获取到研究内容", out)
        self.assertNotIn("参考来源", out)

    def test_data_not_dict(self):
        self.svc._client.post.return_value = make_response(None)
        out = self.svc.research("q")
        self.assertEqual(out, "未获取到研究结果")

    def test_source_missing_url_uses_title_only(self):
        self.svc._client.post.return_value = make_response({
            "output": {"content": "c", "sources": [{"title": "仅标题"}]}
        })
        out = self.svc.research("q")
        self.assertIn("1. 仅标题", out)

    def test_bad_sources_entries_skipped(self):
        self.svc._client.post.return_value = make_response({
            "output": {"content": "c", "sources": [{}, None, 42, ""]}
        })
        out = self.svc.research("q")
        self.assertNotIn("参考来源", out)


# =====================================================================
# 6. research() 错误路径
# =====================================================================
class TestResearchErrors(YoucomServiceTestCase):
    def test_missing_key(self):
        svc = YoucomService(api_key="")
        svc._client.post = MagicMock()
        out = svc.research("q")
        self.assertIn("未配置 You.com API Key", out)
        svc._client.post.assert_not_called()

    def test_401(self):
        self.svc._client.post.return_value = make_http_status_error(401)
        out = self.svc.research("q")
        self.assertIn("401", out)
        self.assertKeyNotLeaked(out)

    def test_429(self):
        self.svc._client.post.return_value = make_http_status_error(429)
        out = self.svc.research("q")
        self.assertIn("429", out)
        self.assertKeyNotLeaked(out)

    def test_500(self):
        self.svc._client.post.return_value = make_http_status_error(500)
        out = self.svc.research("q")
        self.assertIn("500", out)
        self.assertKeyNotLeaked(out)

    def test_timeout(self):
        self.svc._client.post.side_effect = httpx.TimeoutException("timed out")
        out = self.svc.research("q")
        self.assertIn("超时", out)
        self.assertKeyNotLeaked(out)

    def test_malformed_json(self):
        self.svc._client.post.return_value = make_response(
            json_raises=json.JSONDecodeError("Expecting value", "doc", 0)
        )
        out = self.svc.research("q")
        self.assertIn("解析失败", out)
        self.assertKeyNotLeaked(out)


# =====================================================================
# 7. 对抗性输入
# =====================================================================
class TestAdversarialInputs(YoucomServiceTestCase):
    def test_search_whitespace_query_short_circuits(self):
        out = self.svc.search("   \t\n  ")
        self.assertIn("不能为空", out)
        self.svc._client.get.assert_not_called()

    def test_research_whitespace_query_short_circuits(self):
        out = self.svc.research("   ")
        self.assertIn("不能为空", out)
        self.svc._client.post.assert_not_called()

    def test_search_none_query(self):
        out = self.svc.search(None)
        self.assertIn("不能为空", out)
        self.svc._client.get.assert_not_called()

    def test_search_huge_query_no_crash(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        huge = "东" * 50000
        out = self.svc.search(huge)
        self.assertIsInstance(out, str)
        _, kwargs = self.svc._client.get.call_args
        self.assertEqual(len(kwargs["params"]["query"]), 50000)

    def test_search_non_string_int_query_coerced(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        out = self.svc.search(12345)
        self.assertIsInstance(out, str)
        _, kwargs = self.svc._client.get.call_args
        self.assertEqual(kwargs["params"]["query"], "12345")

    def test_search_non_string_list_query_coerced_no_crash(self):
        self.svc._client.get.return_value = make_response({"results": {}})
        out = self.svc.search(["东京", "京都"])
        self.assertIsInstance(out, str)
        self.svc._client.get.assert_called_once()

    def test_research_non_string_query_coerced_no_crash(self):
        self.svc._client.post.return_value = make_response({"output": {"content": "c"}})
        out = self.svc.research(3.14)
        self.assertIsInstance(out, str)
        self.svc._client.post.assert_called_once()

    def test_key_never_in_output_across_error_matrix(self):
        scenarios = [
            ("timeout", httpx.TimeoutException("boom")),
            ("connect", httpx.ConnectError("boom")),
            ("runtime", RuntimeError(f"leaked {SECRET_KEY} maybe")),
        ]
        for label, exc in scenarios:
            with self.subTest(label=label):
                self.svc._client.get.side_effect = exc
                out = self.svc.search("q")
                self.assertKeyNotLeaked(out)

        for status in (401, 403, 422, 429, 500):
            with self.subTest(status=status):
                self.svc._client.get.side_effect = None
                self.svc._client.get.return_value = make_http_status_error(status)
                out = self.svc.search("q")
                self.assertKeyNotLeaked(out)


if __name__ == "__main__":
    unittest.main()
