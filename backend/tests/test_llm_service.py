"""LLM 适配器参数透传测试。

重点是回归一个真实缺陷：`DirectOpenAILLM.invoke` 原先只提取
temperature/max_tokens/top_p/stop/tools/response_format，**把 timeout 丢掉了**，
导致调用方（如 TRIP_PLANNER_TIMEOUT=180）设置的超时完全不起作用。

这里用假客户端验证参数确实被透传，不产生任何网络请求。
"""

import pytest


class _FakeCompletions:
    """记录每次 create 调用的参数，返回可迭代的流式分片。"""

    def __init__(self, sink):
        self._sink = sink

    def create(self, **kwargs):
        self._sink.append(kwargs)
        if kwargs.get("stream"):
            class _Delta:
                def __init__(self, content):
                    self.content = content

            class _Choice:
                def __init__(self, content):
                    self.delta = _Delta(content)

            class _Chunk:
                def __init__(self, content):
                    self.choices = [_Choice(content)]

            return iter([_Chunk("你"), _Chunk("好")])

        class _Msg:
            content = "非流式回答"

        class _Choice2:
            message = _Msg()

        class _Resp:
            choices = [_Choice2()]

        return _Resp()


class _FakeClient:
    def __init__(self, sink):
        self.chat = type("C", (), {"completions": _FakeCompletions(sink)})()
        self.timeout_overrides = []

    def with_options(self, timeout=None, **kwargs):
        self.timeout_overrides.append(timeout)
        return self


@pytest.fixture
def adapter(monkeypatch):
    """构造一个 LLM 适配器，并把内部 OpenAI 客户端换成假实现。"""
    import app.services.llm_service as mod

    sink = []
    inst = mod.DirectOpenAILLM.__new__(mod.DirectOpenAILLM)
    inst.provider = "openai-compatible"
    inst.model = "deepseek-chat"
    inst.api_key = "k"
    inst.base_url = "https://example.invalid/v1"
    inst.timeout = 600
    fake = _FakeClient(sink)
    inst._client = fake
    return inst, sink, fake


class TestInvokePassthrough:

    def test_timeout_被透传(self, adapter):
        """回归用例：timeout 必须通过 with_options 按请求生效。"""
        inst, sink, fake = adapter
        inst.invoke([{"role": "user", "content": "hi"}], timeout=42, stream=False)
        assert fake.timeout_overrides == [42.0]

    def test_未传_timeout_时不覆盖(self, adapter):
        """未指定超时应沿用客户端级超时，不应无谓地 with_options。"""
        inst, sink, fake = adapter
        inst.invoke([{"role": "user", "content": "hi"}], stream=False)
        assert fake.timeout_overrides == []

    def test_timeout_设置失败时不阻断请求(self, adapter):
        inst, sink, fake = adapter

        def _boom(**kwargs):
            raise RuntimeError("不支持该超时参数")

        fake.with_options = _boom
        content = inst.invoke([{"role": "user", "content": "hi"}], timeout=10, stream=False)
        assert content == "非流式回答"

    def test_温度被透传(self, adapter):
        inst, sink, _ = adapter
        inst.invoke([{"role": "user", "content": "hi"}], temperature=0.1, stream=False)
        assert sink[0]["temperature"] == 0.1

    def test_默认温度为_0_7(self, adapter):
        inst, sink, _ = adapter
        inst.invoke([{"role": "user", "content": "hi"}], stream=False)
        assert sink[0]["temperature"] == 0.7

    def test_默认走流式并拼接文本(self, adapter):
        inst, sink, _ = adapter
        content = inst.invoke([{"role": "user", "content": "hi"}])
        assert sink[0]["stream"] is True
        assert content == "你好"

    def test_response_format_被透传(self, adapter):
        inst, sink, _ = adapter
        fmt = {"type": "json_object"}
        inst.invoke([{"role": "user", "content": "hi"}], response_format=fmt, stream=False)
        assert sink[0]["response_format"] == fmt

    def test_tools_被透传(self, adapter):
        inst, sink, _ = adapter
        tools = [{"type": "function", "function": {"name": "f"}}]
        inst.invoke([{"role": "user", "content": "hi"}], tools=tools, tool_choice="auto", stream=False)
        assert sink[0]["tools"] == tools
        assert sink[0]["tool_choice"] == "auto"

    def test_调用方式兼容_call(self, adapter):
        inst, sink, _ = adapter
        assert inst([{"role": "user", "content": "hi"}], stream=False) == "非流式回答"
