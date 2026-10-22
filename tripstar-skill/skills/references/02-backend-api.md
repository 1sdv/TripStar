# 02 · 后端 API 与任务状态机

所有路由都以 `/api` 为前缀（`main.py`：`app.include_router(x.router, prefix="/api")`），
除 `settings.router`（`prefix="/settings"`）、`memory_routes`（`prefix="/memory"`）、`trip`、`poi`、`map`、`chat` 各自的内部前缀。

## 1. 端点清单

### 行程规划（`routes/trip.py`，router prefix=`/trip`）

| 方法 | 路径 | 请求 | 响应 / 行为 |
|---|---|---|---|
| POST | `/api/trip/plan` | `TripRequest` | `{task_id, plan_id(=task_id), status:"processing", ws_url:"/api/trip/ws/{id}", message}`，随后 `asyncio.create_task(_run_trip_planning)` |
| GET | `/api/trip/status/{task_id}` | — | 任务快照（同 WS 事件结构，含 `result`）；不存在 → 404 |
| GET | `/api/trip/history?limit=10` | — | `{items:[{plan_id,task_id,city,cities,start_date,end_date,travel_days,updated_at,overall_suggestions}]}`（只含 completed） |
| GET | `/api/trip/health` | — | `{status, tools_count, ...}`（`tools_count = weather_agent.list_tools() + hotel_agent.list_tools()`） |
| WS | `/api/trip/ws/{task_id}` | — | 先 `accept()` 并推一条当前快照，之后每次状态更新推事件；终态后自行关闭 |

### 图片 / POI（`routes/poi.py`，prefix=`/poi`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/poi/image?name=…` 或 `?url=…` | **图片代理**。返回 `image/*` 字节 + `Cache-Control: public, max-age=86400`。`name` 走关键词缓存（miss 自动重搜）；`url` 仅允许 `*.xiaohongshu.com` / `*.xhscdn.com`。`ValueError`→400，`XHSImageProxyError`→502 |
| GET | `/api/poi/photo?name=…&city=…` | 取景点图片直链（`{success, data:{photo_url}}`）；查不到返回空串由前端占位 |
| GET | `/api/poi/search?keywords=…&city=…` | 高德 POI 搜索（`map_dispatcher`） |
| GET | `/api/poi/detail/{poi_id}` | 高德 POI 详情 |

### 地图能力（`routes/map.py`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/map/poi?keywords=&city=&citylimit=` | POI 搜索（统一调度） |
| GET | `/api/map/weather?city=…` | 天气（统一调度） |
| POST | `/api/map/route` | `RouteRequest{origin_address,destination_address,origin_city,destination_city,route_type}` |
| GET | `/api/map/health` | 地图服务健康检查 |

> 说明：`Result.vue` **不调用** `/api/map/*`（地图渲染直接用 AMap JS API）；这些端点供其他调用方/调试使用。

