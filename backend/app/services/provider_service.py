"""天气 / 酒店数据源调度：Agent（MCP 工具）优先，高德 REST 兜底。

为什么需要它
------------
原先 `plan_trip` 直接调用 `weather_agent.run()` / `hotel_agent.run()`，这两个
Agent 的唯一工具是 `MCPTool(["uvx", "amap-mcp-server"])`。实测该 MCP 服务器
依赖旧版 pydantic（`eval_type_backport` 在 2.12 被移除），**进程启动即崩**，
而 hello_agents 的 `_discover_tools()` 把异常静默吞掉导致工具发现为空——
于是每次调用都返回「未找到工具 `amap_maps_weather`」，天气与酒店数据全程缺失，
最终由 LLM 用常识编造。

本模块把天气/酒店也变成有备胎的链路：

① Agent 调用 MCP 工具（首选，能拿到带评分的完整 POI / 逐日预报）
     ↓ MCP 未注册 / 调用报错 / 返回空或错误文案
② 高德 Web 服务 REST 直连（amap_rest_service）
     ↓ Key 未配置 / 接口失败 / 无结果
③ 显式失败文案（提示 Planner 按常识补齐，不编造具体数值）

**关键优化**：初始化阶段就探测 MCP 工具是否真的注册成功（`_probe_mcp_tools`），
未注册时跳过 Agent，省掉「一次注定失败的 LLM 调用 + 一次错误文案回合」。

降级原则：weather/hotel 是**非关键信息**，任何失败都不应打断行程生成；
③ 的文案本身就是给 Planner 的指令。
"""

import asyncio
from typing import List, Optional, Tuple

from ..config import get_settings
from . import metrics
from .amap_rest_service import (
    format_weather_block,
    get_weather_forecast,
    search_hotels_rest,
)

SOURCE_MCP = "MCP 工具"
SOURCE_REST = "高德 REST"
SOURCE_NONE = "不可用"

# 判断 Agent 回复是否属于「失败话术」而非真实数据。
#
# 关键取舍：**不能**把「抱歉」「没有找到」这类泛化词单独作为判据——
# 真实天气/酒店文案里完全可能出现「抱歉，该酒店暂无评分」，那样会被误判为
# 工具失败并触发一次无谓降级（多打一次 REST、多记一次降级指标）。
# 因此只匹配**明确指向工具/调用失败**的特征串。
_FAILURE_MARKERS = (
    "未找到工具", "未找到名为", "没有名为", "工具不存在", "工具未注册",
    "工具当前不可用", "工具暂时无法", "工具调用失败", "系统返回的错误",
    "系统未能找到", "无法调用工具", "tool not found", "tool_call failed",
)

# 这些词单独出现不足以判失败，只有「软失败词 + 完全没有可验证数据特征」才算失败。
_SOFT_FAILURE_HINTS = ("无法", "暂时无法", "无法获取", "无法查询")

# 可验证的「真实数据」特征：任一命中即认为这次调用确实取到了内容。
# 覆盖天气（日期/温度/风力）与酒店（价格/评分/人均）两类结果形态。
_DATA_PATTERNS = (
    r"\d{4}-\d{2}-\d{2}",                     # 日期
    r"-?\d+\s*(?:°|℃|度)",                    # 温度（也兼容「220 度」这类误写）
    r"(?:人均|价格|评分|费用)\s*[:：]?\s*\d",  # 酒店结构化字段
    r"\d+\s*(?:元|块|¥|￥)",                   # 价格
    r"白天|夜间",                              # 天气描述
    r"级|风\s*\d",                             # 风力
)


def _looks_like_failure(text: str) -> bool:
    """粗判 Agent 输出是否为失败话术。

    判定顺序：
    1. 空文本 → 失败
    2. 命中明确的工具失败特征（「未找到工具」等）→ 失败
    3. 命中软失败词，且**完全没有**可验证数据特征 → 失败
    4. 其余 → 成功

    这样既能拦住「抱歉，工具不可用」这类真失败，
    又不会把「抱歉让您久等，大理 2026-10-15 白天晴 23°C」这种带数据的有效结果误判掉。
    """
    if not text or not text.strip():
        return True

    lowered = text.lower()
    if any(marker.lower() in lowered for marker in _FAILURE_MARKERS):
        return True

    if not any(hint in text for hint in _SOFT_FAILURE_HINTS):
        return False

    import re

    return not any(re.search(pattern, text) for pattern in _DATA_PATTERNS)


def probe_mcp_tools(agent) -> bool:
    """探测某个 Agent 是否真的注册到了可调用的工具。

    `SimpleAgent.list_tools()` 返回的是**工具名字符串列表**（见 hello_agents
    registry.list_tools）。若 MCP 展开成功，名字会是 `amap_maps_weather` 这类子工具名；
    若展开失败，就只剩父工具名 `amap`——据此判断 MCP 是否可用。
    """
    try:
        names = agent.list_tools() or []
        return bool(names) and not (len(names) == 1 and names[0] == "amap")
    except Exception:
        return False


