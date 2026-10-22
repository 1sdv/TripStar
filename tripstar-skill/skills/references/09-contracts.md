# 09 · 前后端字段契约（Pydantic ↔ TypeScript）

后端 `backend/app/models/schemas.py`，前端 `frontend/src/types/index.ts`。两侧**字段名一致、可选性有差异**。

## 1. 请求模型

### `CityStay`
| 字段 | 后端 | 前端 |
|---|---|---|
| `city` | `str` 必填 | `string` |
| `days` | `int` 必填，`ge=1, le=15` | `number` |

### `TripRequest`
| 字段 | 后端 | 前端 `TripFormData` |
|---|---|---|
| `city` | `str = ""`（兼容单城市） | `string` |
| `cities` | `List[CityStay] = []` | `CityStay[]?` |
| `start_date` | `str` 必填 `YYYY-MM-DD` | `string` |
| `end_date` | `str` 必填 | `string` |
| `travel_days` | `int` 必填 `1..30` | `number` |
| `transportation` | `str` 必填 | `string` |
| `accommodation` | `str` 必填 | `string` |
| `preferences` | `List[str] = []` | `string[]` |
| `free_text_input` | `Optional[str] = ""` | `string` |
| `language` | `Optional[str] = "zh"` | `string?` |
| `user_id` | `Optional[str] = ""` | `string?` |

后端 `model_validator(normalize_cities)`：只填 `city` 时自动补 `cities=[CityStay(city, travel_days)]`；
只填 `cities` 时把 `city` 设为第一个城市。因此前端两种传法都能用。

### 其他请求
- `POISearchRequest{keywords, city, citylimit=True}`
- `RouteRequest{origin_address, destination_address, origin_city?, destination_city?, route_type="walking"}`
- `TripChatRequest{message, trip_plan(对象), history: [{role, content}]}`（前端同名类型 `ChatMessage`/`TripChatRequest`）

## 2. 响应模型

### `Location` — `{longitude: float, latitude: float}`

### `Attraction`
| 后端 | 前端 |
|---|---|
| `name: str` | `name: string` |
| `address: str` | `address: string` |
| `location: Location` | `location: Location` |
| `visit_duration: int` | `visit_duration: number` |
| `description: str` | `description: string` |
| `category: Optional[str] = "景点"` | `category?: string` |
| `rating: Optional[float] = None` | `rating?: number` |
| `photos: List[str] = []` | —（前端未使用） |
| `poi_id: Optional[str] = ""` | —（前端未使用） |
| `image_url: Optional[str] = None` | `image_url?: string` |
| `ticket_price: int = 0` | `ticket_price?: number` |
| `reservation_required: Optional[bool] = False` | —（前端 `Result.vue` 直接读，类型未声明） |
| `reservation_tips: Optional[str] = ""` | 同上 |

> 差异：后端 `ticket_price` 是必填有默认值（int），前端是可缺省；`reservation_*` 前端 TS 类型里缺省但模板在用——
> 复刻时建议补齐为 `reservation_required?: boolean; reservation_tips?: string`。

### `Meal` — `type: str`（`breakfast|lunch|dinner|snack`）、`name`、`address?`、`location?`、`description?`、`estimated_cost: int = 0`
前端 `type` 是字面量联合类型，其余为可选；`estimated_cost?: number`。

### `Hotel` — `name`、`address=""`、`location?`、`price_range=""`、`rating=""`、`distance=""`、`type=""`、`estimated_cost: int = 0`
前端对应字段全同名，`location`/`estimated_cost` 可选，其余必填字符串。

### `DayPlan`
| 后端 | 前端 |
|---|---|
| `date: str` | `date: string` |
| `day_index: int`（从 0 开始） | `day_index: number` |
| `city: str = ""` | `city?: string` |
| `is_transfer_day: bool = False` | `is_transfer_day?: boolean` |
| `transfer_info: Optional[str] = ""` | `transfer_info?: string` |
| `description: str` | `description: string` |
| `transportation: str` | `transportation: string` |
| `accommodation: str` | `accommodation: string` |
| `hotel: Optional[Hotel]` | `hotel?: Hotel` |
| `attractions: List[Attraction] = []` | `attractions: Attraction[]` |
| `meals: List[Meal] = []` | `meals: Meal[]` |

