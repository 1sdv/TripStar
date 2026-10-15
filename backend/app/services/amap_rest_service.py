"""高德官方 Web 服务（REST）直连客户端。

为什么直连 REST 而不用 MCP 封装：
`uvx amap-mcp-server` 的 `maps_text_search` 只返回
`id / name / address / typecode` 四个字段，把 `photos`（官方图库）、
`location`（坐标）、`business`（评分、营业时间、电话）全部裁掉了。
要拿到这些字段必须直接调高德 Web 服务 API。

（历史：项目早期另有一个走 MCP 的 `services/amap_service.py`，其方法只
返回空列表、且所依赖的 MCP 服务器与新版 pydantic 不兼容，已删除。）

本模块只负责「取数」，不做业务编排；调用方负责在异步路由里用
`asyncio.to_thread` 派发（`httpx.get` 是阻塞调用）。
"""

import threading
import time
from collections import OrderedDict, deque
from typing import Any, Dict, List, Optional

import httpx

from ..config import get_settings

_PLACE_TEXT_URL = "https://restapi.amap.com/v5/place/text"
_TIMEOUT_SECONDS = 10
# v5 接口默认只返回基础字段，需要显式声明才能拿回图片与营业信息
_SHOW_FIELDS = "photos,business"

# 高德个人 Key 默认限 3 次/秒，超了会返回 CUQPS_HAS_EXCEEDED_THE_LIMIT。
# 前端加载图片时是并发 4 的，不主动限流必然触发。这里与
# `xhs_service._wait_for_amap_geocode_slot` 用同一套「滑动窗口」做法
# （那边限的是地理编码，本模块限的是 POI 搜索，两者共用同一个 Key 的配额）。
_AMAP_RATE_LIMIT = 3
_AMAP_RATE_WINDOW = 1.0
_QPS_RETRY_DELAY_SECONDS = 1.2

_rate_lock = threading.Lock()
_request_times: deque = deque()


def _wait_for_slot() -> None:
    """限制高德 POI 搜索的启动速率，避免超过官方 3 次/秒上限。"""
    while True:
        wait_seconds = 0.0
        now = time.monotonic()
        with _rate_lock:
            while _request_times and now - _request_times[0] >= _AMAP_RATE_WINDOW:
                _request_times.popleft()

            if len(_request_times) < _AMAP_RATE_LIMIT:
                _request_times.append(now)
                return

            wait_seconds = _AMAP_RATE_WINDOW - (now - _request_times[0])

        if wait_seconds > 0:
            time.sleep(wait_seconds)


# 名称+城市 → 图片直链的内存缓存。
#
# 两条 TTL 刻意不对称：高德官方图库直链是**稳定**的（路径里没有时效签名、
# 也不校验 Referer），所以命中可以放心长期复用；而未取到图只缓存很短时间，
# 避免把一次瞬时失败放大成「接下来很久都没有图」——那正是小红书旧实现
# 用 600 秒负向缓存造成过的故障。
_HIT_TTL_SECONDS = 7 * 24 * 3600
_MISS_TTL_SECONDS = 60
_CACHE_MAXSIZE = 1024

_photo_cache: "OrderedDict[str, tuple[str, float]]" = OrderedDict()
_photo_cache_lock = threading.Lock()


def _cache_key(name: str, city: str) -> str:
    return f"{city.strip()}\x00{name.strip()}"


def _cache_get(key: str) -> Optional[str]:
    with _photo_cache_lock:
        entry = _photo_cache.get(key)
        if entry is None:
            return None
        url, expires_at = entry
        if time.monotonic() >= expires_at:
            del _photo_cache[key]
            return None
        _photo_cache.move_to_end(key)
        return url


def _cache_put(key: str, url: str) -> None:
    ttl = _HIT_TTL_SECONDS if url else _MISS_TTL_SECONDS
    with _photo_cache_lock:
        _photo_cache[key] = (url, time.monotonic() + ttl)
        _photo_cache.move_to_end(key)
        while len(_photo_cache) > _CACHE_MAXSIZE:
            _photo_cache.popitem(last=False)


def _photo_urls(poi: Dict[str, Any]) -> List[str]:
    """取出一条 POI 的图片直链列表（过滤掉缺失项）。"""
    photos = poi.get("photos") or []
    if not isinstance(photos, list):
        return []
    return [
        str(p["url"])
        for p in photos
        if isinstance(p, dict) and p.get("url")
    ]


