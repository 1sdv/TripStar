"""统一地图服务调度层

优先使用 Google Maps API（如果已配置且可用），
否则降级到高德地图 MCP 服务。

用法:
    from ..services.map_dispatcher import get_map_provider, geocode_unified

    provider = get_map_provider()   # "google" 或 "amap"
    location  = geocode_unified("故宫", "北京")
"""

from typing import Optional, Literal

from ..config import get_settings
from ..models.schemas import Location


MapProvider = Literal["google", "amap"]

# 全局标志位：记录 Google 地理编码是否失败过，避免对每个景点都重复尝试并超时
_google_geo_failed_flag = False


def reset_google_geo_failure() -> None:
    """清除 Google 地理编码失败标记。

    该标记是为了避免逐个景点重复超时而设的短路开关，
    但一次网络抖动会让整个进程永久降级到高德，因此配置变更时必须允许复位。
    """
    global _google_geo_failed_flag
    _google_geo_failed_flag = False


def get_map_provider() -> MapProvider:
    """根据当前运行时配置判断应使用哪个地图供应商。

    优先级: Google Maps API Key 已配置 → google,
            否则 → amap (高德 MCP)
    """
    settings = get_settings()
    if settings.google_maps_api_key:
        return "google"
    return "amap"


def geocode_unified(
    address: str, city: str, *, address_zh: str = "", address_en: str = ""
) -> Optional[dict]:
    """统一地理编码接口，返回 {"longitude": float, "latitude": float}，全部失败时返回 None。

    根据 get_map_provider() 的结果，自动路由到 Google 或高德，
    并根据供应商特性自动选择最合适语言的地址：
    - Google Maps: 优先使用英文地址 (address_en)，对英文地名识别更友好
    - 高德地图: 优先使用中文地址 (address_zh)，对中文地名识别更准确

    如果 Google 失败过一次，后续会自动全部短路降级到高德，不再重复耗时尝试。

    Args:
        address: 默认地址（任意语言，作为兜底）
        city: 城市名称
        address_zh: 中文地址（优先用于高德地图）
        address_en: 英文地址（优先用于 Google Maps）
    """
    global _google_geo_failed_flag
    provider = get_map_provider()

    if provider == "google" and not _google_geo_failed_flag:
        from .google_map_service import get_google_map_service  # noqa: delay import
        svc = get_google_map_service()
        if svc:
            # Google 对英文地名更友好，优先使用英文地址
            google_address = address_en or address
            loc = svc.geocode(google_address, city)
            if loc:
                return {"longitude": loc.longitude, "latitude": loc.latitude}
        
        # 第一次解析失败，标记为全局不可用
        _google_geo_failed_flag = True
        print(f"⚠️ [Dispatcher] Google 地理编码失败 (后续景点采用高德): {address_en or address}")

    # 高德兜底 — 高德对中文地名识别更准确，优先使用中文地址
    amap_address = address_zh or address
    from .xhs_service import _geocode_amap_raw  # noqa: delay import
    return _geocode_amap_raw(amap_address, city)
