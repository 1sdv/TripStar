"""用户偏好记忆模块

带权重的用户专属旅行偏好记忆，支持：
- LLM 自动提取偏好并打分，低于准入门槛不入库
- 权重随时间惰性衰减，低于遗忘阈值自动删除
- 相同偏好权重合并，上限 10.0
- TOP-K 召回 + 单条长度截断，防止 Prompt 膨胀
- 内存 / SQLite 两种存储，可通过环境变量切换
"""
import logging

logger = logging.getLogger("tripstar.memory")

from .memory_manager import MemoryManager
from .preference_extractor import PreferenceExtractor
from .data_model import MemoryItem

__all__ = ["MemoryManager", "PreferenceExtractor", "MemoryItem", "logger"]
