"""Google Maps API 服务封装

提供与 AmapService 对等的 API 接口:
  - search_poi       → Places API (Text Search)
  - geocode          → Geocoding API
  - plan_route       → Routes / Directions API
  - get_poi_detail   → Places Details API
  - get_weather      → Weather API (current + forecast + history)
"""

import json
import threading
from typing import Dict, Any, List, Optional

import httpx

from ..config import get_settings
from ..models.schemas import Location, POIInfo, WeatherInfo


class GoogleMapService:
    """Google Maps Platform 服务封装类"""

    # --------------- 基础常量 ---------------
    PLACES_BASE = "https://places.googleapis.com/v1/places"
    GEOCODING_BASE = "https://maps.googleapis.com/maps/api/geocode/json"
    DIRECTIONS_BASE = "https://maps.googleapis.com/maps/api/directions/json"
    WEATHER_BASE = "https://weather.googleapis.com/v1/currentConditions"
    WEATHER_FORECAST_BASE = "https://weather.googleapis.com/v1/forecast/days"

    def __init__(self, api_key: str, proxy: str = ""):
        self.api_key = api_key
        # 创建带代理的持久化 HTTP 客户端
        # 仅使用显式传入的 Google Maps 代理，不继承系统环境代理
        client_kwargs: Dict[str, Any] = {"timeout": 15, "trust_env": False}
        if proxy:
            client_kwargs["proxy"] = proxy
        self._client = httpx.Client(**client_kwargs)

    def close(self) -> None:
        """关闭 HTTP 客户端连接池。"""
        self._client.close()

    # ======================== POI 搜索 ========================

    def search_poi(self, keywords: str, city: str, citylimit: bool = True) -> List[POIInfo]:
        """
        使用 Places API (New) Text Search 搜索 POI

        https://developers.google.com/maps/documentation/places/web-service/text-search
        """
        url = f"{self.PLACES_BASE}:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.types,places.internationalPhoneNumber",
        }
        body = {
            "textQuery": f"{city} {keywords}" if citylimit else keywords,
            "languageCode": "zh-CN",
        }
        try:
            resp = self._client.post(url, headers=headers, json=body)
            data = resp.json()
            results: List[POIInfo] = []
            for place in data.get("places", []):
                loc = place.get("location", {})
                results.append(POIInfo(
                    id=place.get("id", ""),
                    name=place.get("displayName", {}).get("text", ""),
                    type=",".join(place.get("types", [])[:3]),
                    address=place.get("formattedAddress", ""),
                    location=Location(
                        longitude=loc.get("longitude", 0),
                        latitude=loc.get("latitude", 0),
                    ),
                    tel=place.get("internationalPhoneNumber"),
                ))
            return results
        except Exception as e:
            print(f"❌ [Google] POI 搜索失败: {e}")
            return []

    # ======================== 地理编码 ========================

    def geocode(self, address: str, city: Optional[str] = None) -> Optional[Location]:
        """
        地理编码 (地址 → 坐标)

        https://developers.google.com/maps/documentation/geocoding
        """
        params: Dict[str, str] = {
            "address": f"{address}, {city}" if city else address,
            "key": self.api_key,
            "language": "zh-CN",
        }
        try:
            resp = self._client.get(self.GEOCODING_BASE, params=params)
            data = resp.json()
            results = data.get("results", [])
            if results:
                loc = results[0]["geometry"]["location"]
                return Location(longitude=loc["lng"], latitude=loc["lat"])
        except Exception as e:
            print(f"❌ [Google] 地理编码失败 ({address}): {e}")
        return None

    # ======================== 路线规划 ========================

    def plan_route(
        self,
        origin_address: str,
        destination_address: str,
        origin_city: Optional[str] = None,
        destination_city: Optional[str] = None,
        route_type: str = "walking",
    ) -> Dict[str, Any]:
        """
        路线规划 — 使用 Directions API

        https://developers.google.com/maps/documentation/directions
        """
        mode_map = {
            "walking": "walking",
            "driving": "driving",
            "transit": "transit",
        }
        params = {
            "origin": f"{origin_address}, {origin_city}" if origin_city else origin_address,
            "destination": f"{destination_address}, {destination_city}" if destination_city else destination_address,
            "mode": mode_map.get(route_type, "walking"),
            "key": self.api_key,
            "language": "zh-CN",
        }
        try:
            resp = self._client.get(self.DIRECTIONS_BASE, params=params)
            data = resp.json()
            if data.get("routes"):
                leg = data["routes"][0]["legs"][0]
                return {
                    "distance": leg["distance"]["value"],
                    "duration": leg["duration"]["value"],
                    "distance_text": leg["distance"]["text"],
                    "duration_text": leg["duration"]["text"],
                    "steps": [s["html_instructions"] for s in leg.get("steps", [])[:5]],
                }
        except Exception as e:
            print(f"❌ [Google] 路线规划失败: {e}")
        return {}

    # ======================== POI 详情 ========================

    def get_poi_detail(self, poi_id: str) -> Dict[str, Any]:
        """
        获取 Place 详情

        https://developers.google.com/maps/documentation/places/web-service/place-details
        """
        url = f"{self.PLACES_BASE}/{poi_id}"
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "id,displayName,formattedAddress,location,types,photos,editorialSummary,rating,userRatingCount",
        }
        try:
            resp = self._client.get(url, headers=headers)
            return resp.json()
        except Exception as e:
            print(f"❌ [Google] POI 详情失败: {e}")
            return {}

    # ======================== 天气查询 ========================

    def get_weather(self, city: str) -> List[WeatherInfo]:
        """
        使用 Google Maps Weather API 查询天气

        API 文档: https://developers.google.com/maps/documentation/weather

        策略:
        1. 先通过 Geocoding 把城市名解析为坐标
        2. 调用 Weather API 的 forecast/days 端点获取未来数天预报
        3. 解析为与高德兼容的 WeatherInfo 列表
        """
        # Step 1: 获取城市坐标
        loc = self.geocode(city)
        if not loc:
            print(f"⚠️ [Google] 天气查询: 无法解析城市 '{city}' 的坐标")
            return []

        # Step 2: 调用 Weather API - 每日预报
        forecast_url = f"https://weather.googleapis.com/v1/forecast/days:lookup"
        params = {
            "key": self.api_key,
            "location.latitude": loc.latitude,
            "location.longitude": loc.longitude,
            "days": 7,
            "languageCode": "zh-CN",
            "unitsSystem": "METRIC",
        }
        try:
            resp = self._client.get(forecast_url, params=params)
            data = resp.json()
            weather_list: List[WeatherInfo] = []

            forecast_days = data.get("forecastDays", [])
            for day_data in forecast_days:
                date_info = day_data.get("displayDate", {})
                date_str = f"{date_info.get('year', 2025)}-{date_info.get('month', 1):02d}-{date_info.get('day', 1):02d}"

                daytime = day_data.get("daytimeForecast", {})
                nighttime = day_data.get("nighttimeForecast", {})

                day_temp_data = day_data.get("maxTemperature", {})
                night_temp_data = day_data.get("minTemperature", {})

                # 提取风力信息
                day_wind = daytime.get("wind", {})
                wind_dir = day_wind.get("direction", {}).get("cardinal", "")
                wind_speed = day_wind.get("speed", {}).get("value", 0)
                # 将风速(km/h)转换为中文风力等级描述
                if wind_speed < 6:
                    wind_power = "微风"
                elif wind_speed < 12:
                    wind_power = "1-2级"
                elif wind_speed < 20:
                    wind_power = "3级"
                elif wind_speed < 29:
                    wind_power = "4级"
                elif wind_speed < 39:
                    wind_power = "5级"
                else:
                    wind_power = "6级以上"

                # 获取天气描述
                day_condition = daytime.get("weatherCondition", "")
                night_condition = nighttime.get("weatherCondition", "")

                # Google Weather API 的 weatherCondition 是英文枚举值, 做简单的中文映射
                condition_map = {
                    "CLEAR": "晴", "MOSTLY_CLEAR": "晴",
                    "PARTLY_CLOUDY": "多云", "MOSTLY_CLOUDY": "多云",
                    "CLOUDY": "阴", "OVERCAST": "阴",
                    "LIGHT_RAIN": "小雨", "RAIN": "中雨",
                    "MODERATE_RAIN": "中雨", "HEAVY_RAIN": "大雨",
                    "LIGHT_SNOW": "小雪", "SNOW": "中雪",
                    "HEAVY_SNOW": "大雪", "THUNDERSTORM": "雷阵雨",
                    "DRIZZLE": "毛毛雨", "FOG": "雾",
                    "HAZE": "霾", "WIND": "大风",
                }
                day_weather = condition_map.get(day_condition, day_condition)
                night_weather = condition_map.get(night_condition, night_condition)

                weather_list.append(WeatherInfo(
                    date=date_str,
                    day_weather=day_weather,
                    night_weather=night_weather,
                    day_temp=int(day_temp_data.get("degrees", 0)),
                    night_temp=int(night_temp_data.get("degrees", 0)),
                    wind_direction=wind_dir,
                    wind_power=wind_power,
                ))

            print(f"✅ [Google] 天气查询成功: {city}, {len(weather_list)} 天预报")
            return weather_list

        except Exception as e:
            print(f"❌ [Google] 天气查询失败: {e}")
            return []


# ============ 单例管理 ============

_google_map_service: Optional[GoogleMapService] = None
_google_map_service_lock = threading.Lock()


def get_google_map_service() -> Optional[GoogleMapService]:
    """获取 Google Maps 服务实例 (单例模式)。如果 API Key 未配置则返回 None。"""
    global _google_map_service

    if _google_map_service is None:
        with _google_map_service_lock:
            if _google_map_service is None:
                settings = get_settings()
                if not settings.google_maps_api_key:
                    return None
                _google_map_service = GoogleMapService(
                    api_key=settings.google_maps_api_key,
                    proxy=settings.google_maps_proxy,
                )
                if settings.google_maps_proxy:
                    print(f"  - Google Maps 代理已配置: {settings.google_maps_proxy}")
                print("✅ Google Maps 服务初始化成功")

    return _google_map_service


def reset_google_map_service() -> None:
    """重置 Google Maps 服务实例（用于运行时配置更新后热生效）。"""
    global _google_map_service
    with _google_map_service_lock:
        if _google_map_service is not None:
            _google_map_service.close()
        _google_map_service = None
