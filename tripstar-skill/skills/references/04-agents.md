# 04 · 多智能体编排（`agents/trip_planner_agent.py`，1134 行）

## 1. 结构

`MultiAgentTripPlanner`（`__init__` 时构建，单例 `get_trip_planner_agent()` / `reset_trip_planner_agent()`）：

| 成员 | 说明 |
|---|---|
| `self.llm` | `get_llm()` 返回的 `DirectOpenAILLM` |
| `self.map_provider` | `get_map_provider()` → `"amap"` 或 `"google"`（本 skill 只实现 amap） |
| `self._active_tool` | 挂在各 Agent 上的地图工具（amap → `MCPTool("amap", uvx amap-mcp-server)`） |
| `self.weather_agent` | `SimpleAgent("天气查询专家", llm, WEATHER_AGENT_PROMPT)` + `add_tool(_active_tool)` |
| `self.hotel_agent` | `SimpleAgent("酒店推荐专家", …)` + 同一工具 |
| `self.planner_agent` | `SimpleAgent("行程规划专家", llm, PLANNER_AGENT_PROMPT)`，**不挂工具** |

景点搜索**不再走 Agent**（`ATTRACTION_AGENT_PROMPT = ""` 已弃用），改为直接调用小红书的 `search_xhs_attractions()`。

## 2. 工具调用协议（关键设计）

hello-agents 的 `SimpleAgent` 在这里被当作"按格式输出工具调用指令的 LLM"，提示词强制输出**单行**：

```
[TOOL_CALL:<tool_name>:key=value,key2=value2]
```

- 天气：`[TOOL_CALL:amap_maps_weather:city=西安]`
- 酒店：`[TOOL_CALL:amap_maps_text_search:keywords=酒店,city=西安]`

提示词模板（`_build_weather_agent_prompt(tool_prefix)` / `_build_hotel_agent_prompt(tool_prefix)`）都包含三条硬约束：
① 必须用工具，不要自己编；② 工具名必须原样写成 `{prefix}_maps_weather` / `{prefix}_maps_text_search`；
③ 输出必须是单行方括号格式，不要 JSON block、不要多余字符。

`tool_prefix` 由供应商决定（`amap` / `google`），因此同一套提示词可以适配两种工具命名。

> 复刻提示：这种"文本协议 + 正则派发"方式依赖模型严格遵循格式；如果换成支持原生 function calling 的模型，
> 建议改成 tools/tool_choice，能显著降低格式失败率（`DirectOpenAILLM.invoke` 已支持透传 `tools`）。

## 3. 规划提示词（`PLANNER_AGENT_PROMPT`）

输出必须是单个 JSON 对象，字段与 `TripPlan` 对齐，并在提示词里给出完整示例。硬性要求（原文要点）：

1. `weather_info` 必须覆盖每一天，每条带 `city`；温度必须是纯数字（不带 `°C`）。
2. 每天 2–3 个景点（城际移动日 1–2 个）；每天必须含早/中/晚三餐。
3. **budget 与价格字段必须是纯数字**，禁止 `30+54+120=324`、禁止 `"324元"`（提示词里明确标注"违反将导致系统崩溃"）。
4. 预约字段 `reservation_required` / `reservation_tips` 若上游提供必须原样保留。
5. **不要在 JSON 里写 `image_url`**——图片由前端按景点名去小红书取。
6. 多城市：每个 day 必须有 `city`；切换当天 `is_transfer_day: true` 且 `transfer_info` **只给交通方式与大致时长**，
   严禁编造车次/班次/具体时刻；`cities` 列出全部途经城市；`budget.total_inter_city_transport` 统计城际交通。

## 4. 主流程 `plan_trip(request, progress_callback)`

```
cities = request.cities（TripRequest.normalize_cities 已保证非空）
_lang_hint = 非中文时追加 " Please respond in English/…"
for idx, city_stay in enumerate(cities):
    progress_base = int(10 + idx/total*65)
    progress_step = max(int(65/total/3), 3)

    [1] attraction_search → search_xhs_attractions(city, keywords, lang)   ← asyncio.to_thread
        keywords = request.preferences[0] if preferences else "景点"
    [2] weather_search    → weather_agent.run(f"请查询{city}的天气信息{_lang_hint}")
        （google 分支若返回含"无法/失败/错误/error/unknown/抱歉/sorry"→ _fallback_amap_weather）
    [3] hotel_search      → hotel_agent.run(...)
planner_response = await _run_planner_with_retry(request, all_attractions, all_weather, all_hotels, memory_snippet)
trip_plan = _parse_response(planner_response, request)
补全 trip_plan.cities（LLM 常漏）；单城市时补全每个 day.city
```

