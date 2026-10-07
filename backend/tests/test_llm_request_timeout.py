"""回归测试：单次请求的 timeout 必须真正生效。

背景
----
``trip_planner_agent._run_planner_with_retry`` 会按 ``TRIP_PLANNER_TIMEOUT``
（默认 180 秒）把超时传给规划 Agent：

    timeout = int(os.getenv("TRIP_PLANNER_TIMEOUT", "180"))
    planner_agent.run(planner_query, timeout=timeout, temperature=0.2)

但 ``DirectOpenAILLM.invoke()`` 只从 kwargs 里取
``model / messages / temperature / max_tokens / top_p / stop`` 等字段来组装
请求，**没有读取 timeout**，于是这个参数被静默丢弃，实际生效的始终是构造
客户端时固定的 ``LLM_TIMEOUT``（默认 60 秒）。

后果：把 ``TRIP_PLANNER_TIMEOUT`` 调大完全没有作用。默认配置下（本地开发按
backend/.env.example 使用 LLM_TIMEOUT=60），一次正常需要 90 秒的规划请求会在
60 秒被掐断，触发 ``_run_planner_with_retry`` 的超时重试分支，再被掐断一次，
最终任务失败——期间产生两次计费调用，且用户看到的失败原因与真实原因无关。

本文件完全离线：用一个鸭子类型的假 client 记录调用，不发起任何网络请求，
也不需要 API Key。
"""

import asyncio
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock
from typing import Optional

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from hello_agents import SimpleAgent

from app.agents import trip_planner_agent as tpa
from app.models.schemas import TripRequest
from app.services.llm_service import DirectOpenAILLM


# ============ 假 client ============


class _Delta:
    def __init__(self, content: str) -> None:
        self.content = content


class _Chunk:
    def __init__(self, content: str) -> None:
        self.choices = [types.SimpleNamespace(delta=_Delta(content))]


class _Message:
    def __init__(self, content: str) -> None:
        self.content = content


class _Response:
    def __init__(self, content: str) -> None:
        self.choices = [types.SimpleNamespace(message=_Message(content))]


class _FakeCompletions:
    def __init__(self, owner: "_FakeClient") -> None:
        self._owner = owner

    def create(self, **kwargs):
        # 机制无关地记录「本次请求实际生效的超时」：实现既可以用
        # with_options(timeout=...)（本 PR 的写法），也可以直接给 create()
        # 传 timeout=（openai SDK 同样支持），两者在这里都算通过。
        effective_timeout = kwargs.pop("timeout", self._owner.effective_timeout)
        self._owner.requests.append(kwargs)
        self._owner.effective_timeouts.append(effective_timeout)

        if self._owner.fail_first_call and len(self._owner.requests) == 1:
            raise TimeoutError("simulated timeout")

        if kwargs.get("stream"):
            return [_Chunk("好"), _Chunk("的")]
        return _Response("好的")


class _FakeClient:
    """最小可用的假 OpenAI client。

    与真实 SDK 行为一致：``with_options()`` 返回**新对象**且不修改原对象
    （这正是不能直接改写 self._client.timeout 的原因）。派生对象与原对象
    共享同一份请求日志，便于断言请求实际生效的超时值。
    """

    def __init__(
        self,
        log: Optional[dict] = None,
        base_timeout: int = 60,
        override_timeout: Optional[int] = None,
        fail_first_call: bool = False,
    ) -> None:
        self._log = log if log is not None else {"requests": [], "timeouts": []}
        self.base_timeout = base_timeout
        self.override_timeout = override_timeout
        self.fail_first_call = fail_first_call
        self.chat = types.SimpleNamespace(completions=_FakeCompletions(self))

    @property
    def requests(self) -> list:
        return self._log["requests"]

    @property
    def effective_timeouts(self) -> list:
        return self._log["timeouts"]

    @property
    def effective_timeout(self) -> int:
        return (
            self.override_timeout
            if self.override_timeout is not None
            else self.base_timeout
        )

    def with_options(self, **kwargs):
        return _FakeClient(
            self._log,
            self.base_timeout,
            kwargs.get("timeout", self.override_timeout),
            self.fail_first_call,
        )


def _make_llm(fake_client: _FakeClient) -> DirectOpenAILLM:
    """绕过 __init__（它需要真实 api_key 并会建立网络客户端）。"""
    llm = object.__new__(DirectOpenAILLM)
    llm.provider = "openai-compatible"
    llm.model = "test-model"
    llm.api_key = "test-key"
    llm.base_url = "http://test.invalid/v1"
    llm.timeout = 60
    llm._client = fake_client
    return llm