def _rest_key_available() -> bool:
    return bool(get_settings().vite_amap_web_key)


# ============ 天气 ============

def _weather_via_rest(city: str, start_date: str = "", end_date: str = "") -> Optional[str]:
    """高德 REST 天气。返回文本；无法获取返回 None。"""
    if not _rest_key_available():
        return None
    casts = get_weather_forecast(city)
    if not casts:
        return None
    return format_weather_block(city, casts, start_date=start_date, end_date=end_date)


async def get_weather(
    city: str,
    weather_agent,
    mcp_ready: bool,
    start_date: str = "",
    end_date: str = "",
) -> Tuple[str, str]:
    """获取城市天气（Agent 优先 → REST 兜底）。

    Args:
        start_date / end_date: 行程日期，用于剔除与行程不重叠的预报

    Returns:
        (天气文本, 数据来源标签)
    """
    if mcp_ready:
        try:
            query = f"请查询{city}的天气信息"
            response = await asyncio.to_thread(weather_agent.run, query)
            if not _looks_like_failure(response):
                metrics.record_source("weather", SOURCE_MCP)
                return response, SOURCE_MCP
            metrics.record_degradation(f"weather/mcp: 返回失败话术 ({city})")
            print(f"  ⚠️ [天气调度] {city} Agent 返回失败话术，降级到高德 REST...")
        except Exception as e:
            metrics.record_degradation(f"weather/mcp: {type(e).__name__} ({city})")
            print(f"  ⚠️ [天气调度] {city} Agent 调用异常（{type(e).__name__}: {e}），降级到高德 REST...")
    else:
        print(f"  ℹ️ [天气调度] {city} MCP 工具未注册，直接使用高德 REST")

    rest_text = await asyncio.to_thread(_weather_via_rest, city, start_date, end_date)
    if rest_text:
        print(f"  ✅ [天气调度] {city} 使用高德 REST 天气数据")
        metrics.record_source("weather", SOURCE_REST)
        return rest_text, SOURCE_REST

    detail = "MCP 工具未注册且高德 REST 未取到数据" if not mcp_ready else "MCP 与高德 REST 均失败"
    print(f"  ⚠️ [天气调度] {city} 天气数据不可用（{detail}）")
    metrics.record_source("weather", SOURCE_NONE)
    metrics.record_degradation(f"weather/none: {city}")
    return (
        f"【{city} 天气数据不可用】{detail}。"
        f"请按该城市该季节的常见气候给出保守提醒（如防晒/保暖），不要编造具体温度数值。",
        SOURCE_NONE,
    )


# ============ 酒店 ============

async def get_hotels(
    city: str,
    accommodation: str,
    hotel_agent,
    mcp_ready: bool,
) -> Tuple[str, str]:
    """获取城市住宿推荐（Agent 优先 → REST 兜底）。

    Returns:
        (酒店文本, 数据来源标签)
    """
    if mcp_ready:
        try:
            query = f"请搜索{city}的{accommodation}酒店"
            response = await asyncio.to_thread(hotel_agent.run, query)
            if not _looks_like_failure(response):
                metrics.record_source("hotel", SOURCE_MCP)
                return response, SOURCE_MCP
            metrics.record_degradation(f"hotel/mcp: 返回失败话术 ({city})")
            print(f"  ⚠️ [酒店调度] {city} Agent 返回失败话术，降级到高德 REST...")
        except Exception as e:
            metrics.record_degradation(f"hotel/mcp: {type(e).__name__} ({city})")
            print(f"  ⚠️ [酒店调度] {city} Agent 调用异常（{type(e).__name__}: {e}），降级到高德 REST...")
    else:
        print(f"  ℹ️ [酒店调度] {city} MCP 工具未注册，直接使用高德 REST")

    rest_text = await asyncio.to_thread(search_hotels_rest, city, accommodation)
    if rest_text:
        print(f"  ✅ [酒店调度] {city} 使用高德 REST 住宿数据")
        metrics.record_source("hotel", SOURCE_REST)
        return rest_text, SOURCE_REST

    detail = "MCP 工具未注册且高德 REST 未取到数据" if not mcp_ready else "MCP 与高德 REST 均失败"
    print(f"  ⚠️ [酒店调度] {city} 住宿数据不可用（{detail}）")
    metrics.record_source("hotel", SOURCE_NONE)
    metrics.record_degradation(f"hotel/none: {city}")
    return (
        f"【{city} 住宿数据不可用】{detail}。"
        f"请按「{accommodation}」的常见档位推荐住宿区域（如市中心、景区周边）与价格区间，"
        f"不要编造具体酒店名称与确切价格，并提示用户自行预订核实。",
        SOURCE_NONE,
    )
