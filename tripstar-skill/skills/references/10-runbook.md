# 10 · 运行手册（环境 · 启动 · 验证 · 排障）

## 1. 前置条件

| 依赖 | 版本/说明 |
|---|---|
| Python | 3.10+（推荐 3.11/3.12）。本机无 python 时可用 `uv python install 3.12` 或 `uv venv` 自动下载 |
| Node.js | 18+（本项目验证于 Node 22.16 / npm 10.9） |
| uv | 可选但推荐（拉高德 MCP 用 `uvx amap-mcp-server`） |
| 网络 | 需要访问：LLM 网关、小红书、高德 API；离线只能跑通前端骨架 |

> 📌 **本机环境已实测（优先看这里）**：解释器在 `E:/000xuexiing/conda/1/envs/py311/python.exe`，
> 该环境的 `site` 会因含中文路径的 editable `.pth` 直接崩（GBK 解码），**必须** `-S` + `PYTHONPATH` 启动；
> 两个 `.env` 已就绪（含 Google Maps Key → 前端会先等 5s 超时再降级高德）；
> CORS 只放行 `localhost`，用 `127.0.0.1` 打开会全站 Network Error。
> 完整实测记录、结果页 28 项验收、以及已修复的「地图标记丢失」缺陷见 **`11-local-run-verified.md`**。

## 2. 后端配置（`backend/.env`）

> 🎫 **凭据怎么拿、放哪里、怎么验证**：见 `12-credentials-setup.md`（高德两个 Key + 安全密钥 / 小红书 Cookie / 模型）。
> 一键体检：`pwsh scripts/check-credentials.ps1 -Online`（逐项 PASS/WARN/FAIL，并打印服务端错误体）。

```dotenv
# LLM（可被设置页热更新覆盖）
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# 高德：Web 服务 Key（地理编码/POI/路线/MCP 环境变量）
VITE_AMAP_WEB_KEY=...
# 高德：前端 JS API Key（地图渲染）
VITE_AMAP_WEB_JS_KEY=...

# 小红书 Cookie（景点搜索必备；过期会报【认证失败】）
XHS_COOKIE=...

# 可选
ENABLE_USER_MEMORY=false          # 偏好记忆总开关
MEMORY_USE_SQLITE=false           # true → memory.db 持久化
TRIP_PLANNER_TIMEOUT=180          # 规划阶段超时（秒）
LLM_TIMEOUT=60
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

也可全部留空启动：服务能跑，`validate_config()` 只打印警告，实际调用会失败。
设置页（`PUT /api/settings`）写入的值会落到 `backend/runtime_settings.json`，**优先级高于 .env**。

> 范围外但存在：`GOOGLE_MAPS_API_KEY` / `GOOGLE_MAPS_PROXY`。保持为空即走高德分支；本 skill 不需要它们。

## 3. 启动

### 3.1 后端（Windows PowerShell）

```powershell
cd backend
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.venv\Scripts\python.exe run.py
# → http://localhost:8000/docs
```

等价的纯 pip 方式：

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

首次请求规划时才会拉起高德 MCP 子进程（`uvx amap-mcp-server`），所以第一次会慢几秒。

### 3.2 前端

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # vue-tsc 类型检查 + vite 打包（唯一的类型闸门）
npm run preview    # 预览 dist
```

`frontend/.env`：`VITE_API_BASE_URL=http://localhost:8000`（不填则用同源；dev 下有 `/api` 代理兜底）、
`VITE_AMAP_WEB_JS_KEY`、`VITE_AMAP_SECURITY_JS_CODE`（高德 JS API 2.0 的安全密钥，构建期注入 index.html）。

### 3.3 Docker

```bash
docker compose up --build      # 后端同时托管 frontend/dist，访问 http://localhost:8000
```

## 4. 一键验证脚本

`scripts/verify.ps1` 会依次检查：

1. `GET /health` → 后端存活；
2. `GET /api/settings` → 配置读取（并提示哪些 Key 未配置）；
3. `GET /api/trip/history?limit=3` → 任务持久化可用；
4. 前端 `npm run build`（可选，加 `-BuildFrontend`）→ TypeScript 与打包是否通过。

```powershell
pwsh scripts/verify.ps1                      # 只查后端
pwsh scripts/verify.ps1 -BuildFrontend       # 同时构建前端
pwsh scripts/verify.ps1 -BaseUrl http://127.0.0.1:8000
```

## 5. 端到端冒烟（手工）

```powershell
$body = @{
  city='西安'; cities=@(@{city='西安'; days=2}); start_date='2026-09-16'; end_date='2026-09-17'
  travel_days=2; transportation='公共交通'; accommodation='经济型酒店'
  preferences=@('历史文化'); free_text_input=''; language='zh-CN'
} | ConvertTo-Json -Depth 5

$r = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/trip/plan -ContentType 'application/json' -Body $body
$r.task_id
# 轮询
Invoke-RestMethod "http://localhost:8000/api/trip/status/$($r.task_id)" | ConvertTo-Json -Depth 4
```

成功后后端日志会依次打印 `attraction_search → weather_search → hotel_search → planning → graph_building → completed`，
`data/trip_tasks/<id>.json` 出现文件，结果页可直接用 `?plan_id=<id>` 打开。

## 6. 离线预览结果页（不需要后端与 Key）

`assets/sample-result.json` 是一份真实的 `TripPlanResponse`（含 `graph_data`）。用法：打开前端 → F12 控制台：

