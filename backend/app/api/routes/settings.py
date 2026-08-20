"""运行时配置 API 路由"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...config import get_runtime_settings, update_runtime_settings
from ...services.amap_service import reset_amap_service
from ...services.google_map_service import reset_google_map_service
from ...services.llm_service import reset_llm
from ...agents.trip_planner_agent import reset_trip_planner_agent

router = APIRouter(prefix="/settings", tags=["运行时配置"])


class RuntimeSettingsPayload(BaseModel):
    """前端设置页提交的运行时配置。"""

    vite_amap_web_key: Optional[str] = Field(default=None, description="高德 Web 服务 Key")
    vite_amap_web_js_key: Optional[str] = Field(default=None, description="高德 JS SDK Key")
    google_maps_api_key: Optional[str] = Field(default=None, description="Google Maps API Key")
    google_maps_proxy: Optional[str] = Field(default=None, description="Google Maps 代理地址")
    xhs_cookie: Optional[str] = Field(default=None, description="小红书 Cookie")
    openai_api_key: Optional[str] = Field(default=None, description="LLM API Key")
    openai_base_url: Optional[str] = Field(default=None, description="LLM Base URL")
    openai_model: Optional[str] = Field(default=None, description="LLM 模型")


@router.get("")
async def get_settings():
    """获取当前运行时配置。"""
    return {
        "success": True,
        "message": "ok",
        "data": get_runtime_settings(),
    }


@router.put("")
async def save_settings(payload: RuntimeSettingsPayload):
    """保存运行时配置并立即生效。"""
    try:
        updates = payload.model_dump(exclude_unset=True)
        updated = update_runtime_settings(updates)

        # 重置单例，确保新配置立即生效
        reset_llm()
        reset_amap_service()
        reset_google_map_service()
        reset_trip_planner_agent()

        return {
            "success": True,
            "message": "配置已保存并立即生效",
            "data": updated,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}") from e