def _pick_photo(pois: List[Dict[str, Any]], name: str) -> str:
    """在候选 POI 中挑一张图。

    优先「名称完全一致」，其次「名称包含关键词」，最后退化到第一个有图的条目。
    高德文本搜索会返回一批相关 POI，直接取第一个容易拿到同名酒店、分店或
    公交站；而终点兜底又很必要——行程里的名字常与高德官方名略有出入
    （「飞天山」在库里是「飞天山景区」，「郴州博物馆」是「郴州市博物馆」）。
    """
    exact = ""
    partial = ""
    fallback = ""
    for poi in pois:
        if not isinstance(poi, dict):
            continue
        urls = _photo_urls(poi)
        if not urls:
            continue
        poi_name = str(poi.get("name") or "").strip()
        if not fallback:
            fallback = urls[0]
        if name and poi_name == name and not exact:
            exact = urls[0]
        elif name and name in poi_name and not partial:
            partial = urls[0]
    return exact or partial or fallback


def search_place(keywords: str, city: str = "", page_size: int = 5) -> Optional[List[Dict[str, Any]]]:
    """调用高德 POI 文本搜索，返回原始 POI 列表（含 photos / business / location）。

    返回值刻意区分两种「空」：
    - `[]`   —— 接口正常，但确实搜不到
    - `None` —— 接口调用失败（网络异常、Key 无效、配额用尽等）
    调用方据此决定要不要把「空结果」写进缓存：失败绝不能当成「此处无图」，
    否则一次限流就会变成一段时间的持续缺图。
    """
    key = get_settings().vite_amap_web_key
    if not key or not keywords:
        return None

    params: Dict[str, Any] = {
        "key": key,
        "keywords": keywords,
        "page_size": page_size,
        "show_fields": _SHOW_FIELDS,
    }
    if city:
        params["region"] = city

    for attempt in (1, 2):
        _wait_for_slot()
        try:
            resp = httpx.get(
                _PLACE_TEXT_URL,
                params=params,
                timeout=_TIMEOUT_SECONDS,
                trust_env=False,
            )
            data = resp.json()
        except Exception as e:  # noqa: BLE001 — 网络异常统一降级，不打断上层
            print(f"⚠️  [AMapREST] POI 搜索失败 ({keywords}@{city}): {e}")
            return None

        if str(data.get("status")) == "1":
            pois = data.get("pois")
            return pois if isinstance(pois, list) else []

        info = str(data.get("info") or "")
        # 被限流是可以自愈的，等一个窗口再试一次，别急着上报失败
        if attempt == 1 and "QPS" in info.upper():
            print(f"⚠️  [AMapREST] 触发 QPS 限流，{_QPS_RETRY_DELAY_SECONDS}s 后重试 ({keywords})")
            time.sleep(_QPS_RETRY_DELAY_SECONDS)
            continue

        print(f"⚠️  [AMapREST] POI 搜索返回异常 ({keywords}@{city}): {info}")
        return None

    return None


def _name_similarity(needle: str, candidate: str) -> float:
    """名称相似度 = 最长公共子序列长度 / 查询词长度，范围 [0, 1]。

    用 LCS 而非包含判定：「海舌公园」与 POI 名「爱在海舌蜜月半岛」并没有包含关系
    （后者是"海舌蜜月"，没有"公园"），但共享 2 字前缀，LCS 比率为 0.5 能救回来；
    而「不存在的景点XYZ」与任何 POI 的 LCS 都极低，仍会被正确拒绝。
    """
    if not needle or not candidate:
        return 0.0
    # 短字符串，朴素 DP 足够
    prev = [0] * (len(candidate) + 1)
    for ch_a in needle:
        cur = [0]
        for j, ch_b in enumerate(candidate, start=1):
            if ch_a == ch_b:
                cur.append(prev[j - 1] + 1)
            else:
                cur.append(max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1] / len(needle)


