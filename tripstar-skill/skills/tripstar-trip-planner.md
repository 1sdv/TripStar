---
name: TripStar 复刻指南（全栈 skill）
description: 当需要阅读、运行、改造或复刻 TripStar（FastAPI 多智能体旅行规划 + Vue3 结果展示页）时使用；范围不含 Google Maps 服务。包含后端任务链路、小红书取数、高德地图、知识图谱构建，以及结果展示页（天气看板/预算/地图/KG/导出）的逐段实现规范。
---

# TripStar 复刻指南

TripStar 是一个"输入城市和日期 → 多智能体生成完整旅行计划 → 图形化展示"的应用。
本 skill 把它拆成可独立复刻的模块，**Google Maps 相关服务被排除**：地图只用高德（AMap JS API 2.0 + 高德 MCP/REST）。

## 何时使用

- 要读懂或改造本项目的规划流程（`POST /api/trip/plan` → WebSocket 进度 → `TripPlanResponse`）。
- 要复刻或重写结果展示页（`Result.vue`：概览、预算、地图、每日行程、知识图谱、天气、导出 PNG）。
- 要迁移知识图谱、天气看板、预算联动等纯前端渲染逻辑到别的项目。
- 要排查"计划生成失败/JSON 解析失败/地图不显示/图片 403"这类问题。

## ⛔ 硬性规则：缺配置时先停下来要配置，**绝不编造结果**

这是本项目最容易被做错的地方：`.env` 不在（或 Key 是占位符）时，**不要**"按字段约定自己写一份行程"来交差。

**禁止**（任何情况下）：

- 编造 `TripPlan`（景点/坐标/天气/预算/餐饮/酒店）并当成项目真实输出；
- 把 `assets/sample-result.json` 说成"刚生成的行程"；
- 在 LLM / 小红书 Cookie / 高德 Key 缺失时声称"已生成攻略""计划已保存"；
- 往 `backend/data/trip_tasks/` 写入伪造任务，冒充真实历史。

**必须**（按顺序执行）：

1. **先探测**：`pwsh scripts/check-credentials.ps1`（无 `.env` 时会直接 FAIL，并逐项打印获取路径）。
   没有 `.env` 时先建模板：`Copy-Item backend\.env.example backend\.env`、`Copy-Item frontend\.env.example frontend\.env`。
2. **报告缺口**：逐项说明缺哪个变量、会导致什么（表见「首次运行」一节），以及仓库里是否根本没 `.env`。
3. **给获取指引**：指向 `references/12-credentials-setup.md` 对应小节 —— §1 高德（Web服务 Key / JS API Key / 安全密钥）、
   §2 小红书 Cookie、§3 模型（Key/Base URL/Model，含方舟 `ep-xxxx` 说明）。
4. **停下来等用户**：明确写"填好这 3 样后告诉我，我再启动后端把行程跑出来"。**不要**用占位数据继续推进。

**唯一例外**（必须同时满足，否则仍按上面执行）：

- 用户**明确**说只要看界面 / 离线预览 / 不需要真实数据；
- 产物标注为 **demo / mock**，并说明数据来源（用 `assets/sample-result.json` 时写明"仓库内历史样例，非本次生成"）；
- 不写入 `backend/data/`，不谎称已生成。

**标准话术模板**（缺凭据时照抄改写即可）：

> 当前仓库没有可用的 `.env` 凭据，因此**无法真实调用** TripStar 的多智能体后端（LLM、小红书 Cookie、高德 Key 均缺失）。
> 需要你补齐 3 项后我才能生成真实行程：
> 1. `backend/.env`：`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL_ID`、`XHS_COOKIE`、`VITE_AMAP_WEB_KEY`
> 2. `frontend/.env`：`VITE_AMAP_WEB_JS_KEY`、`VITE_AMAP_SECURITY_JS_CODE`
> 3. 获取步骤见 `references/12-credentials-setup.md`（§1 高德 / §2 小红书 / §3 模型），填完跑
>    `pwsh scripts/check-credentials.ps1 -Online` 应 0 FAIL。
> 是否要我先把模板复制出来（`Copy-Item backend\.env.example backend\.env`）等你填？

## 首次运行：先备齐 4 个凭据（最容易卡住的一步）

| 凭据 | 变量 | 放哪 | 不配的后果 |
|---|---|---|---|
| 高德 **Web 服务** Key | `VITE_AMAP_WEB_KEY` | `backend/.env` | 地理编码/POI/天气/酒店全废 → 景点无坐标、地图无标记 |
| 高德 **Web端(JS API)** Key | `VITE_AMAP_WEB_JS_KEY` | `frontend/.env` 或设置页 | 「景点地图」空白 |
| 高德 **安全密钥 jscode** | `VITE_AMAP_SECURITY_JS_CODE` | `frontend/.env` | 地图灰格，控制台 `INVALID_USER_SCODE`（改后需重启 dev server） |
| 小红书 **Cookie** | `XHS_COOKIE` | `backend/.env` | 景点搜索失败 → 任务报【认证失败】 |
| 模型 Key/Base/Model | `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL_ID` | `backend/.env` 或设置页 | 任务直接 failed |