def _trip_request() -> TripRequest:
    return TripRequest(
        city="北京",
        start_date="2026-05-01",
        end_date="2026-05-02",
        travel_days=2,
        transportation="公共交通",
        accommodation="经济型酒店",
        preferences=["历史文化"],
        language="zh",
    )


# ============ 用例 ============


class PerRequestTimeoutTests(unittest.TestCase):
    """适配器层：kwargs 里的 timeout 必须作用到本次请求。"""

    def test_explicit_timeout_governs_the_request(self) -> None:
        fake = _FakeClient()
        agent = SimpleAgent(name="探针", llm=_make_llm(fake), system_prompt="探针提示词")

        agent.run("查询天气", timeout=180, temperature=0.2)

        self.assertEqual(
            fake.effective_timeouts,
            [180],
            "timeout 被静默丢弃了，本次请求仍在使用客户端级默认值",
        )

    def test_omitting_timeout_keeps_the_client_level_default(self) -> None:
        fake = _FakeClient()
        agent = SimpleAgent(name="探针", llm=_make_llm(fake), system_prompt="探针提示词")

        agent.run("查询天气")

        self.assertEqual(fake.effective_timeouts, [fake.base_timeout])

    def test_non_streaming_path_also_honours_timeout(self) -> None:
        fake = _FakeClient()
        llm = _make_llm(fake)

        content = llm.invoke([{"role": "user", "content": "hi"}], stream=False, timeout=42)

        self.assertEqual(content, "好的")
        self.assertEqual(fake.effective_timeouts, [42])


class TripPlannerTimeoutTests(unittest.TestCase):
    """端到端：TRIP_PLANNER_TIMEOUT 必须能一路到达 HTTP 客户端。"""

    def _planner_with(self, fake: _FakeClient) -> "tpa.MultiAgentTripPlanner":
        planner = object.__new__(tpa.MultiAgentTripPlanner)
        planner.planner_agent = SimpleAgent(
            name="行程规划专家",
            llm=_make_llm(fake),
            system_prompt=tpa.PLANNER_AGENT_PROMPT,
        )
        return planner

    def test_trip_planner_timeout_env_reaches_the_http_client(self) -> None:
        fake = _FakeClient()
        planner = self._planner_with(fake)

        with mock.patch.dict(os.environ, {"TRIP_PLANNER_TIMEOUT": "240"}):
            asyncio.run(
                planner._run_planner_with_retry(
                    _trip_request(), {"北京": "景点"}, {"北京": "晴"}, {"北京": "酒店"}
                )
            )

        self.assertEqual(
            fake.effective_timeouts,
            [240],
            "TRIP_PLANNER_TIMEOUT 没有生效——规划阶段仍在使用 LLM_TIMEOUT",
        )

    def test_default_trip_planner_timeout_is_180(self) -> None:
        fake = _FakeClient()
        planner = self._planner_with(fake)

        env = {k: v for k, v in os.environ.items() if k != "TRIP_PLANNER_TIMEOUT"}
        with mock.patch.dict(os.environ, env, clear=True):
            asyncio.run(
                planner._run_planner_with_retry(
                    _trip_request(), {"北京": "景点"}, {"北京": "晴"}, {"北京": "酒店"}
                )
            )

        self.assertEqual(fake.effective_timeouts, [180])

    def test_retry_after_timeout_keeps_the_longer_deadline(self) -> None:
        """超时重试分支（trip_planner_agent 里第二处 run 调用）也必须带上该超时。

        原先没有任何用例覆盖这条分支，因此只在这里丢掉 timeout 不会被发现。
        """
        fake = _FakeClient(fail_first_call=True)
        planner = self._planner_with(fake)

        with mock.patch.dict(os.environ, {"TRIP_PLANNER_TIMEOUT": "240"}):
            asyncio.run(
                planner._run_planner_with_retry(
                    _trip_request(), {"北京": "景点"}, {"北京": "晴"}, {"北京": "酒店"}
                )
            )

        self.assertEqual(len(fake.effective_timeouts), 2, "应发生一次超时重试")
        self.assertEqual(fake.effective_timeouts, [240, 240])


if __name__ == "__main__":
    unittest.main()
