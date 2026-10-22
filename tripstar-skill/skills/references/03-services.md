# 03 · 服务层（小红书 / 高德 / LLM / 地图调度）

> Google Maps 相关实现（`google_map_service.py`）不在本 skill 范围；仅在"供应商开关"处提及。

## 1. 小红书服务（`services/xhs_service.py`，759 行，最复杂）

### 1.1 为什么需要签名

小红书 Web 接口要求 `x-s` / `x-t` / `x-s-common` 等签名头，直接 `requests.get` 会返回风控错误（code 300011）。
项目内置 `services/xhs_sign/`（`sign_util.py` + 若干 `*.js`），通过 **PyExecJS** 执行 JS 生成签名，
再用 `requests.Session`（`trust_env=False`，不吃系统代理）直连 `https://edith.xiaohongshu.com`。

### 1.2 客户端

```python
class XhsNativeClient:
    BASE_URL = "https://edith.xiaohongshu.com"
    def __init__(self, cookies_str): self._session = requests.Session(); self._session.trust_env = False
    def search_notes(keyword, page=1, sort_type=0, page_size=20) -> dict   # POST /api/sns/web/v1/search/notes
    def get_note_detail(note_id, xsec_token="", xsec_source="pc_search") -> dict  # POST /api/sns/web/v1/feed
```

- 失败判定：`res_json["success"] is False` 且 `code == 300011` 或 `msg` 含"异常" → 抛 `XHSCookieExpiredError`；
  其他失败抛通用 `Exception(f"小红书搜索失败 (code=…): …")`。
- `get_xhs_client()`：Cookie 未配置直接抛 `XHSCookieExpiredError("小红书 Cookie 未配置，请先在前端设置页完成配置")`；
  否则 `normalize_xhs_cookie()` 归一（支持 JSON 格式 Cookie → `k=v; k=v` 字符串）。

### 1.3 景点搜索（业务入口）

```python
search_xhs_attractions(city: str, keywords: str, language: str = "zh") -> str
```

- 返回**给 LLM 消费的纯文本**（不是结构化对象）：标题/摘要/关键信息片段，最终由规划 Agent 组织成景点 JSON。
- `language != 'zh'` 时会提示按目标语言输出。
- 内部调用签名搜索 + 笔记详情（`get_note_detail_ssr`），并做去重与截断。
- 同步函数 → Agent 侧用 `asyncio.to_thread` 调，避免阻塞事件循环。

### 1.4 图片获取与缓存（两级）

**一级：关键词 → 直链（内存缓存）**

```python
_PHOTO_CACHE_MAXSIZE = 512
_PHOTO_CACHE_TTL_SECONDS = 6 * 3600
_PHOTO_CACHE_MISS_TTL_SECONDS = 600          # 未命中也缓存 10 分钟，避免反复重搜
_photo_cache_get(keyword) / _photo_cache_put(keyword, url)
get_xhs_photo_sync(keyword) -> str            # 缓存 → _fetch_xhs_photo(keyword)
_fetch_xhs_photo(keyword)                     # 搜索笔记 → 取首图直链
async def get_photo_from_xhs(keyword) -> str  # asyncio.to_thread(get_xhs_photo_sync, keyword)
```

**二级：图片字节（磁盘缓存）**

```python
_IMAGE_CACHE_DIR = backend/data/photo_cache
_IMAGE_CACHE_TTL_SECONDS = 24 * 3600
_IMAGE_MAX_SIZE_BYTES = 10 * 1024 * 1024
_IMAGE_ALLOWED_HOST_SUFFIXES = (".xiaohongshu.com", ".xhscdn.com")
_IMAGE_FETCH_HEADERS = { 带 Referer/UA，规避防盗链 }

_validate_image_url(url)                     # 只允许小红书域名，否则 ValueError
_image_cache_paths(cache_key)                # → {sha256}.img + {sha256}.meta
_read_image_cache(key) -> (bytes, content_type) | None      # 校验 meta 的过期时间
_write_image_cache(key, content, content_type)
_download_image(url) -> (bytes, content_type)               # 校验 content-type=image/*、大小、非空
fetch_xhs_image_bytes(url) -> (bytes, content_type)         # 缓存键 "url:"+url
get_xhs_photo_bytes_sync(keyword) -> (bytes, content_type)  # 缓存键 "kw:"+keyword；失败重搜新直链，最多 2 次
async def get_photo_bytes_from_xhs(keyword)                 # asyncio.to_thread(...)
```

缓存键规则：`url:<原始直链>`、`kw:<关键词>`；哈希后落盘，meta 记录 `content_type` 与写入时间。

### 1.5 高德地理编码（在 xhs_service 内，供 dispatcher 兜底）

