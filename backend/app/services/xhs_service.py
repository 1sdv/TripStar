"""小红书搜索服务 - 基于 Spider_XHS 原生签名引擎

彻底替换第三方 xhs 库，使用本地 JS 签名 + 直连 edith.xiaohongshu.com API，
解决 300011 账号异常风控误杀问题。
"""

import json
import re
import math
import random
import logging
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import requests
import httpx
from typing import List, Dict, Any, Optional
from ..config import get_settings
from .llm_service import get_llm
from .xhs_sign.sign_util import generate_request_params, splice_str, generate_x_b3_traceid, trans_cookies

logger = logging.getLogger(__name__)
_amap_geocode_warning_lock = threading.Lock()
_amap_geocode_warning_keys: set[tuple[str, str]] = set()


class XHSCookieExpiredError(Exception):
    """小红书 Cookie 过期致命异常，用于向前端报警"""
    pass


class XHSFetchError(Exception):
    """小红书普通抓取异常；区别于 Cookie 过期/风控。"""
    pass


# ============ Cookie 处理 ============

def normalize_xhs_cookie(cookie: str) -> str:
    """兼容 Cookie 请求头字符串和浏览器导出的 JSON Cookie 列表。"""
    normalized = cookie.strip()
    if not normalized:
        return normalized

    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {"'", '"'}:
        normalized = normalized[1:-1].strip()

    cookie_items = None
    if normalized.startswith("[") and normalized.endswith("]"):
        try:
            cookie_items = json.loads(normalized)
        except json.JSONDecodeError:
            cookie_items = None
    elif normalized.startswith("{") and '"name"' in normalized and '"value"' in normalized:
        try:
            cookie_items = json.loads(f"[{normalized}]")
        except json.JSONDecodeError:
            cookie_items = None

    if isinstance(cookie_items, list):
        pairs = []
        for item in cookie_items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            value = str(item.get("value", "")).strip()
            if name:
                pairs.append(f"{name}={value}")
        if pairs:
            print("已将 JSON 格式的小红书 Cookie 转换为请求头字符串格式。")
            return "; ".join(pairs)

    return normalized


# ============ 原生小红书 API 客户端 ============

class XhsNativeClient:
    """
    使用 Spider_XHS 签名引擎直连小红书 API 的原生客户端。
    不依赖任何第三方 xhs Python 库，通过 PyExecJS 调用本地 JS
    生成 x-s / x-t / x-s-common 等完整签名，彻底绕过 300011 风控。
    """
    BASE_URL = "https://edith.xiaohongshu.com"

    def __init__(self, cookies_str: str):
        self.cookies_str = cookies_str
        self._session = requests.Session()
        self._session.trust_env = False

    def search_notes(self, keyword: str, page: int = 1, sort_type: int = 0,
                     page_size: int = 20) -> dict:
        """
        搜索笔记 - 直连 /api/sns/web/v1/search/notes
        
        Args:
            keyword: 搜索关键词
            page: 页码
            sort_type: 排序方式 0综合 1最新 2最多点赞
            page_size: 每页数量
            
        Returns:
            API 响应 JSON
        """
        sort_map = {
            0: "general",
            1: "time_descending",
            2: "popularity_descending",
            3: "comment_descending",
            4: "collect_descending",
        }
        sort = sort_map.get(sort_type, "general")

        api = "/api/sns/web/v1/search/notes"
        data = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "search_id": generate_x_b3_traceid(21),
            "sort": "general",
            "note_type": 0,
            "ext_flags": [],
            "filters": [
                {"tags": [sort], "type": "sort_type"},
                {"tags": ["不限"], "type": "filter_note_type"},
                {"tags": ["不限"], "type": "filter_note_time"},
                {"tags": ["不限"], "type": "filter_note_range"},
                {"tags": ["不限"], "type": "filter_pos_distance"},
            ],
            "geo": "",
            "image_formats": ["jpg", "webp", "avif"],
        }

        headers, cookies, serialized_data = generate_request_params(
            self.cookies_str, api, data, "POST"
        )
        response = self._session.post(
            self.BASE_URL + api,
            headers=headers,
            data=serialized_data.encode("utf-8"),
            cookies=cookies,
            timeout=15,
        )
        res_json = response.json()

        if not res_json.get("success"):
            code = res_json.get("code", "")
            msg = res_json.get("msg", "")
            if code == 300011 or "异常" in msg:
                raise XHSCookieExpiredError(
                    f"小红书 Cookie 已被风控拦截 (code={code}): {msg}。请更换 Cookie 后重试。"
                )
            raise Exception(f"小红书搜索失败 (code={code}): {msg}")

        return res_json

    def get_note_detail(self, note_id: str, xsec_token: str = "",
                        xsec_source: str = "pc_search") -> dict:
        """
        获取笔记详情 - 直连 /api/sns/web/v1/feed
        
        Args:
            note_id: 笔记 ID
            xsec_token: 安全令牌（来自搜索结果）
            xsec_source: 来源标识
            
        Returns:
            笔记详情 JSON
        """
        api = "/api/sns/web/v1/feed"
        data = {
            "source_note_id": note_id,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": "1"},
            "xsec_source": xsec_source,
            "xsec_token": xsec_token,
        }

        headers, cookies, serialized_data = generate_request_params(
            self.cookies_str, api, data, "POST"
        )
        response = self._session.post(
            self.BASE_URL + api,
            headers=headers,
            data=serialized_data,
            cookies=cookies,
            timeout=15,
        )
        res_json = response.json()

        if not res_json.get("success"):
            code = res_json.get("code", "")
            msg = res_json.get("msg", "")
            if code == 300011 or "异常" in msg:
                raise XHSCookieExpiredError(
                    f"小红书 Cookie 已被风控拦截 (code={code}): {msg}"
                )

        return res_json


