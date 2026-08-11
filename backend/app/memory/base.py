"""记忆存储抽象基类"""
from abc import ABC, abstractmethod
from typing import List

from .data_model import MemoryItem


class BaseMemoryStore(ABC):
    """记忆存储接口，内存与 SQLite 实现均需遵守"""

    @abstractmethod
    async def save(self, user_id: str, item: MemoryItem) -> None:
        ...

    @abstractmethod
    async def list_all(self, user_id: str) -> List[MemoryItem]:
        ...

    @abstractmethod
    async def delete(self, user_id: str, memory_id: str) -> bool:
        ...

    @abstractmethod
    async def clear(self, user_id: str) -> None:
        ...