`_emit_progress` 兼容同步/异步 `progress_callback`（返回 coroutine 时 await）。

### `_build_planner_query()`

把"城市天数分配 + 起止日期 + 交通 + 住宿 + 偏好 + 每城市的景点/天气/酒店原始文本 + 额外要求 + 语言要求"
拼成一段自然语言提示，末尾附 7 条要求（每天 2–3 景点、三餐、每天一个具体酒店、考虑距离、返回完整 JSON、
经纬度要真实、信息不足时用保守建议补齐而不要输出"无法查询"）。多城市再追加 6 条多城市要求。
`memory_snippet`（用户历史偏好）存在时插在基本信息之后，并要求"在景点选择、餐饮、住宿、行程节奏中体现"。

### `_run_planner_with_retry()`

```python
timeout = int(os.getenv("TRIP_PLANNER_TIMEOUT", "180"))
try:  await asyncio.to_thread(planner_agent.run, query, timeout=timeout, temperature=0.2)
except Exception as exc:
    if "timeout" not in str(exc).lower() and "timed out" not in ...: raise
    # 追加"信息不足就用保守建议补齐，但必须输出完整合法 JSON"后重试一次
```

## 5. JSON 解析与修复流水线（`_parse_response`）

这是本项目"抗 LLM 输出污染"的核心，按顺序尝试 6 个候选，全部失败才动用 LLM 修复：

```
① 提取 JSON 文本：```json … ``` → ``` … ``` → 第一个 { 到最后一个 } → 否则 ValueError
② _sanitize_json_str：去 ``` 包裹、去 // 与 /* */ 注释、去控制字符、修尾逗号 `,]`/`,}`、
   中文引号 “”→'、‘’→'、全角冒号→:、全角逗号→,、
   修算术表达式 `"total_attractions": 30+54+120=324` → 取等号后结果（无等号则受限 eval）
③ 候选集：基础清理 / _fix_unescaped_quotes（字符串内未转义 " 改 '）/ _repair_truncated_json /
   二者的组合 / 正则 `\{[\s\S]*\}` 提取后再修 / 正则+截断修复
④ 依次 json.loads → TripPlan(**data)，首个成功即返回
⑤ 全失败 → _llm_repair_json()（送 head 500 + tail 2000 字符，temperature=0，max_tokens=1500）再解析
⑥ 仍失败 → ValueError("行程 JSON 解析失败: …")
```

`_repair_truncated_json()` 三步骤：闭合未终止字符串 → 反复剥掉尾部非法碎片并去悬挂逗号 →
用括号栈（跳过字符串内容）精确补齐缺失的 `]` / `}`。

## 6. 降级与兜底

- `_fallback_amap_weather(city)`：**仅 Google 分支**触发。跳过 MCP，直接用 `httpx` 请求
  `https://restapi.amap.com/v3/weather/weatherInfo`（`key=vite_amap_web_key, city=最后一段城市名, extensions=all`），
  把 `forecasts[0].casts` 拼成 `date: 白天X 25°C, 夜间Y 15°C, 风向风力` 的多行文本返回。
  高德分支本身不降级——工具失败的回执直接透传给规划 LLM，由提示词第 7 条要求它"用保守建议补齐"。
- `_create_fallback_plan(request)`：构造一个"占位行程"（每天 2 个假景点 + 三餐），当前**未在主流程使用**，
  仅供极端情况手工调用。

## 7. 复刻清单

- [ ] 三个 Agent（weather / hotel / planner）的职责与工具挂载分离。
- [ ] 工具名与提示词前缀一致（`amap_maps_weather`、`amap_maps_text_search`）。
- [ ] 景点走小红书服务、天气/酒店走地图 MCP。
- [ ] 规划阶段 `temperature=0.2`、独立超时、超时重试一次。
- [ ] JSON 修复 6 步流水线 + LLM 修复兜底。
- [ ] 规划结果后置补全（`cities`、单城市 `day.city`）。
- [ ] 逐城市进度回调，兼容同步/异步回调函数。