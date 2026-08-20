"""从用户需求 + 生成行程中提取稳定旅行偏好并打分

复用项目 chat_service 的 LLM 直连方式（httpx 调用 OpenAI 兼容接口），
不依赖 hello_agents 的 Agent 机制，避免额外开销。
"""
import json
import os
from typing import List, Tuple

import httpx

from ..config import get_settings
from . import logger
from .memory_manager import MIN_INIT_WEIGHT

EXTRACT_PROMPT = """你需要从用户出行需求和最终生成的旅行行程中，提炼用户稳定旅行偏好。
规则：
1. 只提取长期稳定偏好，临时目的地、单次短期安排不要提取
2. 每条偏好附带重要性分数（0~10），分数越高代表用户长期习惯越强
3. 输出JSON数组，结构示例：
[
    {{"content": "偏爱小众自然景点", "score": 7.2}},
    {{"content": "住宿偏好民宿", "score": 6.5}}
]
4. 没有稳定偏好返回空数组[]
只返回纯JSON，禁止额外解释文字。

用户原始需求：
{user_query}
生成行程内容：
{trip_content}
"""


def _get_llm_config() -> dict:
    """按请求实时读取 LLM 配置，支持设置页热更新（与 chat_service 一致）"""
    settings = get_settings()
    api_key = (
        settings.openai_api_key
        or os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    )
    base_url = (
        settings.openai_base_url
        or os.getenv("LLM_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    )
    model_id = (
        settings.openai_model
        or os.getenv("LLM_MODEL_ID")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4"
    )
    timeout = int(os.getenv("LLM_TIMEOUT", "120"))
    return {
        "api_key": api_key.strip(),
        "base_url": base_url.rstrip("/"),
        "model_id": model_id.strip(),
        "timeout": timeout,
    }


class PreferenceExtractor:
    """行程结束后调用 LLM 提取偏好，返回 (内容, 分数) 列表"""

    async def extract_preferences(
        self, user_query: str, trip_content: str
    ) -> List[Tuple[str, float]]:
        cfg = _get_llm_config()
        if not cfg["api_key"]:
            logger.warning("[ExtractPrefs] LLM API Key 未配置，跳过偏好提取")
            return []

        prompt = EXTRACT_PROMPT.format(
            user_query=user_query, trip_content=trip_content[:6000]
        )
        messages = [
            {"role": "system", "content": "你是一个旅行偏好分析助手，只输出JSON。"},
            {"role": "user", "content": prompt},
        ]
        payload = {
            "model": cfg["model_id"],
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 800,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        }
        url = f"{cfg['base_url']}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=cfg["timeout"]) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            text = data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"[ExtractPrefsFailed] LLM 调用失败: {e}")
            return []

        try:
            parsed = json.loads(text)
        except Exception as e:
            logger.warning(f"[ExtractPrefsFailed] JSON 解析失败: {e}, raw={text[:200]}")
            return []

        raw_result: List[Tuple[str, float]] = []
        for item in parsed if isinstance(parsed, list) else []:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content", "")).strip()
            try:
                score = float(item.get("score", 0))
            except (TypeError, ValueError):
                score = 0.0
            if content:
                raw_result.append((content, score))

        logger.debug(f"[ExtractRawPrefs] raw count={len(raw_result)}")
        filtered: List[Tuple[str, float]] = []
        for content, score in raw_result:
            if score < MIN_INIT_WEIGHT:
                logger.info(
                    f"[PrefFilterDrop] score={score:.2f} < limit {MIN_INIT_WEIGHT}, content={content}"
                )
            else:
                filtered.append((content, score))
        logger.info(f"[ExtractPrefs] after filter keep={len(filtered)}")
        return filtered