# ============ 客户端工厂 ============

def get_xhs_client() -> XhsNativeClient:
    """初始化并返回原生小红书客户端"""
    settings = get_settings()
    if not settings.xhs_cookie:
        raise XHSCookieExpiredError("小红书 Cookie 未配置，请先在前端设置页完成配置")
    cookie_str = normalize_xhs_cookie(settings.xhs_cookie)
    return XhsNativeClient(cookie_str)


# ============ 高德地理编码 ============

def _geocode_amap_raw(address: str, city: str) -> Optional[dict]:
    """纯高德 Web 服务地理编码（供 map_dispatcher 降级调用）。

    返回: {"longitude": float, "latitude": float}；失败返回 None。
    不再用固定坐标兜底，避免把景点静默标到错误城市。
    """
    settings = get_settings()
    if not settings.vite_amap_web_key:
        return None

    params = {
        "keywords": address,
        "city": city,
        "offset": 1,
        "key": settings.vite_amap_web_key,
    }
    try:
        resp = httpx.get("https://restapi.amap.com/v3/place/text", params=params, timeout=5, trust_env=False)
        data = resp.json()
        if data.get("status") == "1" and data.get("pois"):
            location = data["pois"][0]["location"]
            lon, lat = location.split(",")
            return {"longitude": float(lon), "latitude": float(lat)}
        info = str(data.get("info") or "")
        warning_key = (address, info)
        with _amap_geocode_warning_lock:
            if warning_key not in _amap_geocode_warning_keys:
                _amap_geocode_warning_keys.add(warning_key)
                print(f"高德地理编码无结果 ({address}): status={data.get('status')} info={info}")
    except Exception as e:
        print(f"高德地理编码查阅失败 ({address}): {e}")

    return None


def geocode_amap(address: str, city: str, *, name_zh: str = "", name_en: str = "") -> Optional[dict]:
    """统一地理编码入口 — 自动路由到 Google / 高德。

    内部通过 map_dispatcher 判断当前活跃供应商，
    并根据供应商自动选择最合适语言的地址进行编码：
    - Google Maps: 优先使用英文名称 (name_en)
    - 高德地图: 优先使用中文名称 (name_zh)
    """
    from .map_dispatcher import geocode_unified
    return geocode_unified(address, city, address_zh=name_zh, address_en=name_en)


