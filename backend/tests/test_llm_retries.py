"""Exercise configured retries through the real OpenAI SDK, without network access.

Run from backend: python -m unittest discover -s tests -v
"""

import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import openai

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services import llm_service


class LLMRetryTests(unittest.TestCase):
    def start_patch(self, patcher):
        self.addCleanup(patcher.stop)
        return patcher.start()

    def setUp(self):
        self.addCleanup(llm_service.reset_llm)
        llm_service.reset_llm()
        self.start_patch(patch.dict(os.environ, {}, clear=True))
        self.start_patch(patch.object(llm_service, "get_settings", return_value=SimpleNamespace(
            openai_api_key="test-key",
            openai_base_url="https://llm.invalid/v1",
            openai_model="test-model",
        )))
        self.sleep = self.start_patch(patch("openai._base_client.time.sleep"))
        # Intercept the HTTP transport so serialization, SDK errors and retry
        # decisions still run, but no request can reach a model provider.
        self.transport = self.start_patch(patch.object(httpx.HTTPTransport, "handle_request"))
        self.transport.side_effect = AssertionError("Unexpected HTTP request")

    def make_llm(self, retries=None):
        if retries is not None:
            os.environ["LLM_MAX_RETRIES"] = str(retries)
        llm = llm_service.get_llm()
        self.addCleanup(llm._client.close)
        return llm

    @staticmethod
    def success(stream):
        if stream:
            chunk = {"id": "test", "object": "chat.completion.chunk", "created": 0,
                     "model": "test-model", "choices": [{"index": 0, "delta": {"content": "ok"}}]}
            return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                  content=f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n")
        return httpx.Response(200, json={
            "id": "test", "object": "chat.completion", "created": 0, "model": "test-model",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": "ok"}}],
        })

    def invoke(self, llm, stream=False):
        return llm.invoke([{"role": "user", "content": "test"}], stream=stream)

    def test_default_retains_two_sdk_retries(self):
        llm = self.make_llm()
        self.transport.side_effect = [httpx.Response(503), httpx.Response(503), self.success(False)]
        self.assertEqual(self.invoke(llm), "ok")
        self.assertEqual(self.transport.call_count, 3)

    def test_configured_budget_applies_to_both_response_modes(self):
        llm = self.make_llm(3)
        for stream in (False, True):
            with self.subTest(stream=stream):
                self.transport.reset_mock()
                self.transport.side_effect = [httpx.Response(504) for _ in range(3)] + [self.success(stream)]
                self.assertEqual(self.invoke(llm, stream), "ok")
                self.assertEqual(self.transport.call_count, 4)

    def test_exhaustion_does_not_add_an_application_retry_loop(self):
        llm = self.make_llm(1)
        self.transport.side_effect = lambda request: httpx.Response(502)
        with self.assertRaises(openai.InternalServerError):
            self.invoke(llm)
        self.assertEqual(self.transport.call_count, 2)

    def test_zero_disables_sdk_retries(self):
        llm = self.make_llm(0)
        self.transport.side_effect = lambda request: httpx.Response(503)
        with self.assertRaises(openai.InternalServerError):
            self.invoke(llm)
        self.assertEqual(self.transport.call_count, 1)
        self.sleep.assert_not_called()

    def test_bad_request_and_auth_errors_are_not_retried(self):
        llm = self.make_llm(3)
        for status in (400, 401, 403):
            with self.subTest(status=status):
                self.transport.reset_mock()
                self.transport.side_effect = lambda request: httpx.Response(status)
                with self.assertRaises(openai.APIStatusError):
                    self.invoke(llm)
                self.assertEqual(self.transport.call_count, 1)
        self.sleep.assert_not_called()

    def test_rate_limit_respects_retry_after(self):
        llm = self.make_llm(1)
        self.transport.side_effect = [httpx.Response(429, headers={"retry-after": "2"}), self.success(False)]
        self.assertEqual(self.invoke(llm), "ok")
        self.sleep.assert_called_once_with(2.0)

    def test_transport_failures_can_recover(self):
        llm = self.make_llm(1)
        for error in (httpx.ConnectError, httpx.ReadTimeout):
            with self.subTest(error=error.__name__):
                self.transport.reset_mock()
                self.transport.side_effect = [error("temporary failure"), self.success(False)]
                self.assertEqual(self.invoke(llm), "ok")
                self.assertEqual(self.transport.call_count, 2)

    def test_invalid_configuration_fails_before_client_creation(self):
        for value in ("-1", "1.5", "invalid", ""):
            with self.subTest(value=value), patch.object(llm_service, "OpenAI") as constructor:
                os.environ["LLM_MAX_RETRIES"] = value
                with self.assertRaisesRegex(ValueError, "LLM_MAX_RETRIES"):
                    llm_service.get_llm()
                constructor.assert_not_called()
                self.assertIsNone(llm_service._llm_instance)

    def test_partial_stream_is_not_replayed(self):
        class InterruptedStream(httpx.SyncByteStream):
            def __iter__(self):
                yield b'data: {"choices":[{"index":0,"delta":{"content":"partial"}}]}\n\n'
                raise httpx.ReadError("stream interrupted")

        llm = self.make_llm(3)
        self.transport.side_effect = lambda request: httpx.Response(
            200, headers={"content-type": "text/event-stream"}, stream=InterruptedStream(),
        )
        with self.assertRaises(httpx.ReadError):
            self.invoke(llm, stream=True)
        self.assertEqual(self.transport.call_count, 1)
        self.sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
