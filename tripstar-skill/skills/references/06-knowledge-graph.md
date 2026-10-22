# 06 · 知识图谱（构建规则 + 数据结构）

实现：`backend/app/services/knowledge_graph_service.py`（266 行，纯函数、无外部依赖）。
它把已生成的 `TripPlan` 转成 ECharts graph 数据，**不做检索、不做推理**，只用于可视化。

## 1. 入口

```python
build_knowledge_graph(trip_plan: TripPlan, language: str = "zh") -> {"nodes", "edges", "categories"}
```

调用点：`routes/trip.py` 的 `_run_trip_planning()`，在 `plan_trip` 成功后：

```python
await _update_task_state(task_id, stage="graph_building", progress=95, message="正在构建知识图谱...")
graph_data = build_knowledge_graph(trip_plan, language=request.language or "zh")
trip_result = TripPlanResponse(success=True, message=..., plan_id=task_id, data=trip_plan, graph_data=graph_data)
```

随后 `stage=completed` 一并持久化到 `data/trip_tasks/{id}.json` 的 `result` 里。

## 2. 输出结构

```ts
{ nodes: [{ id, name, category:int, symbolSize:int, itemStyle:{color}, value:string }],
  edges: [{ source, target, label }],
  categories: [{ name }] }
```

`category` 是 `categories` 的下标（0..7），`itemStyle.color` 按类别取固定色，`value` 是悬停详情字符串。

## 3. 八类节点与样式

| idx | 内部 key | 中文名 | 颜色 | symbolSize |
|---|---|---|---|---|
| 0 | city | 城市 | `#4A90D9` | 70 |
| 1 | day | 日程 | `#5B8FF9` | 45 |
| 2 | attraction | 景点 | `#5AD8A6` | 35 |
| 3 | hotel | 酒店 | `#F6BD16` | 35 |
| 4 | meal | 餐饮 | `#E8684A` | 25 |
| 5 | weather | 天气 | `#6DC8EC` | 28 |
| 6 | budget | 预算 | `#FF9845` | 40 |
| 7 | preference | 偏好/建议 | `#B37FEB` | 30 |

多语言：`_I18N` 内置 zh / en / ja 三套（分类名、边标签、文本模板），`_t(key, lang, **kw)` 取值并支持占位符
（如 `day_n` → `第{n}天` / `Day {n}` / `{n}日目`）。`lang` 从 `language` 归一（`zh-CN` → `zh`）。

## 4. 构建规则（顺序即代码顺序）

### ① 城市与根节点

```python
cities_list = trip_plan.cities or [trip_plan.city]
多城市：root_id = "trip_root"，name = " → ".join(cities)，value = "start ~ end"
       每个城市 city_<name>，edge(root → city, 行程)
单城市：root_id = "city_<trip_plan.city>"，value = "start ~ end"
```

### ② 每日节点

```python
day_id = f"day_{day.day_index}"
parent = city_node_ids.get(day.city) or root_id      # 逐日挂到对应城市
add_node(day_id, "第N天", 日程, day.date)
add_edge(parent -> day_id, 行程)
```

### ③ 景点（含游览顺序链）

```python
attr_id = f"attr_{day_index}_{i}_{attr.name}"
value = " | ".join([address, "游览{min}分钟", "门票¥{price}"])   # 有则拼
add_edge(day_id -> attr_id, 游览)
if i > 0: add_edge(prev_attr -> attr_id, 下一站)                 # 编码同天游览顺序
```

### ④ 酒店

```python
hotel_id = f"hotel_{day_index}_{hotel.name}"
value = "价格区间 | ¥成本/晚"（有 estimated_cost 时）否则只放 price_range
add_edge(day_id -> hotel_id, 入住)
```

### ⑤ 餐饮

```python
meal_id = f"meal_{day_index}_{j}_{meal.name}"
name = "{餐型}: {meal.name}"；value = "¥estimated_cost"（>0 时）
edge label = 餐型（早餐/午餐/晚餐/小吃）
```

### ⑥ 天气

```python
w_id = f"weather_{w.date}"；name = "{day_weather} {day_temp}°C"；value = w.date
按 day.date == w.date 匹配到某一天 → add_edge(day_id -> w_id, 天气)
匹配不到就是孤立节点（数据里日期格式不一致时会这样）
```

### ⑦ 预算

```python
budget_total：name = "总预算 ¥{total}"，edge(root -> budget_total, 预算)
子项：景点/酒店/餐饮/交通/城际交通（值 > 0 才建），id = f"budget_{label_key}"，edge(budget_total -> 子项, label)
```

### ⑧ 总体建议

```python
suggestion_overall：name = overall_suggestions 的**前 30 字 + "…"**（超长才截断），value = 完整文本
edge(root -> suggestion_overall, 建议)
```

## 5. 已知行为与坑

1. **节点 id 含天数**：同一家酒店连着住两晚会产生两个同名不同 id 的节点（`hotel_1_x` / `hotel_2_x`），不会被合并。
2. **天气靠日期字符串精确匹配**：`WeatherInfo.date` 与 `DayPlan.date` 格式不一致就断链。
3. **建议节点 name 被截断到 30 字**，完整内容只在 `value`（tooltip）里。
4. **预算明细来自 LLM 的 budget 字段**，而前端预算表是从行程反算的——两者可能不一致（前端编辑后会覆盖 budget）。
5. **分类名是本地化文本**，前端必须做归一化映射（见 07 的 `CATEGORY_KEY_MAP`）才能上色与翻译。
6. `node_ids` 去重：重复 id 不会产生第二个节点，但边仍会重复添加。

## 6. 复刻要点

- 保持"纯函数"：输入 `TripPlan`，输出 dict；不要查库、不要发网络请求，才能随时重算。
- 分层语义固定为 `城市 → 日程 → 实体`，`下一站` 边单独表达顺序，便于前端做路径高亮。
- 颜色/尺寸与前端映射解耦：后端给 `itemStyle.color`，前端另有一套渐变（`KG_NODE_CATEGORY_COLORS`）用于 SVG 节点，两者互不依赖。
- 若新增实体类型（如"交通段"），需同时扩 `NODE_COLORS/NODE_SIZES/_I18N` 与前端 `CATEGORY_KEY_MAP`。