# ============ SSR 降级方案（备用） ============

def get_note_detail_ssr(note_id: str) -> dict:
    """通过网页抓取 SSR 状态提取笔记详情，作为原生 API 的降级备选"""
    url = f"https://www.xiaohongshu.com/explore/{note_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = httpx.get(url, headers=headers, timeout=8, trust_env=False)
        match = re.search(r'window\.__INITIAL_STATE__=({.*?})</script>', resp.text)
        if match:
            state_json = json.loads(match.group(1).replace('undefined', 'null'))
            return state_json.get("note", {}).get("noteDetailMap", {}).get(note_id, {}).get("note", {})
    except Exception as e:
        print(f"SSR详情提取失败 {note_id}: {e}")
    return {}


# ============ 景点搜索核心函数 ============

def search_xhs_attractions(city: str, keywords: str, language: str = "zh") -> str:
    """
    搜索小红书笔记，使用大模型极速提纯出结构化景点，
    并静默拼装经纬度和真实图片，回传给Planner。

    Args:
        city: 城市名称
        keywords: 搜索关键词
        language: 目标输出语言 (zh/en/ja 等)
    """
    print(f"🔍 [XHS_SERVICE] 正在呼叫小红书 API 搜索: {city} {keywords}")
    client = get_xhs_client()
    query = f"{city} {keywords} 旅游 景点攻略"

    try:
        # 使用原生签名客户端搜索
        res_json = client.search_notes(keyword=query)
        items = res_json.get("data", {}).get("items", [])[:4]

        combined_text = ""
        for i, note in enumerate(items):
            if note.get("model_type") == "note":
                note_card = note.get("note_card", {})
                title = note_card.get("display_title", "")

                # 尝试通过原生 API 获取笔记详情
                desc = ""
                try:
                    note_id = note.get("id", "")
                    xsec_token = note.get("xsec_token", "")
                    if note_id:
                        detail_res = client.get_note_detail(note_id, xsec_token)
                        detail_items = detail_res.get("data", {}).get("items", [])
                        if detail_items:
                            note_data = detail_items[0].get("note_card", {})
                            desc = note_data.get("desc", "")
                except Exception:
                    # 降级到 SSR 抓取
                    try:
                        note_id = note.get("id", "")
                        if note_id:
                            detail = get_note_detail_ssr(note_id)
                            desc = detail.get("desc", "")
                    except Exception:
                        desc = ""

                combined_text += f"\n笔记{i+1}:\n标题: {title}\n正文内容: {desc}\n"

    except XHSCookieExpiredError:
        raise
    except (requests.Timeout, requests.ConnectionError) as e:
        print(f"❌ 小红书网络请求失败: {e}")
        raise XHSFetchError(f"访问小红书超时或网络不可达，请检查网络/代理后重试: {e}") from e
    except Exception as e:
        print(f"❌ 小红书接口抓取失败: {e}")
        raise XHSFetchError(f"小红书数据抓取失败: {e}") from e

    if not combined_text:
        return f"未在小红书检索到关于 {city} {keywords} 的内容。"

    # ======== 轻量级提取过程 ========
    print(f"🧠 [XHS_SERVICE] 正在调用内联模型提纯小红书游记参数...")
    llm = get_llm()

    # 根据目标语言构建翻译附加指令
    _lang = (language or "zh").strip().lower().split("-")[0]
    _lang_names = {"en": "English", "ja": "Japanese", "ko": "Korean", "fr": "French", "de": "German", "es": "Spanish"}
    if _lang != "zh" and _lang in _lang_names:
        translation_instruction = f"""
**极其重要的翻译要求:**
目标语言为 {_lang_names[_lang]}。你必须将提取结果中的 "name", "reason", "reservation_tips" 字段的内容翻译为 {_lang_names[_lang]}。
- "name" 字段使用目标语言 {_lang_names[_lang]} 的景点名称（例如中文"故宫博物院" → English "The Palace Museum"）。
- "reason" 和 "reservation_tips" 也必须翻译为 {_lang_names[_lang]}。
- "duration" 和 "reservation_required" 保持原始数值/布尔值不变。
- **注意**: "name_zh" 必须始终保持简体中文名称，"name_en" 必须始终保持英文名称，不受目标语言影响！
- 严格保持 JSON schema 格式不变！
"""
    else:
        translation_instruction = ""

    extract_prompt = f"""
请从以下真实的素人小红书打卡游记中，提纯出真实存在的【游玩景点】。
要求返回严格的 JSON 数组格式(哪怕只提取到了1个)，切勿返回除了JSON以外的任何冗余 markdown 文字！
{translation_instruction}
数组中每个对象必须包含以下字段:
"name": 景点官方名称(用于前端展示，按目标语言填写；若目标语言为中文则与 name_zh 相同)
"name_zh": 景点的中文简体名称(必须是简体中文，例如 "故宫博物院"。此字段始终为中文，不受目标语言影响)
"name_en": 景点的英文名称(必须是英文，使用景点在国际上通用的官方英文名，例如 "The Palace Museum"。此字段始终为英文，不受目标语言影响)
"reason": 小红书用户的真实评价/避坑指南
"duration": 游玩时长(数字, 分钟)
"reservation_required": 是否需要提前预约(布尔值 true/false)。请根据游记中提到的"需要预约"、"提前预约"、"抢票"、"约满"、"官方预约"等关键词判断，如果游记未提及则默认为 false
"reservation_tips": 预约相关提示(字符串)。如果需要预约，请提取预约渠道、提前天数等具体信息；如果不需要预约则填空字符串

**地理编码辅助字段说明:**
name_zh 和 name_en 将分别用于不同地图服务商(高德/Google)的地理定位，请务必准确填写！
- name_zh 必须是中文简体名称
- name_en 必须是英文名称，优先使用国际通用的官方英文名

游记杂文内容如下:
{combined_text}

JSON 返回示例:
[
  {{"name": "故宫博物院", "name_zh": "故宫博物院", "name_en": "The Palace Museum", "reason": "必去打卡，建议走中轴线。", "duration": 240, "reservation_required": true, "reservation_tips": "需要提前7天在故宫官网或微信小程序预约，每日限流8万人"}},
  {{"name": "老君山金顶", "name_zh": "老君山金顶", "name_en": "Laojun Mountain Golden Summit", "reason": "网红打卡点，夜景绝美，必须坐索道上山。", "duration": 180, "reservation_required": false, "reservation_tips": ""}}
]
"""
    try:
        response = llm._client.chat.completions.create(
            model=llm.model,
            messages=[{"role": "user", "content": extract_prompt}],
            temperature=0.1,
        )
        content = response.choices[0].message.content

        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            extracted = json.loads(json_match.group())
        else:
            extracted = json.loads(content)

        valid_items = [item for item in extracted if item.get("name")]

        def _resolve_location(item: dict) -> Optional[dict]:
            name = item["name"]
            try:
                return geocode_amap(
                    name,
                    city,
                    name_zh=item.get("name_zh", name),
                    name_en=item.get("name_en", name),
                )
            except Exception as geo_err:
                print(f"地理编码异常 ({name}): {geo_err}")
                return None

        locations: List[Optional[dict]] = []
        if valid_items:
            with ThreadPoolExecutor(max_workers=min(5, len(valid_items))) as pool:
                locations = list(pool.map(_resolve_location, valid_items))

        final_result = f"这是小红书热门精选游记的提取结果，附带确切坐标（图片由前端单独搜索获取）：\n"
        for item, loc in zip(valid_items, locations):
            if loc:
                item["location"] = loc
            final_result += json.dumps(item, ensure_ascii=False) + "\n"

        print(f"✅ [XHS_SERVICE] 小红书数据挖掘完毕，已装载进上下文。")
        return final_result

    except Exception as e:
        print(f"❌ 大模型提纯小红书数据异常: {e}")
        return "尝试提取小红书结构化数据失败，降级回常规处理。"