```python
_AMAP_GEOCODE_RATE_LIMIT = 3      # 3 次/秒（高德官方上限）
_AMAP_GEOCODE_RATE_WINDOW = 1.0
_wait_for_amap_geocode_slot()      # 令牌桶式限速

_geocode_amap_raw(address, city) -> {"longitude":float,"latitude":float} | None
geocode_amap(address, city, *, name_zh="", name_en="") -> 同上
```

> 关键约定：**失败返回 `None`，绝不伪造默认坐标**（早期版本用固定坐标兜底，会把景点静默标到错误城市）。

## 2. 高德服务（`services/amap_service.py`）

两种用法并存：

1. **MCP 工具**（Agent 用）：`MCPTool(name="amap", server_command=["uvx","amap-mcp-server"], env={"AMAP_MAPS_API_KEY": settings.vite_amap_web_key}, auto_expand=True)`
   - 首次 `get_amap_mcp_tool()` 时启动子进程并枚举可用工具（`maps_text_search`、`maps_weather`、`maps_geo` 等）。
   - `_available_tools` 用于日志与前端 `tools_count`。
2. **封装方法**（路由/服务用）：`AmapService` 提供
   - `search_poi(keywords, city)` / `get_poi_detail(poi_id)`
   - `get_weather(city)`：调 `maps_weather` 后当前**直接返回 `[]`**（`TODO: 解析实际的天气数据`）——天气数据实际由 Agent 直接消费工具返回文本，不经此方法。
   - `plan_route(origin, destination, route_type)` 等。
   - 单例：`get_amap_service()` / `reset_amap_service()`（后者同时清 `_amap_mcp_tool`，设置页保存后调用）。

## 3. 地图调度（`services/map_dispatcher.py`）

```python
MapProvider = Literal["google", "amap"]

get_map_provider():            # settings.google_maps_api_key 非空 → "google"，否则 "amap"
geocode_unified(address, city, *, address_zh="", address_en="") -> {"longitude","latitude"} | None
reset_google_geo_failure()     # 配置更新后允许重新尝试 Google
```

- 语言选择策略：Google 优先 `address_en`，高德优先 `address_zh`。
- **全局短路标志**：Google 地理编码失败过一次就置 `_google_geo_failed_flag = True`（带锁，只打印一次），
  后续同进程全部直接走高德，避免每个景点都等一次超时。设置页保存时 `reset_google_geo_failure()` 复位。
- 本 skill **只实现高德分支**：`get_map_provider()` 恒返回 `amap` 即可，`geocode_unified` 直接调用 `_geocode_amap_raw`。

## 4. LLM 服务（`services/llm_service.py`）

```python
class DirectOpenAILLM:            # 轻量适配器，兼容 hello_agents 的 llm 接口（.invoke/.provider/.model）
    def __init__(model, api_key, base_url, timeout)
    def invoke(messages, **kwargs) -> str   # 默认 stream=True 并拼接；支持 temperature/max_tokens/top_p/stop/
                                            # response_format/tools/tool_choice；支持一次性覆盖 timeout
def get_llm() -> DirectOpenAILLM            # 单例
def reset_llm()                             # 设置页保存后调用
```

三个关键细节（复刻时必须保留）：

1. **清系统代理**：`_clear_system_proxy_env()` 删除 `HTTP(S)_PROXY/ALL_PROXY`（大小写），否则访问内网 LLM 网关会 502。
2. **`trust_env=False`**：`httpx.Client` 不读环境代理。
3. **自定义 UA**：部分网关按 UA 拦截默认的 `OpenAI/Python`。

配置优先级：`settings.openai_*`（可被设置页热更新覆盖）→ `LLM_API_KEY/LLM_BASE_URL/LLM_MODEL_ID` → `OPENAI_API_KEY/OPENAI_BASE_URL/OPENAI_MODEL` → 默认 `gpt-4`/官方地址；超时 `LLM_TIMEOUT`（默认 60s，规划阶段另有 `TRIP_PLANNER_TIMEOUT` 默认 180s）。

## 5. 行程问答（`services/chat_service.py` + `routes/chat.py`）

`POST /api/chat/ask` → `TripChatRequest{message, trip_plan, history}`。
服务把当前 `trip_plan`（JSON 片段）+ 历史对话组装成 messages，调用 `get_llm().invoke(...)`，返回 `{success, reply}`。
前端 `AIChat.vue` 浮层使用（快速问题：价格、适合人群、餐饮建议）。

## 6. 服务层通用约定

- 所有外部调用都在**同步函数**里用 `requests`/`httpx` 完成，异步环境用 `asyncio.to_thread` 包装（项目既有模式，例如 `get_photo_bytes_from_xhs`）。
- 单例 + `reset_*()` 配对，配合设置页热更新。
- 异常类型化：`XHSCookieExpiredError`、`XHSFetchError`、`XHSImageProxyError`，路由层再映射成 HTTP 状态码。
- 缓存目录都在 `backend/data/`，随项目落盘；不做定时清理，靠读取时校验 TTL。