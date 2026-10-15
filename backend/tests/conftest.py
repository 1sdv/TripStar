"""pytest 公共夹具。

原则：测试**不依赖网络、不依赖真实 LLM、不写真实知识库**。
需要外部资源的地方一律用 fake / monkeypatch 替换，保证测试可离线反复运行。
"""

import sys
from pathlib import Path

import pytest

# 让 `import app.xxx` 可用（backend/ 加入 sys.path）
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(scope="session")
def planner():
    """未初始化外部依赖的 MultiAgentTripPlanner 实例。

    用 `__new__` 绕过 `__init__`（它会连 MCP、建 LLM 客户端、读环境变量），
    只用于测试纯字符串/纯逻辑方法。
    """
    from app.agents.trip_planner_agent import MultiAgentTripPlanner

    return MultiAgentTripPlanner.__new__(MultiAgentTripPlanner)


@pytest.fixture
def trip_request_factory():
    """构造 TripRequest 的工厂，避免每个用例重复写必填字段。"""
    from app.models.schemas import CityStay, TripRequest

    def _make(cities=None, **overrides):
        cities = cities or [("大理", 3)]
        payload = {
            "city": "",
            "cities": [CityStay(city=c, days=d) for c, d in cities],
            "start_date": "2026-05-01",
            "end_date": "2026-05-03",
            "travel_days": sum(d for _, d in cities),
            "transportation": "公共交通",
            "accommodation": "经济型酒店",
            "preferences": ["自然风光"],
            "free_text_input": "",
            "language": "zh",
        }
        payload.update(overrides)
        return TripRequest(**payload)

    return _make