- **高德**：`console.amap.com` → 应用管理 → 创建应用 → 加两个 Key（服务平台分别选 **Web服务** / **Web端(JS API)**），JS Key 详情页里取 **安全密钥**。
- **小红书 Cookie**：登录 `xiaohongshu.com` → F12 → Network → 任意请求 → 复制 Request Headers 里 `cookie` 整行值（需含 `web_session` 才是登录态）。
- **模型**：任何 OpenAI 兼容平台即可。本机用的是火山方舟 `https://ark.cn-beijing.volces.com/api/v3`，**注意模型 ID 要在「在线推理」里已创建/启用接入点**，否则报 `InvalidEndpoint.ClosedEndpoint`。
- **先体检再启动**：`pwsh scripts/check-credentials.ps1 -Online`，逐项 PASS/WARN/FAIL 并直接给修复方向。
- 完整获取步骤与错误码对照：`references/12-credentials-setup.md`。

## 目录与文档定位（先读这里）

本 skill 的深度内容在同目录的 `references/` 下。定位方式：本文件所在目录即插件目录的 `skills/`，
因此 `references/*.md` 与它同级；若路径未知，在 `%USERPROFILE%\.pi-desktop\plugins\` 下搜索
`tripstar-trip-planner.md` 即可得到插件根目录。

| 需要什么 | 读哪个文件 |
|---|---|
| 整体架构、端到端数据流、目录职责 | `references/01-architecture.md` |
| 全部 HTTP/WS 端点、任务状态机、持久化 JSON | `references/02-backend-api.md` |
| 小红书取数、高德 MCP/REST、图片代理缓存、LLM 客户端 | `references/03-services.md` |
| 多智能体提示词、工具调用协议、JSON 修复流水线 | `references/04-agents.md` |
| 偏好记忆（权重衰减/合并/TOP-K/SQLite） | `references/05-memory.md` |
| 知识图谱构建规则（节点/边/分类） | `references/06-knowledge-graph.md` |
| **结果展示页逐段实现规范（重点）** | `references/07-result-frontend.md` |
| 前端骨架：路由、API 层、i18n、设计系统、Landing | `references/08-app-frontend.md` |
| 前后端字段契约（Pydantic ↔ TS 全字段） | `references/09-contracts.md` |
| 运行、配置、验证、排障 | `references/10-runbook.md` |
| **本机实测运行记录 + 结果页 28 项验收 + 已修缺陷** | `references/11-local-run-verified.md` |
| **首次运行：高德 Key / 小红书 Cookie / 模型配置怎么拿 + 体检** | `references/12-credentials-setup.md` |

## 五分钟数据流

```
Landing.vue 表单
  └─ generateTripPlan(form)  POST /api/trip/plan
       ├─ 立即返回 {task_id, plan_id, ws_url}
       └─ WebSocket /api/trip/ws/{task_id} 推送 {status, stage, progress, message}
            阶段: submitted(5) → initializing → attraction_search → weather_search
                  → hotel_search → planning → graph_building(95) → completed(100)
  后端 _run_trip_planning → MultiAgentTripPlanner.plan_trip
       ├─ 逐城市: 小红书景点搜索 → 天气 Agent → 酒店 Agent（amap MCP 工具）
       ├─ 规划 Agent 输出 JSON → 多层 JSON 修复 → TripPlan
       └─ build_knowledge_graph(TripPlan) → graph_data
  └─ 结果 {success, plan_id, data: TripPlan, graph_data}
