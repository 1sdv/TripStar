# 01 · 架构与端到端数据流

## 1. 组成

| 层 | 技术 | 位置 | 端口 |
|---|---|---|---|
| 前端 | Vue 3 + Vite 6 + TypeScript + Ant Design Vue 4 + ECharts 5 + Swiper 11 + html2canvas | `frontend/` | 5173（dev） |
| 后端 | FastAPI + uvicorn + Pydantic v2 + hello-agents（SimpleAgent/MCPTool） | `backend/` | 8000 |
| 数据 | 小红书（景点/图片）、高德（POI/地理编码/天气/路线）、LLM（OpenAI 兼容） | 外部 | — |
| 存储 | 任务 JSON 文件 + 图片磁盘缓存 + 可选 SQLite（记忆） | `backend/data/`、`backend/memory.db` | — |

前端 dev 由 Vite 代理 `/api` → `http://localhost:8000`（`vite.config.ts` 的 `server.proxy`）。
生产（Docker）时后端直接托管 `frontend/dist`：`app.mount('/assets')` + SPA catch-all，前后端同源。

## 2. 目录职责

```
backend/
├─ run.py                     uvicorn 启动（读 settings.host/port，reload=True）
├─ requirements.txt           hello-agents[protocols]、fastapi、uvicorn、httpx、PyExecJS、aiosqlite…
├─ .env                       OPENAI_*/XHS_COOKIE/VITE_AMAP_* 等
├─ runtime_settings.json      设置页热更新的持久化覆盖（不存在则用环境变量）
├─ app/
│  ├─ config.py               Settings + 运行时覆盖 + 掩码 + validate/print
│  ├─ api/main.py             FastAPI 实例、CORS、路径重写中间件、路由挂载、静态托管
│  ├─ api/routes/
│  │  ├─ trip.py              任务提交/状态/历史/WS + 任务持久化 + 记忆提取触发
│  │  ├─ poi.py               小红书图片代理/取图/POI 检索
│  │  ├─ map.py               POI/天气/路线/健康检查（地图能力统一出口）
│  │  ├─ chat.py              针对当前行程的问答
│  │  ├─ settings.py          运行时配置读写（写后重置所有单例）
│  │  └─ memory_routes.py     偏好记忆 CRUD
│  ├─ agents/trip_planner_agent.py   多智能体编排 + 提示词 + JSON 修复
│  ├─ services/
│  │  ├─ xhs_service.py       小红书签名客户端、搜索、图片缓存、高德地理编码
│  │  ├─ map_dispatcher.py    供应商路由（amap / google）+ 统一 geocode
│  │  ├─ amap_service.py      高德 MCP 工具封装 + 能力封装
│  │  ├─ google_map_service.py  Google 实现（★ 本 skill 范围外）
│  │  ├─ knowledge_graph_service.py  TripPlan → {nodes, edges, categories}
│  │  ├─ llm_service.py       DirectOpenAILLM（清代理 + trust_env=False）
│  │  ├─ chat_service.py      行程问答的 prompt 组装与调用
│  │  └─ xhs_sign/            小红书 x-s/x-t 签名 JS（PyExecJS 执行）
│  ├─ memory/                 记忆模型/存储/管理器/偏好提取
│  └─ models/schemas.py       全部 Pydantic 契约
└─ data/
   ├─ trip_tasks/{task_id}.json   已完成/进行中的任务快照（含 result.graph_data）
   └─ photo_cache/{sha256}.img|.meta  图片字节缓存（24h TTL，10MB 上限）

frontend/
├─ vite.config.ts      端口 5173、/api 代理、@ 别名、manualChunks（echarts/html2canvas/swiper/maps 分包）、
│                      构建期把 VITE_AMAP_SECURITY_JS_CODE 注入 index.html 的 __AMAP_SECURITY_JS_CODE__
├─ index.html          含 __AMAP_SECURITY_JS_CODE__ 占位符
└─ src/
   ├─ main.ts          路由（'/'→Landing, '/result'→Result，均懒加载）+ Antd + i18n
   ├─ App.vue          全局壳（NavBar 之外的页面容器）
   ├─ views/Landing.vue    表单 + 进度 stepper + 历史计划列表（唯一入口页）
   ├─ views/Result.vue     结果展示（详见 07）
   ├─ views/Home.vue       ★ 遗留页，未被路由或任何组件引用（可忽略/删除）
   ├─ components/      NavBar（设置弹窗 + 语言 + 导航）、AIChat（问答浮层）、OverviewAttractionCard（概览卡）
   ├─ services/api.ts  axios 实例 + runtime settings + submit/poll/WS + memory API
   ├─ types/index.ts   前端类型契约
   ├─ i18n/            vue-i18n 9，zh-CN/ja-JP/en-US 三语
   └─ styles/global.css  全局设计系统（7429 行，含 Paper-Kit 风格的通用组件样式）
```