```js
fetch('/path/to/sample-result.json').then(r => r.json()).then(res => {
  sessionStorage.setItem('tripPlan', JSON.stringify(res.data))
  sessionStorage.setItem('graphData', JSON.stringify(res.graph_data))
  sessionStorage.setItem('planId', res.plan_id)
  location.href = '/result?plan_id=' + res.plan_id
})
```

或直接把 JSON 内容内联：

```js
sessionStorage.setItem('tripPlan', JSON.stringify(<res.data 的内容>))
```

结果页会渲染概览/预算/每日/天气/知识图谱；地图会提示"请先在设置中配置高德地图 JS Key"（无 Key 时的预期行为）。

## 7. 排障表

| 现象 | 原因 | 处理 |
|---|---|---|
| `/docs` 打不开 | 端口占用 / 依赖未装 | `netstat -ano | findstr :8000`；重装 requirements |
| 启动即报配置验证失败 | `.env` 有非法值 | 看 `print_config()` 输出；`validate_config` 只警告，抛错多为解析失败 |
| 任务一直 `processing` | LLM/小红书阻塞 | 看后端日志最后一条 stage；确认 `OPENAI_*`、`XHS_COOKIE` |
| 报【认证失败】 | 小红书 Cookie 过期/被风控（300011） | 更新 `XHS_COOKIE`（设置页或 .env） |
| 任务 `failed: 行程 JSON 解析失败` | LLM 输出被截断/污染且修复失败 | 提高 `TRIP_PLANNER_TIMEOUT`、换更强模型、降低 `max_tokens` 压力 |
| 地图空白 | 未配 `VITE_AMAP_WEB_JS_KEY`；或容器高度 0 | 设置页填 Key（热生效）；检查 `.right-map` 高度 |
| 地图是灰色格子/一片蓝 | 高德 JS **安全密钥**缺失 | 配 `VITE_AMAP_SECURITY_JS_CODE` 并重启 dev server |
| 景点图片 403 / 不显示 | 直链被 Referer 拦；或缓存过期 | 前端确保走 `/api/poi/image?...`；后端会重搜 |
| 导出 PNG 里地图空白 | 未开 `preserveDrawingBuffer` | 保持 `WebGLParams.preserveDrawingBuffer = true` |
| 导出 PNG 缺图片/二维码 | `<img>` 未加载完就截图 | 保持 `exportAsImage` 里等待 `img.complete/onload` |
| 结果页刷新后空白 | sessionStorage 被清或 planId 不匹配 | 直接访问 `/result?plan_id=<id>` 由后端回补 |
| 保存设置后地图不更新 | 事件未派发/未监听 | 确认 `RUNTIME_SETTINGS_UPDATED_EVENT` 流程 |
| 记忆列表为空 | `ENABLE_USER_MEMORY=false` | 设为 true 并重启后端 |
| 访问 LLM 一直超时/502 | 系统代理被继承 | 代码已清代理 + `trust_env=False`；再查 `HTTPS_PROXY` 是否被别处注入 |
| 前端 `npm run build` TS 报错 | 类型契约改动未同步 | 见 `09-contracts.md` |
| Python 连 `--version` 都崩，报 `init_import_site` / `UnicodeDecodeError: 'gbk'` | 环境里 editable `.pth` 含中文路径，`site` 按 GBK 解码 | 用 `-S` + `PYTHONPATH=<site-packages>` 启动（见 11 §2） |
| `ImportError: cannot import name 'eval_type_backport'` | `fastmcp` 与 pydantic 2.14 不兼容 | 不影响主链路；需要时 `pip install "pydantic<2.12"`（见 11 §3） |
| 结果页全空、控制台 `Network Error` | 用 `127.0.0.1:5173` 打开但 CORS 只放行 `localhost` | 换 `localhost` 打开，或补全 `CORS_ORIGINS`（见 11 §5） |
| 地图只有底图、**没有任何景点标记**，控制台 `Invalid Object: Pixel(NaN, NaN)` | 地图容器高度为 0（`height:100%` 穿过 `min-height` 不解析） | `.map-card { height: 500px }`（本仓库已修，见 11 §6） |
| 「导出攻略」不含地图 | 导出时不在「景点地图」分节，容器不可见被跳过 | 先切到地图分节再导出（既有行为） |

## 8. 数据与清理

| 路径 | 内容 | 清理方式 |
|---|---|---|
| `backend/data/trip_tasks/*.json` | 任务与结果（含 graph_data） | 直接删；删了历史就没了 |
| `backend/data/photo_cache/*.img/.meta` | 图片缓存（24h TTL） | 直接删；不影响功能 |
| `backend/memory.db` | 偏好记忆（SQLite 模式） | 直接删；或走 `/api/memory/clear` |
| `backend/runtime_settings.json` | 设置页覆盖值 | 删掉即回退到 `.env` |

## 9. 最小可运行子集（只想要结果展示页）

不需要后端与任何 Key，只要能造出一份 `TripPlanResponse`：

1. 复制 `frontend/`，删掉 `services/api.ts` 里的 WS/settings 依赖或保留但不调用；
2. 保留 `types/`、`i18n/`、`components/{NavBar,OverviewAttractionCard,AIChat}`、`views/Result.vue`；
3. `Result.vue` 里删除 Google 分支（`initGoogleMap` / `addGoogleAttractionMarkers` / `drawGoogleRoutes` / `google*` 状态）
   与相关依赖 `@googlemaps/js-api-loader`、`@types/google.maps`；
4. 用 `assets/sample-result.json` 直接喂 `tripPlan` / `graphData`；
5. 地图若要真显示，仍需要高德 JS Key；不需要地图时可直接删掉 `map` 分节。