"""RAG 检索能力：BGE-M3 向量化 + ChromaDB 混合检索 + rerank 精排。

模块划分与原「觅途」项目保持一致：
    embedding   —— 硅基流动 BGE-M3 向量化（必须与建库模型一致）
    vectorstore —— ChromaDB 持久化封装（posts 社区游记 / authority 权威底库）
    rerank      —— 硅基流动 bge-reranker 精排（增强项，失败自动降级）
    retriever   —— 向量 + 关键词 RRF 融合 → 热度破平局 → 精排 → 去重 → 权威兜底

对 TripStar 的适配点（与原项目不同之处）：
1. 配置全部走 app.config.get_settings()，不再有 import 期强校验；
2. 关键词检索在 Chroma 层用 where_document 下推字面过滤，避免把全量 chunk 拉进内存；
3. 多城市场景下 destinations 通常按「省+市」存储（如 "云南大理"），因此新增
   filter_destinations 参数把两路召回都限定在匹配到的目的地内，防止 A 城行程被
   B 城游记污染；
4. 抽掉对 Java 后端 / HMAC 审核链路的全部依赖。

设计原则：RAG 是增强项。任何一环不可用（未配 Key、库为空、rerank 报错）都静默降级，
由调用方捕获异常后跳过，绝不阻塞行程生成主流程。
"""

from .retriever import (
    COLLECTION_AUTHORITY,
    COLLECTION_POSTS,
    collect_city_notes,
    resolve_destinations,
    retrieve,
    retrieve_notes_for_city,
    rag_available,
)
from .embedding import embed_text, embed_texts
from .rerank import rerank
from .vectorstore import get_store

__all__ = [
    "COLLECTION_AUTHORITY",
    "COLLECTION_POSTS",
    "collect_city_notes",
    "embed_text",
    "embed_texts",
    "get_store",
    "rag_available",
    "rerank",
    "resolve_destinations",
    "retrieve",
    "retrieve_notes_for_city",
]
