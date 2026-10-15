"""硅基流动 BGE-M3 向量化封装（OpenAI 兼容 /embeddings 端点）。

与原项目行为严格一致：不加任何 instruction 前缀、不改写文本。
现有知识库由该模型（1024 维）写入，查询侧必须用完全相同的方式向量化，
否则会因向量空间不一致导致检索失效。
"""

import threading
from typing import List

from openai import OpenAI

from ...config import get_settings

_client = None
_lock = threading.Lock()


def _get_client() -> OpenAI:
    """惰性创建 embedding 客户端（单例）。"""
    global _client
    settings = get_settings()
    if not settings.embedding_api_key:
        raise RuntimeError(
            "缺少 EMBEDDING_API_KEY：请在 backend/.env 中配置硅基流动 Key"
            "（https://cloud.siliconflow.cn），或关闭 RAG 注入。"
        )
    if _client is None:
        with _lock:
            if _client is None:
                _client = OpenAI(
                    api_key=settings.embedding_api_key,
                    base_url=settings.embedding_base_url.rstrip("/"),
                )
    return _client


def reset_client() -> None:
    """重置客户端（运行时配置变更后调用）。"""
    global _client
    with _lock:
        _client = None


def embed_texts(texts: List[str]) -> List[List[float]]:
    """批量向量化，返回与输入顺序一致的向量列表。"""
    if not texts:
        return []
    response = _get_client().embeddings.create(
        model=get_settings().embedding_model,
        input=texts,
    )
    ordered = sorted(response.data, key=lambda item: item.index)
    return [item.embedding for item in ordered]


def embed_text(text: str) -> List[float]:
    """单条文本向量化。"""
    vectors = embed_texts([text])
    if not vectors:
        raise RuntimeError("向量化返回为空")
    return vectors[0]
