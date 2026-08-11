"""记忆条目数据模型"""
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class MemoryItem:
    """单条用户偏好记忆"""
    memory_id: str
    content: str          # 偏好文本，如"偏爱小众自然景点"
    source: str           # explicit=用户手动添加 / implicit=LLM自动提取
    weight: float         # 权重 [0, 10]
    create_time: float
    last_access_time: float

    @classmethod
    def create(cls, content: str, source: str, init_weight: float) -> "MemoryItem":
        now = time.time()
        return cls(
            memory_id=str(uuid.uuid4()),
            content=content.strip(),
            source=source,
            weight=init_weight,
            create_time=now,
            last_access_time=now,
        )

    def update_access(self) -> None:
        self.last_access_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "MemoryItem":
        return MemoryItem(**d)