## 3. 一次规划的完整时序

```
① 用户填写 Landing 表单（cities[]/start_date/transportation/accommodation/preferences/free_text）
② generateTripPlan() → POST /api/trip/plan
   后端：task_id = uuid4()[:8]；写入 _tasks[task_id]；持久化 JSON；返回 {task_id, plan_id, ws_url}
   然后 asyncio.create_task(_run_trip_planning(task_id, request))  ← 后台继续
③ 前端立刻连 WebSocket /api/trip/ws/{task_id}（api.ts 的 subscribeTripTask）
④ 后端逐阶段 _update_task_state(...) → _persist_task_state + _broadcast_task_event
   前端 onTaskEvent 更新 loadingProgress / loadingStatus
⑤ 后端内部：
   a. stage=initializing → get_trip_planner_agent()（首次会拉起高德 MCP：uvx amap-mcp-server）
   b. 逐城市（progress 10→75）：
      - 景点：search_xhs_attractions(city, keywords, lang)（同步 → asyncio.to_thread）
      - 天气：weather_agent.run("请查询{city}的天气信息")
      - 酒店：hotel_agent.run(...)
   c. stage=planning → planner_agent.run(planner_query, temperature=0.2, timeout=180)
      → _parse_response 多层修复 → TripPlan
   d.（可选）记忆提取：user_id 存在且 ENABLE_USER_MEMORY=true → asyncio.create_task
   e. stage=graph_building(95) → build_knowledge_graph(trip_plan, language)
⑥ _update_task_state(status=completed, progress=100, result=TripPlanResponse(...))
⑦ 前端 WS 收到 status=completed + result → 写 sessionStorage → router.push('/result?plan_id=…')
⑧ Result.vue 渲染（详见 07）；右侧 AIChat 可继续提问（POST /api/chat/ask）
```

## 4. 失败与降级路径

| 环节 | 失败表现 | 代码内已有对策 |
|---|---|---|
| 小红书 Cookie 失效 | `XHSCookieExpiredError`（code 300011/msg 含"异常"） | 任务标记 failed，错误文案带【认证失败】前缀 |
| LLM 未配置 | Agent 初始化抛错 | `validate_config()` 仅警告；实际调用失败 → 任务 failed |
| 天气工具无结果 | 返回含"无法/失败/error"等字样 | Google 分支才降级到高德 REST；高德分支直接透传文本让 LLM 兜底 |
| LLM 输出被截断/污染 | `json.JSONDecodeError` | `_sanitize_json_str` → `_fix_unescaped_quotes` → `_repair_truncated_json` → 正则提取 → LLM 修复 |
| 规划超时 | `TimeoutError` | `_run_planner_with_retry` 重试一次并追加"保守补齐"指令 |
| 图片直链过期 | 403 | 前端改走 `/api/poi/image?name=`，后端 miss 时重搜新直链（最多 2 次） |
| 高德 JS Key 缺失 | 地图空白 + 警告 | `message.warning('请先在设置中配置高德地图 JS Key')` |
| 服务重启丢失内存任务 | status 非终态 | `_normalize_loaded_task` 把未完成任务改成 failed，提示重新生成 |

## 5. 设计取舍（复刻时值得保留的）

- **任务是"提交即返回 + 长连接推送"**，而不是一个长 HTTP 请求：避免反代/网关空闲超时，且刷新页面可用 `/api/trip/status/{id}` 回补。
- **结果页数据走 sessionStorage 优先**：从 Landing 跳转过来零延迟；直链/刷新才回源后端。
- **知识图谱后端算、前端排版**：语义聚类（分类/关系）在后端，视觉表现（坐标/力导）在前端，互不耦合。
- **设置改动即热生效**：`PUT /api/settings` 后重置 `llm/amap/google/geo-failure/trip_planner` 全部单例，前端通过自定义事件重建地图。
- **图片必须代理**：小红书 CDN 有 Referer 校验且直链限时，浏览器直引必然 403。