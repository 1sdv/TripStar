"""
AI 行程问答服务
基于 httpx 直接调用 OpenAI 兼容的 Chat Completions API，
将当前旅行计划作为上下文注入,实现针对行程的智能问答
"""

import os
import json
import httpx
from typing import List, Optional, Dict, Any
from ..config import get_settings

# ============ System Prompt ============
SYSTEM_PROMPT = """你是一个专业且贴心的私人旅行管家「旅途星辰AI」。

你当前正在为用户提供关于一份 **已生成的旅行计划** 的答疑服务。
用户可能会问你关于行程中的景点、酒店、餐饮、天气、交通、门票、费用等任何细节问题。

请根据下方提供的【当前旅行计划】JSON 上下文来回答用户的问题。
回答规则：
1. 如果行程数据中包含相关信息，请精确引用并给出详细回答。
2. 如果行程数据中没有明确信息，可以基于常识进行合理推断，但需说明"行程中未提供该信息，以下是建议"。
3. 回答要有温度、条理清晰，适当使用 emoji 增加亲切感 🌟。
4. 回答尽量简洁，控制在200字以内，除非用户要求详细展开。
5. 使用中文回答。"""


def _get_llm_runtime_config() -> Dict[str, Any]:
    """按请求实时读取 LLM 配置，支持前端设置页热更新。"""
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


# 上下文体积上限：行程 JSON 与历史对话都不能无限增长，否则每次提问的 token 成本失控
_MAX_CONTEXT_CHARS = 12000
_MAX_HISTORY_MESSAGES = 10


def _build_context_message(trip_plan_dict: Dict[str, Any]) -> str:
    """将旅行计划转化为上下文文本"""
    plan_json = json.dumps(trip_plan_dict, ensure_ascii=False, indent=2)
    if len(plan_json) > _MAX_CONTEXT_CHARS:
        plan_json = plan_json[:_MAX_CONTEXT_CHARS] + "\n...(行程数据过长，已截断)"
    return f"【当前旅行计划】\n```json\n{plan_json}\n```"


async def chat_with_trip_context(
    message: str,
    trip_plan_dict: Dict[str, Any],
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    使用 LLM 回答关于当前行程的用户提问

    Args:
        message: 用户的提问
        trip_plan_dict: 当前旅行计划 (dict 格式)
        history: 可选的历史对话 [{"role": "user"/"assistant", "content": "..."}]

    Returns:
        AI 的回复文本
    """
    # 构造消息列表
    llm_config = _get_llm_runtime_config()
    if not llm_config["api_key"]:
        return "抱歉，AI 服务尚未配置 API Key，请先在设置页面中完成配置。"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_context_message(trip_plan_dict)},
    ]

    # 追加历史对话（只保留最近若干轮，避免上下文无限增长）
    if history:
        for item in history[-_MAX_HISTORY_MESSAGES:]:
            messages.append({
                "role": item.get("role", "user"),
                "content": item.get("content", ""),
            })

    # 追加本次用户提问
    messages.append({"role": "user", "content": message})

    # 调用 LLM
    url = f"{llm_config['base_url']}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {llm_config['api_key']}",
    }
    payload = {
        "model": llm_config["model_id"],
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024,
    }

    try:
        async with httpx.AsyncClient(timeout=llm_config["timeout"]) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            reply = data["choices"][0]["message"]["content"]
            return reply.strip()

    except httpx.HTTPStatusError as e:
        print(f"❌ LLM API 返回错误: {e.response.status_code} - {e.response.text}")
        return f"抱歉，AI 服务暂时出现问题 (HTTP {e.response.status_code})，请稍后重试 🙏"
    except httpx.TimeoutException:
        print("❌ LLM API 请求超时")
        return "抱歉，AI 回复超时了，请稍后再试 ⏳"
    except Exception as e:
        print(f"❌ LLM 调用异常: {e}")
        return f"抱歉，AI 出现了意外错误，请稍后重试 🙏"
