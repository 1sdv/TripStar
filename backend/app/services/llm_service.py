"""LLM服务模块"""

import os

import httpx
from openai import OpenAI
from ..config import get_settings

# 全局LLM实例
_llm_instance = None


def _clear_system_proxy_env() -> None:
    """清理系统级代理环境变量，避免 LLM / 其他非 Google 服务误继承代理配置。"""
    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        os.environ.pop(key, None)


class DirectOpenAILLM:
    """轻量 LLM 适配器，避免 HelloAgentsLLM 构造阶段自动继承系统代理。"""

    def __init__(self, model: str, api_key: str, base_url: str, timeout: int):
        self.provider = "openai-compatible"
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            http_client=httpx.Client(
                timeout=self.timeout,
                trust_env=False,
            ),
            default_headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )

    def invoke(self, messages, **kwargs):
        """兼容 HelloAgentsLLM 的核心接口，返回纯文本内容。"""
        response = self._client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens"),
            top_p=kwargs.get("top_p"),
            stop=kwargs.get("stop"),
        )
        choice = response.choices[0]
        content = getattr(choice.message, "content", None) or ""
        return content

    def __call__(self, messages, **kwargs):
        return self.invoke(messages, **kwargs)


def get_llm() -> DirectOpenAILLM:
    """
    获取LLM实例(单例模式)
    
    Returns:
        HelloAgentsLLM实例
    """
    global _llm_instance
    
    if _llm_instance is None:
        settings = get_settings()
        _clear_system_proxy_env()

        api_key = (
            settings.openai_api_key
            or os.getenv("LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or ""
        )
        base_url = (
            settings.openai_base_url
            or os.getenv("LLM_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        )
        model = (
            settings.openai_model
            or os.getenv("LLM_MODEL_ID")
            or os.getenv("OPENAI_MODEL")
            or "gpt-4"
        )
        timeout = int(os.getenv("LLM_TIMEOUT", "60"))

        _llm_instance = DirectOpenAILLM(
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
        
        print(f"✅ LLM服务初始化成功")
        print(f"   提供商: {_llm_instance.provider}")
        print(f"   模型: {_llm_instance.model}")
    
    return _llm_instance


def reset_llm():
    """重置LLM实例(用于测试或重新配置)"""
    global _llm_instance
    _llm_instance = None

