"""硅基流动 Rerank 精排封装（Cohere 兼容 /v1/rerank 端点）。

精排是**增强项**：调用失败时抛异常，由 retriever 降级回 RRF 融合结果，
保证任何 rerank 故障都不会阻塞行程生成。
"""

from typing import List

import httpx

from ...config import get_settings


def _rerank_url() -> str:
    """硅基流动的 rerank 端点是 {root}/v1/rerank，而 base_url 自带 /v1。"""
    base = (get_settings().embedding_base_url or "").rstrip("/")
    if base.endswith("/v1"):
        base = base[: -len("/v1")]
    return f"{base}/v1/rerank"


def rerank(query: str, documents: List[str], top_n: int | None = None) -> List[int]:
    """对候选文档重排，返回按相关性降序的原始下标列表。

    请求体：{"model", "query", "documents", "top_n"}（Cohere Rerank 兼容格式）
    响应：{"results": [{"index": 0, "relevance_score": 0.9}, ...]}
    """
    settings = get_settings()
    if not settings.embedding_api_key:
        raise RuntimeError(
            "缺少 EMBEDDING_API_KEY：请在 backend/.env 中配置硅基流动 Key"
            "（https://cloud.siliconflow.cn）。"
        )
    if not documents:
        return []

    payload: dict = {
        "model": settings.rerank_model,
        "query": query,
        "documents": documents,
    }
    if top_n is not None:
        payload["top_n"] = top_n

    with httpx.Client(timeout=settings.rerank_timeout, trust_env=False) as client:
        resp = client.post(
            _rerank_url(),
            headers={"Authorization": f"Bearer {settings.embedding_api_key}"},
            json=payload,
        )
    resp.raise_for_status()
    data = resp.json()

    results = data.get("results") or []
    # 服务端若乱序，这里再按 relevance_score 降序兜底
    results.sort(key=lambda r: -float(r.get("relevance_score", 0.0)))
    return [int(r["index"]) for r in results]