### 其他

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat/ask` | `TripChatRequest{message, trip_plan, history}` → `{success, reply}`（行程问答） |
| GET | `/api/settings` | 运行时配置（密钥掩码返回：`前4字符 + •••••••• + 后4字符`） |
| PUT | `/api/settings` | 部分更新（`exclude_unset`）→ 持久化 `runtime_settings.json` → **重置所有单例**（llm/amap/google/geo-failure/trip_planner）→ 返回掩码后的最新值 |
| GET | `/api/memory/list?user_id=` | 有效记忆（已衰减 + TOP-K） |
| POST | `/api/memory/add-explicit?user_id=&content=` | 手动偏好（`source=explicit`，初始权重 8.5） |
| DELETE | `/api/memory/item?user_id=&memory_id=` | 删除单条 |
| DELETE | `/api/memory/clear?user_id=` | 清空该用户 |
| GET | `/` | 有 `frontend/dist` 时返回首页，否则返回服务信息 JSON |
| GET | `/health` | `{status:"healthy", service, version}` |
| GET | `/docs`、`/redoc` | OpenAPI 文档 |

未开启记忆模块（`ENABLE_USER_MEMORY != true`）时，`/api/memory/*` 统一返回 `{code:400, msg:"记忆模块未开启"}`。

## 2. 任务状态机

`_TASKS_DATA_DIR = backend/data/trip_tasks`；内存字典 `_tasks: Dict[task_id, task]`；磁盘 `{task_id}.json`。

任务字典字段（`_create_task_state`）：

```
task_id, plan_id, status('processing'|'completed'|'failed'), stage, progress(0-100),
message, error, result(TripPlanResponse 或 dict), request_payload, subscribers(list[Queue]),
created_at / updated_at
```

阶段与进度（由 `plan_trip` 中 `_emit_progress` 驱动）：

| stage | progress | 触发点 |
|---|---|---|
| `submitted` | 5 | `POST /plan` 返回前 |
| `initializing` | 10 左右 | `_run_trip_planning` 拿到 agent 后 |
| `attraction_search` | `10 + (i/n)*65` | 每城市景点搜索前 |
| `weather_search` | 上一步 + `max(65/n/3, 3)` | 每城市天气查询前 |
| `hotel_search` | 再 + 一步 | 每城市酒店搜索前 |
| `planning` | ~85 | 交给规划 Agent 前 |
| `graph_building` | 95 | `build_knowledge_graph` 前 |
| `completed` / `failed` | 100 | 结束 |

> `n` = 城市数。进度是**单调递增的粗粒度估算**，不要在前端做精确等式判断。

## 3. 持久化

`_persist_task_state()` 原子写（先 `.json.tmp` 再 `replace`）：

```json
{
  "task_id": "6c83aff5",
  "plan_id": "6c83aff5",
  "status": "completed",
  "stage": "completed",
  "progress": 100,
  "message": "旅行计划生成成功",
  "result": { "success": true, "message": "...", "plan_id": "...", "data": { TripPlan }, "graph_data": { nodes, edges, categories } },
  "error": null,
  "request_payload": { TripRequest 的 model_dump(mode="json") }
}
```

- 启动时 `_load_persisted_tasks()` 预加载全部 `*.json`；未到终态的任务被改写为 failed（`服务已重启…请重新生成`）。
- `_get_task()` 先内存后磁盘，因此**历史计划即使进程重启也能在结果页恢复**。
- `_build_history_item()` 只挑 completed 的摘要，供首页历史列表使用。

## 4. WebSocket 事件结构

```json
{
  "task_id": "...", "plan_id": "...",
  "status": "processing|completed|failed",
  "stage": "attraction_search|...",
  "progress": 42,
  "message": "正在查询 西安 的天气...",
  "error": null,
  "request_payload": {...},
  "result": { "success": true, "data": {...}, "graph_data": {...} }
}
```

前端 `subscribeTripTask()`（`services/api.ts`）逻辑：
`onmessage` → `JSON.parse` → `onTaskEvent(event)`；`status==='completed'` 时用 `event.result` resolve；
`status==='failed'` 时 reject(`event.error || event.message`)；`onerror`/`onclose`（未 settle）→ reject。
`ws_url` 为相对路径时拼上 `ws(s)://<apiBase>`。断线后可用 `resumeTripPlan(taskId)`：先 `GET /status`，未完成再重连 WS。

## 5. 中间件与 CORS

- **路径重写中间件**：若路径含 `/api/` 但不以 `/api/` 开头（云托管/反代前缀），截取到 `/api/...`，避免 404。
- CORS 来自 `settings.cors_origins`（逗号分隔，默认 localhost:5173/3000 各两种写法），`allow_credentials=True`，方法/头全放开。
- 生产静态托管：`frontend/dist` 存在时挂 `/assets` + SPA catch-all（`api/` 前缀仍返回 404 JSON）。

## 6. 复刻要点

1. `task_id` 用 `uuid4()[:8]`，短且够用；`plan_id` 与 `task_id` 相同，前端两处名字混用时要兼容。
2. 提交端点**必须立即返回**，否则长任务会被网关掐断。
3. `_update_task_state` 是唯一的状态写入口：改内存 → 持久化 → 广播 → 清理死队列。
4. WS 推送要容忍"订阅者已断开"（记录 dead queues 并移除），否则内存泄漏。
5. 端点返回结构保持扁平：`{success, message, data}` / `{code, msg, data}` 两种风格在项目里并存（旧接口 vs 记忆接口），复刻时选一种即可，但别在同一模块里混用。