# ============ 景点搜图 ============

_PHOTO_CACHE_MAXSIZE = 512
_PHOTO_CACHE_TTL_SECONDS = 6 * 3600
_PHOTO_CACHE_MISS_TTL_SECONDS = 600
_photo_cache: "OrderedDict[str, tuple[str, float]]" = OrderedDict()
_photo_cache_lock = threading.Lock()


def _photo_cache_get(keyword: str) -> Optional[str]:
    with _photo_cache_lock:
        entry = _photo_cache.get(keyword)
        if entry is None:
            return None
        url, expires_at = entry
        if time.monotonic() >= expires_at:
            del _photo_cache[keyword]
            return None
        _photo_cache.move_to_end(keyword)
        return url


def _photo_cache_put(keyword: str, url: str) -> None:
    ttl = _PHOTO_CACHE_TTL_SECONDS if url else _PHOTO_CACHE_MISS_TTL_SECONDS
    with _photo_cache_lock:
        _photo_cache[keyword] = (url, time.monotonic() + ttl)
        _photo_cache.move_to_end(keyword)
        while len(_photo_cache) > _PHOTO_CACHE_MAXSIZE:
            _photo_cache.popitem(last=False)


def get_xhs_photo_sync(keyword: str) -> str:
    """带缓存的景点图片查询入口。"""
    cached = _photo_cache_get(keyword)
    if cached is not None:
        return cached

    url = _fetch_xhs_photo(keyword)
    _photo_cache_put(keyword, url)
    return url


