"""内存存储实现（默认，服务重启后记忆丢失）"""
from typing import Dict, List

from .base import BaseMemoryStore
from .data_model import MemoryItem


class InMemoryStore(BaseMemoryStore):
    def __init__(self) -> None:
        # key: user_id -> {memory_id: MemoryItem}
        self._storage: Dict[str, Dict[str, MemoryItem]] = {}

    async def save(self, user_id: str, item: MemoryItem) -> None:
        self._storage.setdefault(user_id, {})[item.memory_id] = item

    async def list_all(self, user_id: str) -> List[MemoryItem]:
        return list(self._storage.get(user_id, {}).values())

    async def delete(self, user_id: str, memory_id: str) -> bool:
        bucket = self._storage.get(user_id, {})
        if memory_id in bucket:
            del bucket[memory_id]
            return True
        return False

    async def clear(self, user_id: str) -> None:
        if user_id in self._storage:
            self._storage[user_id].clear()