Landing 写 sessionStorage(tripPlan / graphData / planId) → router.push('/result?plan_id=…')
Result.vue 优先读 sessionStorage，失效时 GET /api/trip/status/{id} 回补
```

## 六条不可违背的契约

1. **`TripPlan` 是唯一事实源**：结果页所有区块（概览/预算/地图/每日/KG/天气/导出）都从同一份 `TripPlan` 派生，没有额外接口。
2. **`graph_data` 由后端算好**：`{nodes, edges, categories}` 是 ECharts graph 格式，前端只负责布局与画线，不重新构建语义。
3. **图片走后端代理**：小红书直链有时效签名+防盗链，前端一律用 `/api/poi/image?name=` 或 `?url=`，不要直接引用 CDN。
4. **金额字段必须是纯数字**：`ticket_price/estimated_cost/budget.*` 禁止出现 `30+54=84` 或 `"324元"`；前端 `recalculateBudgetTotals()` 依赖数值相加。
5. **天气温度必须是数字**：后端 `WeatherInfo.parse_temperature` 会剥掉 `°C/℃`，前端 `Math.round` 后拼 `°C`。
6. **地图供应商由后端配置决定**：`google_maps_api_key` 非空才走 Google，否则走高德（本 skill 只实现高德分支）。

## 运行（已验证，优先用这条）

```powershell
# 后端：本机 conda 环境必须加 -S + PYTHONPATH
#   （否则 site 模块按 GBK 解码含中文路径的 editable .pth，Python 直接起不来）
cd backend
$env:PYTHONPATH = "<PY_ENV>\Lib\site-packages"       # 你的 site-packages 目录
& "<PY>" -S -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000   # 你的 python.exe

# 前端
cd frontend
npm install
npm run dev -- --port 5173 --host 127.0.0.1
```

- 结果页必须用 **`http://localhost:5173`** 打开（`CORS_ORIGINS` 只放行 localhost，用 127.0.0.1 会全站 Network Error）。
- 看任意历史计划：`http://localhost:5173/result?plan_id=<backend/data/trip_tasks 里的 task_id>`。
- 没有 conda 环境的机器：`uv venv .venv` → `uv pip install -r requirements.txt` → `.venv\Scripts\python.exe run.py`。
- 最小配置在 `backend/.env`（LLM/`XHS_COOKIE`/`VITE_AMAP_WEB_KEY`）与 `frontend/.env`（`VITE_AMAP_WEB_JS_KEY`、`VITE_AMAP_SECURITY_JS_CODE`）。
- **验收**：把 `scripts/ui-assert.js` 粘进 DevTools 控制台，应得到 `28 pass / 0 fail`（实测基线见 `11-local-run-verified.md`）。
- 脚本：`scripts/start-backend.ps1`、`scripts/start-frontend.ps1`、`scripts/verify.ps1`、`scripts/ui-assert.js`。

## 结果展示页速查（细节见 07）

- 单页面 + `v-show` 分节，`activeSection` ∈ `overview|budget|map|days|knowledge-graph|weather`，**不是路由**。
- 六块各自独立初始化：Swiper（概览）、预算联动（纯 computed）、AMap（地图）、Collapse（每日）、ECharts force（KG）、CSS 天气动效（天气）。
- 天气看板天气图标是**纯 CSS 画的**（cloud/sun/rays/rain/bolt/flake + `weather-*` keyframes），不是图片。
- KG 初始位置 = 度数最高节点居中 + 按分类分扇区四层极坐标，再交给 `layout:'force'` 松弛；`emphasis.focus:'adjacency'` 做邻接高亮。
- 导出 PNG = `buildExportHTML()` 生成 800px 独立 HTML → `html2canvas(scale:2)` → `a[download]`；地图先单独 `captureMapScreenshot()` 截成 dataURL 嵌入。
- **地图容器必须有确定高度**（`.map-card{height:500px}`）：高度 0 时 AMap 抛 `Invalid Object: Pixel(NaN, NaN)`，标记全丢。
- **结果页用 `localhost:5173` 打开**：`CORS_ORIGINS` 不含 127.0.0.1 变体，否则全站 `Network Error`、页面空状态。
- 验收基线：`scripts/ui-assert.js` → `28 pass / 0 fail`（实测见 `11-local-run-verified.md` §7）。

## 工作方式

- 复刻某一块时，**先读该块对应的 reference，再动手**；不要凭印象改字段名（前后端字段有刻意差异，见 09）。
- **首次接手一个陌生环境**：先 `pwsh scripts/check-credentials.ps1 -Online` 再启动。
  不要假设 `.env` 里填了值就可用——实测遇到过"Key 齐全但方舟接入点已关闭（`InvalidEndpoint.ClosedEndpoint`）"、
  "高德 Web/JS 两个 Key 配成同一个"、"Cookie 只有 a1 没有 `web_session`"这类情况。
- 改动后端响应结构时，同步检查 `09-contracts.md` 两侧与 `Result.vue` 的消费点。
- 任何"看起来能跑但页面空白"的问题，先按 `10-runbook.md` 的检查表定位（sessionStorage 优先级、`v-if` vs `v-show`、容器高度为 0、Key 缺失）。
- 不要引入 Google Maps 依赖：`Result.vue` 中的 `initGoogleMap`/`addGoogleAttractionMarkers`/`drawGoogleRoutes` 与
  `google_map_service.py` 属于**范围外**，复刻时只保留高德分支与 `mapProviderType` 开关即可。