"""景点数据源调度：小红书 → 本地 RAG 知识库 → 通用常识，三级降级。

为什么需要它
------------
原先 `plan_trip` 直接裸调 `search_xhs_attractions`，小红书 Cookie 一旦过期
（code=-100）或触发风控，异常会一路冒到任务层，整个行程生成直接失败。
本模块把「景点数据」变成一条有备胎的链路，保证**永远返回可用文本**。

三级链路
--------
① 小红书原生搜索（数据最新、含真实避坑/预约信息）
     ↓ 异常 / 空结果 / 提纯失败
② 本地 RAG 知识库（已入库游记，离线可用、不受 Cookie 影响）
     ↓ 库中无该城市 / 检索空 / 提纯失败
③ 通用常识兜底（让原 Planner 的「信息不足时按常识补齐」规则接管）

设计要点
--------
* **先探库再调 LLM**：命中不到城市时直接跳到 ③，不做注定无用的提纯调用。
* **提纯复用同一份 Prompt**：`_extract_attractions_from_text` 由 XHS 与 RAG 共用，
  只有接地约束措辞不同，避免两条路径的字段与地理编码逻辑漂移。
* **不抛异常**：所有故障都转成返回值，由调用方按来源标签决定后续处理。
"""

from typing import List, Optional, Tuple

from . import metrics
from .xhs_service import (
    XHSCookieExpiredError,
    XHSFetchError,
    _extract_attractions_from_text,
    format_attractions_block,
    search_xhs_attractions,
)

# 来源标签（同时用于日志、进度提示与 Planner 上下文抬头）
SOURCE_XHS = "小红书"
SOURCE_RAG = "本地知识库"
SOURCE_GENERIC = "通用常识"

# RAG 挖景点时的检索规模：比「事实层」注入更宽，尽量覆盖足够多的景点
_RAG_EXTRACT_TOP_K = 10
_RAG_EXTRACT_CANDIDATE_MULT = 6

_RAG_GROUNDING_RULE = """**严格的接地约束（必须遵守）:**
1. 你**只能**从下面给出的游记片段中提取真实被提到的景点，**严禁编造**片段里没有的景点；
2. 片段中未提及的景点一律不要输出；
3. 如果片段里只提到了 1 个景点，就只返回 1 个，不要凑数；
4. 景点的时长、是否需预约等信息，只能依据片段内容判断，片段没提及就填默认值
   （duration 填 120，reservation_required 填 false，reservation_tips 填空字符串）。"""


def _city_has_kb_coverage(city: str) -> bool:
    """探测知识库中是否存在该城市的游记（零 LLM 成本的快速判断）。"""
    try:
        from .rag import resolve_destinations

        return bool(resolve_destinations(city))
    except Exception as e:
        print(f"  ⚠️ [景点调度] 知识库覆盖探测失败: {type(e).__name__}: {e}")
        return False


def _try_xhs(city: str, keywords: str, language: str) -> Tuple[Optional[str], str]:
    """尝试小红书路径。返回 (文本或 None, 失败原因)。"""
    try:
        text = search_xhs_attractions(city, keywords, language)
    except XHSCookieExpiredError as e:
        return None, f"小红书 Cookie 已被风控拦截：{e}"
    except XHSFetchError as e:
        return None, f"小红书抓取失败：{e}"
    except Exception as e:
        return None, f"小红书异常：{type(e).__name__}: {e}"

    # 成功返回但内容不可用（空串 / 未检索到 / 提纯失败）也算失败，继续降级
    if not text or "未在小红书检索到" in text or "提取小红书结构化数据失败" in text:
        return None, "小红书未返回可用景点数据"
    return text, ""


def _try_rag(city: str, keywords: str, language: str) -> Tuple[Optional[str], str]:
    """尝试本地知识库路径：检索游记 → LLM 提纯 → 补坐标。返回 (文本或 None, 失败原因)。"""
    try:
        from .rag import collect_city_notes, rag_available

        available, reason = rag_available()
        if not available:
            return None, f"知识库不可用（{reason}）"

        if not _city_has_kb_coverage(city):
            return None, f"知识库中暂无「{city}」的游记"

        notes = collect_city_notes(
            city,
            [keywords] if keywords else None,
            top_k=_RAG_EXTRACT_TOP_K,
            candidate_mult=_RAG_EXTRACT_CANDIDATE_MULT,
        )
        if not notes:
            return None, f"知识库检索「{city}」无命中"

        items = _extract_attractions_from_text(
            notes,
            city,
            source_label="本地知识库中的真实游记片段",
            grounding_rule=_RAG_GROUNDING_RULE,
            language=language,
        )
        if not items:
            return None, "知识库提纯未产出景点（片段中可能没有明确景点）"

        print(f"  ✅ [景点调度] 知识库路径命中 {len(items)} 个景点（{city}）")
        return format_attractions_block(items, city, SOURCE_RAG, language), ""
    except Exception as e:
        return None, f"知识库路径异常：{type(e).__name__}: {e}"


def _generic_fallback(city: str, keywords: str, failures: List[str], language: str) -> str:
    """通用常识兜底：无法获取实时数据时，让 Planner 的常识补齐规则接管。"""
    detail = "；".join(failures) if failures else "无可用数据源"
    print(f"  ⚠️ [景点调度] {city} 两条数据源均失败 → 通用常识兜底（{detail}）")
    return (
        f"【{city} 景点数据来源：通用常识】\n"
        f"小红书与本地知识库均未能提供 {city} 的景点数据（原因：{detail}）。\n"
        f"请基于你对该城市{('与' + keywords) if keywords else ''}的通用认知安排经典景点，"
        f"并注意：坐标可能不准确、门票与预约信息需用户自行核实，"
        f"请在 description 或 reservation_tips 中明确提示需自行确认。\n"
    )


def search_attractions(
    city: str,
    keywords: str = "景点",
    language: str = "zh",
) -> Tuple[str, str]:
    """按三级降级链获取景点数据。

    与 `search_xhs_attractions` 的调用形态一致，但**永不抛异常**。

    Args:
        city: 城市名
        keywords: 偏好关键词（由 request.preferences[0] 传入）
        language: 目标输出语言

    Returns:
        (回传给 Planner 的文本块, 数据来源标签)
    """
    failures: List[str] = []

    # ---------- ① 小红书 ----------
    text, reason = _try_xhs(city, keywords, language)
    if text:
        print(f"  ✅ [景点调度] {city} 使用小红书数据")
        metrics.record_source("attraction", SOURCE_XHS)
        return text, SOURCE_XHS
    failures.append(reason)
    metrics.record_degradation(f"attraction/xhs: {reason}")
    print(f"  ⚠️ [景点调度] {city} 小红书路径不可用（{reason}），降级到本地知识库...")

    # ---------- ② 本地 RAG 知识库 ----------
    text, reason = _try_rag(city, keywords, language)
    if text:
        metrics.record_source("attraction", SOURCE_RAG)
        return text, SOURCE_RAG
    failures.append(reason)
    metrics.record_degradation(f"attraction/rag: {reason}")
    print(f"  ⚠️ [景点调度] {city} 知识库路径不可用（{reason}），降级到通用常识...")

    # ---------- ③ 通用常识 ----------
    metrics.record_source("attraction", SOURCE_GENERIC)
    return _generic_fallback(city, keywords, failures, language), SOURCE_GENERIC