def resolve_poi_location(names: List[str], city: str = "") -> Optional[Dict[str, float]]:
    """按名称用 POI 文本搜索解析坐标，返回 {"longitude","latitude"}，失败返回 None。

    这是地理编码的**精度兜底**：实测高德 v3/geocode 对「海舌公园」这类非行政地名
    会直接返回 ENGINE_RESPONSE_DATA_ERROR，而 v5/place/text 能正常搜到；
    反过来对「喜洲」这类乡镇级地名，POI 结果又比 geocode 更贴近实际位置。
    因此两者互补：先 geocode，失败再用本函数。

    名称匹配采用 LCS 相似度阈值，避免把完全无关的 POI 坐标当成本景点坐标
    （把景点标错位置比缺坐标更糟）。
    """
    for name in [n for n in names if n and n.strip()]:
        needle = name.strip()
        threshold = 0.5 if len(needle) <= 4 else 0.6

        pois = search_place(needle, city, page_size=3)
        if not pois:
            continue

        best_location = ""
        best_score = 0.0
        for poi in pois:
            poi_name = str(poi.get("name") or "").strip()
            location = str(poi.get("location") or "")
            if not poi_name or "," not in location:
                continue
            score = _name_similarity(needle, poi_name)
            if score > best_score:
                best_score = score
                best_location = location

        if best_location and best_score >= threshold:
            try:
                lon, lat = best_location.split(",")
                return {"longitude": float(lon), "latitude": float(lat)}
            except (ValueError, TypeError):
                continue

    return None


# ============ 天气（v3 天气预报）与酒店（v5 文本搜索）REST 直连 ============
#
# 背景：MCP 路径（uvx amap-mcp-server）依赖旧版 pydantic，与当前环境不兼容，
# 进程启动即崩、工具发现静默为空，导致天气/酒店拿不到数据。这两个函数让
# 天气与酒店也能走官方 Web 服务 REST，彻底摆脱 MCP。

_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"
_WEATHER_TIMEOUT_SECONDS = 8
# 高德免费版仅提供有限天数的预报，超出部分由 Planner 依据常识补齐
_WEATHER_FORECAST_DAYS = 4

# 常见行政区后缀：高德天气要求「城市名或 adcode」，带后缀常报 INVALID_PARAMS
_CITY_SUFFIXES = ("特别行政区", "自治区", "自治州", "地区", "盟", "省", "市", "县", "区", "州")


def _clean_city_for_amap(city: str) -> str:
    """把 "中国-云南-大理" / "大理市" 这类输入规整为高德天气可接受的纯城市名。"""
    text = str(city or "").strip()
    if not text:
        return ""
    # 去掉国家/省份前缀，取最后一段
    text = text.replace("－", "-").split("-")[-1].strip()
    for suffix in _CITY_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
            break
    return text


def _poi_location_text(location: Any) -> str:
    """高德 location 字段是 "经度,纬度" 字符串，缺失时返回空串。"""
    if isinstance(location, str) and "," in location:
        return location
    return ""


def get_weather_forecast(city: str) -> Optional[List[Dict[str, str]]]:
    """查询城市天气预报，返回 casts 原始列表；失败或 Key 未配置返回 None。

    返回字段：date / dayweather / nightweather / daytemp / nighttemp /
              daywind / nightwind / daypower / nightpower
    """
    key = get_settings().vite_amap_web_key
    clean_city = _clean_city_for_amap(city)
    if not key or not clean_city:
        return None

    params = {"key": key, "city": clean_city, "extensions": "all", "output": "JSON"}
    try:
        _wait_for_slot()
        resp = httpx.get(_WEATHER_URL, params=params, timeout=_WEATHER_TIMEOUT_SECONDS, trust_env=False)
        data = resp.json()
    except Exception as e:
        print(f"⚠️  [AMapREST] 天气查询失败 ({clean_city}): {e}")
        return None

    if str(data.get("status")) != "1":
        print(f"⚠️  [AMapREST] 天气接口返回异常 ({clean_city}): {data.get('info')}")
        return None

    forecasts = data.get("forecasts") or []
    if not forecasts:
        return None
    casts = forecasts[0].get("casts") or []
    return casts if isinstance(casts, list) else None