### `WeatherInfo`
| 后端 | 前端 |
|---|---|
| `date: str` | `date: string` |
| `city: str = ""` | `city?: string` |
| `day_weather / night_weather: str = ""` | 同 |
| `day_temp / night_temp: Union[int, str] = 0` | `number` |
| `wind_direction / wind_power: str = ""` | 同 |

后端 `field_validator(parse_temperature)` 会剥掉 `°C`/`℃`/`°` 并转 int（失败给 0）。
**前端假定拿到的是数字**，`formatWeatherTemp` 里仍做了 `Number.isFinite` 兜底。

### `Budget`
| 后端 | 前端 |
|---|---|
| `total_attractions/hotels/meals/transportation: int = 0` | `number` |
| `total_inter_city_transport: int = 0` | `total_inter_city_transport?: number` |
| `total: int = 0` | `number` |

### `TripPlan`
`city: str`、`cities: List[str] = []`、`start_date: str`、`end_date: str`、`days: List[DayPlan]`、
`weather_info: List[WeatherInfo] = []`、`overall_suggestions: str`、`budget: Optional[Budget]`。
前端 `budget?: Budget`（可选），其余一致。

### `TripPlanResponse`
`success: bool`、`message: str = ""`、`plan_id: Optional[str]`、`data: Optional[TripPlan]`、`graph_data: Optional[KnowledgeGraphData]`。
前端同名且 `plan_id?`/`data?`/`graph_data?` 均可选。

> 注意前端还用了 `TripPlan.hotel_recommendations`（导出 HTML 中的酒店区块），
> 该字段**不在** `TripPlan` 里——代码用交叉类型 `TripPlan & { hotel_recommendations?: [...] }` 读取，可能恒为空。

## 3. 知识图谱

| 后端 `GraphNode` | 前端 `GraphNode` |
|---|---|
| `id: str` | `id: string` |
| `name: str` | `name: string` |
| `category: int = 0` | `category: number` |
| `symbolSize: int = 30` | `symbolSize: number` |
| `itemStyle: Optional[dict]` | `itemStyle?: { color: string }` |
| `value: Optional[str] = ""` | `value?: string` |

`GraphEdge{source, target, label=""}`、`GraphCategory{name}`、`KnowledgeGraphData{nodes, edges, categories}` 两侧一致。

## 4. 任务与运行时配置类型（仅前端）

```ts
type TripTaskStatus = 'processing' | 'completed' | 'failed'
type TripTaskStage  = 'submitted'|'initializing'|'attraction_search'|'weather_search'
                    | 'hotel_search'|'planning'|'graph_building'|'completed'|'failed'
interface TripTaskEvent { task_id, plan_id, status, stage, progress, message, error?, result? }
interface TripHistoryItem { plan_id, task_id, city, start_date, end_date, travel_days, updated_at, overall_suggestions? }
interface BackendRuntimeSettings { vite_amap_web_key, vite_amap_web_js_key, google_maps_api_key, google_maps_proxy, xhs_cookie, openai_api_key, openai_base_url, openai_model }
interface RuntimeSettings extends BackendRuntimeSettings { api_base_url: string }
```

> 历史接口的 `items[]` 后端还会返回 `cities: string[]`（多城市展示用），前端类型里没有声明——按需补。

## 5. 契约维护建议

1. 后端改字段时同步改 `types/index.ts`，否则 `vue-tsc`（`npm run build` 会跑）会报错——这是本项目唯一的类型检查闸门。
2. 可选性差异集中在 `ticket_price / estimated_cost / budget / day.city / weather.city`，改前端默认值时先确认后端默认值。
3. 所有金额、温度字段坚持"纯数字"约定（见主 skill 的六条契约）。
4. 若新增 `graph_data` 实体类型，需要同时改：`NODE_COLORS/NODE_SIZES/_I18N`（后端）、`CATEGORY_KEY_MAP/KG_NODE_CATEGORY_COLORS`（前端）、三语 JSON。