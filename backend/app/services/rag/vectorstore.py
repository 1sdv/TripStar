"""ChromaDB 本地持久化封装。

两个 collection 与原「觅途」项目保持一致（已拷贝其数据，勿改名）：
    posts     —— UGC 游记切块（社区知识库，社区热度 like_count 用于排序破平局）
    authority —— 权威底库（景点/路线，UGC 检索不足时兜底补位）

向量由 BAAI/bge-m3 写入、1024 维、cosine 距离；查询侧必须使用同一模型。
"""

import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...config import get_settings

COLLECTION_POSTS = "posts"
COLLECTION_AUTHORITY = "authority"

_DEFAULT_CHROMA_DIR = Path(__file__).resolve().parents[3] / "data" / "chroma"

_store: Optional["VectorStore"] = None
_lock = threading.Lock()


def resolve_chroma_dir() -> Path:
    """知识库目录：CHROMA_DIR 优先（相对路径按 backend/ 解析），否则 backend/data/chroma。"""
    configured = (get_settings().chroma_dir or "").strip()
    if not configured:
        return _DEFAULT_CHROMA_DIR
    path = Path(configured)
    if path.is_absolute():
        return path
    return (Path(__file__).resolve().parents[3] / path).resolve()


class VectorStore:
    """ChromaDB 封装；所有方法同步阻塞，调用方负责放进线程（asyncio.to_thread）。"""

    def __init__(self) -> None:
        import chromadb

        self._client = chromadb.PersistentClient(path=str(resolve_chroma_dir()))
        self._collections = {
            name: self._client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
            for name in (COLLECTION_POSTS, COLLECTION_AUTHORITY)
        }

    def _collection(self, name: str):
        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    def count(self, collection: str = COLLECTION_POSTS) -> int:
        return self._collection(collection).count()

    def add_chunks(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        collection: str = COLLECTION_POSTS,
    ) -> None:
        self._collection(collection).add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def upsert_chunks(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        collection: str = COLLECTION_POSTS,
    ) -> None:
        """写入或覆盖同 id 的 chunk —— 灌库脚本用，保证重复灌入幂等。"""
        self._collection(collection).upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def get_by_ids(
        self,
        ids: List[str],
        collection: str = COLLECTION_POSTS,
    ) -> List[Dict[str, Any]]:
        """按 id 查询已有条目，用于灌库前去重统计。"""
        if not ids:
            return []
        result = self._collection(collection).get(ids=ids, include=["metadatas"])
        found = result.get("ids") or []
        return [{"id": i, "meta": result.get("metadatas", [])[index]} for index, i in enumerate(found)]

    def delete_by_post_id(
        self,
        post_id: int,
        collection: str = COLLECTION_POSTS,
    ) -> int:
        """删除某篇文档的全部 chunk，返回删除数量（用于覆盖式重灌）。"""
        collection_obj = self._collection(collection)
        existing = collection_obj.get(where={"post_id": int(post_id)}, include=[])
        ids = existing.get("ids") or []
        if ids:
            collection_obj.delete(ids=ids)
        return len(ids)

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        collection: str = COLLECTION_POSTS,
        filter_destinations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """向量检索；filter_destinations 非空时在 Chroma 层按目的地元数据过滤。"""
        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": max(1, top_k),
            "include": ["documents", "metadatas", "distances"],
        }
        if filter_destinations:
            kwargs["where"] = {"destination": {"$in": list(filter_destinations)}}
        return self._collection(collection).query(**kwargs)

    def search_document(
        self,
        needle: str,
        limit: int,
        collection: str = COLLECTION_POSTS,
        filter_destinations: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """字面过滤检索（Chroma where_document 下推），返回 [{id, doc, meta}]。

        用于关键词检索：避免把全量 chunk 拉进内存再打分。
        """
        kwargs: Dict[str, Any] = {
            "where_document": {"$contains": needle},
            "include": ["documents", "metadatas"],
            "limit": max(1, limit),
        }
        if filter_destinations:
            kwargs["where"] = {"destination": {"$in": list(filter_destinations)}}
        result = self._collection(collection).get(**kwargs)
        ids = result.get("ids") or []
        docs = result.get("documents") or []
        metas = result.get("metadatas") or []
        return [
            {"id": ids[i], "doc": docs[i], "meta": metas[i]}
            for i in range(len(ids))
        ]

    def get_all(
        self,
        collection: str = COLLECTION_POSTS,
        filter_destinations: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """返回 chunks，元素 {id, doc, meta}。"""
        kwargs: Dict[str, Any] = {"include": ["documents", "metadatas"]}
        if filter_destinations:
            kwargs["where"] = {"destination": {"$in": list(filter_destinations)}}
        if limit:
            kwargs["limit"] = int(limit)
        result = self._collection(collection).get(**kwargs)
        ids = result.get("ids") or []
        docs = result.get("documents") or []
        metas = result.get("metadatas") or []
        return [
            {"id": ids[i], "doc": docs[i], "meta": metas[i]}
            for i in range(len(ids))
        ]

    def destinations(self, collection: str = COLLECTION_POSTS) -> List[str]:
        """已入库的目的地去重列表（用于城市名 → 库内目的地映射）。

        必须逐条确认「该 id 仍然存在」：Chroma 的 `get(include=["metadatas"])` 在
        `delete()` 之后仍可能返回已删行的元数据残留。若直接采信，会让
        `resolve_destinations()`（以及「探库」判断）以为某城市有覆盖，
        实际却检索不到任何内容，白走一条降级分支。
        """
        result = self._collection(collection).get(include=["metadatas"])
        ids = result.get("ids") or []
        metas = result.get("metadatas") or []

        candidates: Dict[str, List[str]] = {}
        for index, doc_id in enumerate(ids):
            meta = (metas[index] if index < len(metas) else None) or {}
            value = str(meta.get("destination", "")).strip()
            if value:
                candidates.setdefault(value, []).append(doc_id)

        if not candidates:
            return []

        # 批量校验存在性：每 100 个 id 一次请求，避免逐条 get 造成上百次往返
        def _alive(id_list: List[str]) -> set:
            found: set = set()
            for start in range(0, len(id_list), 100):
                chunk = id_list[start:start + 100]
                try:
                    got = self._collection(collection).get(ids=chunk, include=[])
                    found.update(got.get("ids") or [])
                except Exception:
                    # 校验失败时保守地认为其存在（宁可多探一次库，不要漏掉已灌城市）
                    found.update(chunk)
            return found

        alive: List[str] = []
        # 只校验每个目的地的前几个 id：删除是按 post_id 整篇删的，
        # 同目的地只要还有任一 chunk 存活就说明该城市仍有覆盖
        for value, id_list in candidates.items():
            if _alive(id_list[:3]):
                alive.append(value)
        return alive


def get_store() -> VectorStore:
    """返回 VectorStore 单例（首次调用会打开持久化目录）。"""
    global _store
    if _store is None:
        with _lock:
            if _store is None:
                _store = VectorStore()
    return _store


def reset_store() -> None:
    """重置单例（CHROMA_DIR 变更或测试时使用）。"""
    global _store
    with _lock:
        _store = None