def format_weather_block(
    city: str,
    casts: List[Dict[str, str]],
    start_date: str = "",
    end_date: str = "",
) -> str:
    """把预报 casts 格式化为 Planner 可读文本。

    高德免费版只提供**未来数天**的预报。若行程日期超出预报窗口（例如提前几个月规划），
    绝不能用今天的预报冒充行程期间的天气，否则会误导行程安排——此时只明确告知
    「无对应日期预报」，由 Planner 按季节给出保守提醒。

    Args:
        start_date / end_date: 行程日期（YYYY-MM-DD）；为空则不做过滤
    """
    relevant = casts
    if start_date:
        # 预报日期为 YYYY-MM-DD，字符串比较即可
        upper = end_date or start_date
        relevant = [
            c for c in casts
            if start_date <= str(c.get("date", "")) <= upper
        ]

    if start_date and not relevant:
        available = "、".join(str(c.get("date", "")) for c in casts[:_WEATHER_FORECAST_DAYS])
        return (
            f"【{city} 行程期间无天气预报】高德官方预报仅覆盖 {available}，"
            f"与行程日期（{start_date} ~ {end_date or start_date}）不重叠。"
            f"请按该城市该季节的常见气候给出保守提醒（如防晒、早晚温差、雨季），"
            f"不要编造具体温度数值。"
        )

    lines = [
        f"【{city} 未来天气（高德官方预报，最多 {_WEATHER_FORECAST_DAYS} 天）】"
    ]
    for c in relevant[:_WEATHER_FORECAST_DAYS]:
        lines.append(
            f"{c.get('date', '')}: 白天{c.get('dayweather', '')} {c.get('daytemp', '')}°C, "
            f"夜间{c.get('nightweather', '')} {c.get('nighttemp', '')}°C, "
            f"{c.get('daywind', '')}风 {c.get('daypower', '')}"
        )
    if len(relevant) < _WEATHER_FORECAST_DAYS and start_date:
        lines.append(
            "（注：行程部分日期超出预报窗口，那几天请按该季节常见气候给出保守建议，"
            "不要编造具体温度）"
        )
    return "\n".join(lines)


def search_hotels_rest(city: str, accommodation: str = "酒店") -> Optional[str]:
    """用高德 POI 文本搜索找住宿，返回可直接注入 Prompt 的文本块。

    返回 None 表示接口失败（Key 未配置 / 网络异常 / 配额用尽），由调用方决定后续降级；
    返回空串表示接口正常但没有结果。
    """
    keyword = f"{accommodation or '酒店'}" if accommodation else "酒店"
    pois = search_place(f"{keyword}", city, page_size=6)
    if pois is None:
        return None
    if not pois:
        return ""

    lines = [f"【{city} {keyword}搜索结果（高德官方 POI）】"]
    for index, poi in enumerate(pois, start=1):
        name = str(poi.get("name") or "").strip()
        if not name:
            continue
        raw_address = poi.get("address")
        # v5 的 address 可能是字符串或 [省,市,区,街道] 列表
        address = "".join(str(x) for x in raw_address) if isinstance(raw_address, list) else str(raw_address or "").strip()
        loc = _poi_location_text(poi.get("location"))
        business = poi.get("business") or {}
        rating = str(business.get("rating") or "").strip()
        cost = str(business.get("cost") or "").strip()
        type_name = str(poi.get("type") or "").split(";")[-1].strip()

        parts = [f"{index}. {name}"]
        if type_name:
            parts.append(f"类型：{type_name}")
        if address:
            parts.append(f"地址：{address}")
        if loc:
            parts.append(f"坐标：{loc}")
        if rating:
            parts.append(f"评分：{rating}")
        if cost:
            parts.append(f"人均：{cost}元")
        lines.append(" | ".join(parts))

    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def get_poi_photo_url(name: str, city: str = "") -> str:
    """按景点名取一张高德官方图库直链，取不到返回空串（带缓存）。

    该直链可直接被浏览器引用：实测带不带 Referer 都返回 200，
    因此页面展示不需要后端代理（导出场景除外，见 xhs_service 的白名单注释）。
    """
    name = (name or "").strip()
    city = (city or "").strip()
    if not name:
        return ""

    cache_key = _cache_key(name, city)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    url = ""
    api_failed = False
    # 先限定城市搜；不带城市再兜一次，覆盖「城市名与高德行政区划不一致」的情况
    for region in ([city] if city else []) + [""]:
        pois = search_place(name, region)
        if pois is None:
            api_failed = True
            continue
        url = _pick_photo(pois, name)
        if url:
            break

    if url:
        _cache_put(cache_key, url)
    elif api_failed:
        # 接口失败不代表没有图：不写缓存，下次请求立刻重试
        print(f"⚠️  [AMapREST] 「{name}」查询失败，不缓存以便重试 (city={city or '-'})")
    else:
        _cache_put(cache_key, "")
        print(f"⚠️  [AMapREST] 高德图库确认无「{name}」的图片 (city={city or '-'})")
    return url