def _fetch_xhs_photo(keyword: str) -> str:
    """根据关键词从小红书搜索一张首图URL

    使用原生签名客户端搜索最新帖子，然后通过原生 API 或 SSR 抓取首张图片。
    """
    try:
        client = get_xhs_client()

        # 搜图时强制按"最新"排序，避开综合高赞的含文字攻略图
        res_json = client.search_notes(keyword=keyword, sort_type=1)
        items = res_json.get("data", {}).get("items", [])

        target_note_id = None
        target_xsec_token = ""
        for note in items:
            if note.get("model_type") == "note":
                target_note_id = note.get("id")
                target_xsec_token = note.get("xsec_token", "")
                break

        if not target_note_id:
            return ""

        # 方案 A: 通过原生 API 获取笔记详情和图片
        try:
            detail_res = client.get_note_detail(
                target_note_id, target_xsec_token
            )
            detail_items = detail_res.get("data", {}).get("items", [])
            if detail_items:
                note_card = detail_items[0].get("note_card", {})
                image_list = note_card.get("image_list", [])
                if image_list:
                    # 取第一张图的 URL
                    first_img = image_list[0]
                    # 优先 info_list 中的高清图
                    info_list = first_img.get("info_list", [])
                    if len(info_list) > 1:
                        return info_list[1].get("url", "")
                    elif info_list:
                        return info_list[0].get("url", "")
                    # 降级到其他字段
                    return (
                        first_img.get("url_default", "")
                        or first_img.get("url_pre", "")
                        or first_img.get("url", "")
                    )
        except Exception:
            pass

        # 方案 B: 降级到 SSR 抓取
        url = f"https://www.xiaohongshu.com/explore/{target_note_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = httpx.get(url, headers=headers, timeout=10, trust_env=False)

        match = re.search(r'window\.__INITIAL_STATE__=({.*?})</script>', resp.text)
        if match:
            state_json_str = match.group(1).replace("undefined", "null")
            state_json = json.loads(state_json_str)
            note_data = (
                state_json.get("note", {})
                .get("noteDetailMap", {})
                .get(target_note_id, {})
                .get("note", {})
            )
            img_list = note_data.get("imageList", [])
            if img_list:
                first_img = (
                    img_list[0].get("urlDefault")
                    or img_list[0].get("urlPattern")
                    or img_list[0].get("url")
                )
                if first_img:
                    return first_img

    except Exception as e:
        print(f"小红书单图抓取失败 ({keyword}): {e}")
    return ""


async def get_photo_from_xhs(keyword: str) -> str:
    """供异步环境调用的小红书图片搜索API"""
    import asyncio
    return await asyncio.to_thread(get_xhs_photo_sync, keyword)
