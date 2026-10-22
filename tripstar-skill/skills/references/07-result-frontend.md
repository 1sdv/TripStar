# 07 · 结果展示页实现规范（`frontend/src/views/Result.vue`，4706 行）

这是本项目最复杂的单个文件，也是复刻的重点。它把一份 `TripPlan` + `graph_data` 渲染成六个可视区块，
并支持编辑预算、重排景点、导出 PNG。全文分 4 段：`<template>` 1–572、`<script setup>` 574–2975、
`<style scoped>` 2977–4605、`<style>`（全局，给地图气泡用）4607–4706。

> 复刻顺序建议：骨架（分节+导航）→ 概览 Swiper → 每日行程 → 天气看板 → 预算联动 → 知识图谱 → 地图 → 导出。

---

## 1. 页面骨架

### 1.1 布局结构

```
.result-container           深色渐变底 + .lower-shade 遮罩（fixed，z-index 0）
├─ <NavBar @brand-click @cta-click>      顶部导航（含设置弹窗、语言切换）
└─ main.result-main  (z-index 2, padding 70px 20px 44px)
   ├─ .content-wrapper   (max-width 1400px, 毛玻璃卡片)
   │  ├─ .top-switch-nav
   │  │  ├─ .top-switch-menu-wrap > a-menu(mode=horizontal, :selected-keys=[activeSection])
   │  │  └─ .top-switch-actions  [刷新地图 | 编辑行程/保存/取消 | 导出图片]
   │  ├─ a-card#overview
   │  ├─ .top-info-section  (同一行放 budget 与 map，用 v-show 切换)
   │  ├─ a-card#knowledge-graph
   │  ├─ a-card.days-card   (a-collapse accordion)
   │  └─ a-card#weather
   ├─ .empty-state-panel   (tripPlan 为空时)
   ├─ a-back-top
   └─ <AIChat :trip-plan="tripPlan">      右下角问答浮层
```

### 1.2 分节机制（关键：不是路由）

`const activeSection = ref('overview')`，取值为
`'overview' | 'budget' | 'map' | 'days' | 'knowledge-graph' | 'weather'`。

- 菜单点击 → `scrollToSection({key})`：若 key 以 `day-` 开头则切到 `days` 并展开对应面板，否则 `activeSection.value = key`。
- **每个区块是 `v-show`**（保留 DOM，切回来不重建、地图/Swiper/KG 状态不丢）。
- 例外：天气卡同时带 `v-if="tripPlan.weather_info?.length > 0"`（无天气数据时彻底不渲染）。
- 菜单项按数据条件显示：`budget` 需 `tripPlan.budget`，`weather` 需有 `weather_info`。

> 复刻陷阱：如果把分节改成 `v-if` 或真路由，地图容器会被销毁重建、ECharts 需要重新 `resize()`，
> 而且 `?plan_id=` 刷新恢复逻辑会失效。请保留 `v-show`。

### 1.3 生命周期

```ts
onMounted:
  1) window.addEventListener(RUNTIME_SETTINGS_UPDATED_EVENT, handleRuntimeSettingsUpdated)
  2) planId = route.query.plan_id || sessionStorage.planId
  3) 若 sessionStorage.tripPlan 存在且 planId 匹配 → applyTripPlanPayload(...) 直接返回
  4) 否则若 planId 有值 → pollTaskStatus(planId) → status==='completed' 时 restoreTripPlanFromResponse
watch(activeSection): 切到 map → ensureMapReady()；knowledge-graph → ensureGraphReady()；overview → initOverviewSwiper()
watch(overviewAttractions): 校正 activeOverviewCard 并重建 Swiper
onUnmounted: 摘监听、destroyOverviewSwiper()、destroyCurrentMap()、销毁 kgChart 与 resize 监听
```

`applyTripPlanPayload({plan, graph, planId})` 是所有数据入口的唯一收口点：

```
tripPlan.value = plan；pendingBudgetItems = []
planId → sessionStorage.planId
sessionStorage.tripPlan = JSON.stringify(plan)
graph  → graphData/graphCategories + sessionStorage.graphData（无 graph 则 removeItem）
await loadAttractionPhotos()
按当前 activeSection 补初始化（map / knowledge-graph / overview swiper）
```

### 1.4 关键状态清单

| ref/变量 | 用途 |
|---|---|
| `tripPlan` | 当前计划（唯一事实源，编辑模式直接原地改） |
| `planId` | 任务/计划 ID，同时写 sessionStorage |
| `editMode` / `originalPlan` | 编辑开关与快照（取消时整体回滚） |
| `attractionPhotos: Record<name, url>` | 景点名 → 代理图片 URL 缓存 |
| `activeSection` / `activeDays` | 分节 / 展开的天 |
| `activeOverviewCard` | 概览 Swiper 当前卡索引（可 -1） |
| `budgetFilterType` / `budgetSortMode` / `pendingBudgetItems` | 预算筛选、排序、删除后可恢复项 |
| `activeWeatherIndex` | 天气看板当前天 |
| `graphData` / `graphCategories` / `kgChart` / `kgResizeHandler` | 知识图谱 |
| `map` / `mapProviderType` / `mapRefreshing` / `mapInitGeneration` | 地图实例与初始化代际号 |
| `googleMap` / `googleMarkers` / … | Google 分支（**范围外**，复刻时删除） |
| `overviewSwiper` | Swiper 实例 |

---

## 2. 概览区：Swiper 3D 卡片流

- `overviewAttractions = computed()`：遍历 `days` → `attractions`，扁平化为
  `{name,address,visit_duration,description,ticket_price,dayNumber(=dayArrayIndex+1),dayArrayIndex,order}`。
- `initOverviewSwiper()`（`await nextTick()` 后）：

```ts
new Swiper('.swiper', {
  modules: [EffectCoverflow, Keyboard, Mousewheel],
  effect: 'coverflow', grabCursor: true, centeredSlides: true,
  coverflowEffect: { rotate: 0, stretch: 0, depth: 100, modifier: 2.5 },
  keyboard: { enabled: true }, mousewheel: { thresholdDelta: 70 }, spaceBetween: 30, loop: false,
  breakpoints: { 640: { slidesPerView: 3 }, 1024: { slidesPerView: 4 } },
  on: { slideChange: (s) => (activeOverviewCard.value = s.activeIndex) },
})
// 初始停在 index = min(1, len-1)（不是 0，视觉上更居中）
```

- 卡片组件 `OverviewAttractionCard.vue`：props `{item, imageSrc, active}`，
  emits `hover` / `select-day(dayArrayIndex)` / `image-error(event)`；点击 "show more" → `goToDayFromOverview()` → `activeDays=[idx]` 且 `activeSection='days'`。
- 图片优先级：`attractionPhotos[name]` → 否则 `getAttractionImage()` 生成 **SVG dataURL 占位图**（深底 `#1a262f` + 白字景点名）。
- `.overview-meta` 展示日期区间、Plan ID、`overall_suggestions`。

---

## 3. 每日行程区

- `a-collapse v-model:activeKey="activeDays" accordion`，默认展开第 1 天（`[0]`）。
- 面板头：`第 N 天` + 城市标签（`day.city`）+ 城际移动标签（`day.is_transfer_day`）+ `day.date`。
- 城际移动横幅：`day.is_transfer_day && day.transfer_info` 时显示 🚄 + `transfer_info`。
- 基本信息三行：`description / transportation / accommodation`。
- 景点：`a-list :grid="{gutter:16, column:2}"` → 每张 `a-card`：
  - 图片：`toProxiedPhotoUrl(item.image_url) || getAttractionImage(item.name, index)`，`@error="handleImageError"`；
  - 序号角标（`index+1`）、门票角标 `¥ticket_price`；
  - 查看模式显示 `address / visit_duration+分钟 / description / rating`；
  - `reservation_required` 时显示 `📋 需提前预约` + `reservation_tips`；
  - 编辑模式把 address/visit_duration/description 换成 `a-input / a-input-number(10–480) / a-textarea`，并在 `#extra` 放 Up / Down / 删除。
- 酒店：`day.hotel` 存在时用 `a-descriptions(column=2)` 展示 `address / type / price_range / rating / distance(span=2)`。
- 餐饮：`a-descriptions(column=1 bordered)`，label 由 `getMealLabel(type)` 映射
  `breakfast/lunch/dinner/snack → i18n result.meals.*`，值 `meal.name - meal.description`。

编辑相关函数：

```ts
toggleEditMode()  // 深拷贝快照 originalPlan = JSON.parse(JSON.stringify(tripPlan))
saveChanges()     // editMode=false → recalculateBudgetTotals() → 写 sessionStorage → 地图刷新/销毁
cancelEdit()      // tripPlan = 快照；清空 pendingBudgetItems
deleteAttraction(dayIdx, attrIdx)  // 至少保留 1 个（否则 message.warning）→ splice → recalculateBudgetTotals
moveAttraction(dayIdx, attrIdx, 'up'|'down')  // 数组相邻元素交换
```

---

## 4. 天气看板（本项目最有辨识度的区块）

### 4.1 数据与选择

```ts
weatherList  = computed(() => tripPlan.weather_info ?? [])
selectedWeather = computed(() => list[clamp(activeWeatherIndex, 0, len-1)] ?? null)
selectWeatherDay(i)  // 列表项 mouseenter / click 均触发
watch(weatherList)   // 长度变化时把 activeWeatherIndex 归零，防止越界
```

布局：左右两栏 `.weather-dashboard` = `.weather-side`（大卡：日期/星期/城市/图标/温度/白天天气）+ `.weather-info-side`
（上部 `.week-list` 未来几天小卡，下部 `.today-info` 五项明细）。≤768px 变纵向。

### 4.2 日期与温度格式化

```ts
localeTag = computed(() => zh→'zh-CN' | ja→'ja-JP' | 其他→'en-US')
parseWeatherDate(raw)  // 先把 年/月/日、'.'、'/' 归一成 '-'，new Date 失败再用 /(\d{4})\D+(\d{1,2})\D+(\d{1,2})/ 兜底
formatWeatherDate(raw)      // Intl.DateTimeFormat(localeTag, {month:'short',day:'numeric',year:'numeric'})
formatWeatherWeekday(raw, short=false)  // weekday: 'short' | 'long'
formatWeatherTemp(t)        // 非数字 → '--'；否则 `${Math.round(Number(t))}°C`
```

### 4.3 天气 → 图标种类（关键词匹配，中英混合）

```ts
type WeatherIconKind = 'sun-shower' | 'thunder-storm' | 'cloudy' | 'flurries' | 'sunny' | 'rainy'

getWeatherIconKind(text)  // text = `${day_weather} ${night_weather}`
  1) /(雷|thunder|storm|lightning|雷暴|雷阵雨)/i        → 'thunder-storm'
  2) /(雪|snow|sleet|hail|冰雹|冻雨|雨夹雪)/i            → 'flurries'
  3) hasRain && hasSun(/晴|sun|clear/)                  → 'sun-shower'
  4) hasRain /(雨|rain|shower|drizzle|阵雨|小雨|中雨|大雨|暴雨)/i → 'rainy'
  5) /(云|阴|cloud|overcast|雾|霾|fog|mist|haze|wind|breeze|gale)/i → 'cloudy'
  6) 默认 'sunny'
```

### 4.4 图标是纯 CSS 画的

主图标与列表小图标是**同一套 DOM 结构**（`.weather-icon` + 修饰类），按 kind 切换模板：

| kind | DOM |
|---|---|
| `sun-shower` | `.cloud` + `.sun>.rays` + `.rain` |
| `thunder-storm` | `.cloud` + `.lightning > .bolt × 2` |
| `cloudy` | `.cloud` × 2 |
| `flurries` | `.cloud` + `.snow > .flake × 2` |
| `rainy` | `.cloud` + `.rain` |
| `sunny` | `.sun > .rays` |

动画（scoped 样式内定义）：`weather-spin`（太阳 12s 旋转、雪花 8/14s 反向）、`weather-float`（云上下浮动 5.5s）、
`weather-cloud`（云横向循环 4s）、`weather-rain`（雨滴位移 3s）、`weather-lightning`（闪电闪烁 2s/1.5s）。
复用要点：想换图形只需替换这 6 组模板 + 对应 class，不必引入图标库。

### 4.5 背景渐变按天气切换

```ts
getWeatherGradient(dayWeather)  // 返回 linear-gradient(140deg, …)
  雷 → #3a4a86→#5b3b8a | 雪 → #8bc6ec→#d9afd9 | 雨 → #4b6cb7→#182848
  雾霾 → #7b8799→#4a5568 | 阴 → #6d7f92→#3f4c6b | 默认(晴) → #72edf2→#5151e5
weatherSideStyle = computed(() => ({ '--weather-gradient': getWeatherGradient(...) }))
```

CSS 里 `.weather-side` 用 `background: var(--weather-gradient)`，`.weather-gradient` 叠一层纹理/遮罩。

### 4.6 降水/湿度/风力（无真实数据时的确定性推导）

```ts
getWeatherPrecipitation(text)  // 雷/暴雨 85% | 雨 65% | 雪 55% | 阴 30% | 其他 10%
getWeatherHumidity(text)       // 雷 88% | 雨 78% | 雪 72% | 阴/雾/霾 62% | 其他 42%
getWeatherWind(weather)        // `${wind_direction} ${wind_power}`，缺失显示 '--'
```

> 说明：`WeatherInfo` 只有 `wind_direction/wind_power` 是真实字段，降水与湿度是**按天气类型估的展示值**。
> 复刻时可保留（视觉完整）或替换成真实数据源，但不要在 UI 上标注为实测值。

---

## 5. 预算区（数据双向联动，全前端计算）

### 5.1 汇总卡（右侧）

`tripPlan.budget` 直接展示：`total`、`total_attractions`、`total_hotels`、`total_meals`、
`total_transportation`、可选 `total_inter_city_transport`（`v-if`）。数字统一经 `formatBudgetAmount()`（整数不带小数、否则保留 2 位）。

### 5.2 明细表（左侧）

`budgetItems = computed()`（**从行程明细反算，不读 budget 子项**）：

```
每天景点 → {id: attraction-dayIdx-attrIdx, type:'attraction', name, amount: ticket_price, sourceIndex}
每天酒店 → {id: hotel-dayIdx, type:'hotel', name, amount: estimated_cost}
每天餐饮 → {id: meal-dayIdx-mealIdx, type:'meal', name: `${餐型} · ${name}`, amount: estimated_cost, sourceIndex}
交通     → 把 budget.total_transportation 按"有 transportation 文本的天"平均分摊，
           最后一天吃掉余数（Math.min(avg, remaining) + 尾差），id: transport-dayIdx
```

金额 `<= 0` 的项不显示。`filteredBudgetItems = computed()`：先按 `budgetFilterType`
（all/attraction/hotel/meal/transport）过滤，再按 `budgetSortMode` 排序
（`amountDesc|amountAsc|dayAsc|dayDesc`，同天按金额降序）。

### 5.3 就地编辑 / 删除 / 恢复

```ts
editBudgetItemAmount(item)   // window.prompt 输入新金额 → 校验 >=0 → window.confirm
                             // attraction→ticket_price  meal→estimated_cost  hotel→estimated_cost
                             // transport→差值法调整 budget.total_transportation
                             // → recalculateBudgetTotals(transportOverride) → 写 sessionStorage
deleteBudgetItem(item)       // 深拷贝到 pendingBudgetItems（含 insertIndex / accommodation 等恢复上下文）
                             // 真的从 day 里移除（hotel 同时清 accommodation；transport 清 transportation 文本）
                             // → 重算总额 → destroyCurrentMap()（地图标记已过期）
restoreBudgetItem(pending)   // 按 payload.type 插回原位置（splice(insertIndex,0,clone)）→ 重算 → 移除 pending 项
```

`recalculateBudgetTotals(transportationOverride?)`：分别累加 `ticket_price`、`estimated_cost`、`estimated_cost`，
交通取 override 或原值，最后重写整个 `tripPlan.budget`（`total` = 三项 + 交通）。
**注意：它不重算 `total_inter_city_transport`**（城际交通由 LLM 给出，前端不动）。
数值清洗统一走 `toBudgetNumber()`（NaN/<=0 → 0）与 `roundBudgetAmount()`（消除浮点误差）。

---

## 6. 知识图谱区（ECharts force）

### 6.1 数据进入

`graphData = KnowledgeGraphData | null`（来自 `response.graph_data`，同时缓存到 `sessionStorage.graphData`）。
`ensureGraphReady()`：无数据直接返回；已有实例则 `resize()`，否则 `initKnowledgeGraph()`。

### 6.2 分类归一化（关键：后端分类名是本地化的）

```ts
CATEGORY_KEY_MAP = {
  '城市'|'都市'|'city' → 'city',  '日程'|'行程'|'スケジュール'|'schedule' → 'schedule',
  '景点'|'観光地' → 'attraction', '酒店'|'ホテル' → 'hotel',
  '餐饮'|'食事'|'dining'|'グルメ' → 'meal', '天气'|'天気' → 'weather',
  '预算'|'予算' → 'budget', '偏好/建议'|'好み/提案'|'tips' → 'suggestion' }
normalizeCategoryKey(name)   // 先查原名，再查小写
getCategoryLabel(name)       // 归一命中 → t(`result.graph.categories.${key}`)，否则原样返回
```

于是**同一套前端可吃 zh/ja/en 三种后端输出**，颜色与文案都不依赖后端语言。

### 6.3 颜色与尺寸

```ts
KG_NODE_CATEGORY_COLORS = {          // 节点用渐变（start→end），图例点同源
  city:{#0B3D91,#5EEAD4}, schedule:{#0000FF,#E06BE0}, attraction:{#0F7A32,#C8FF6A},
  hotel:{#f59e0b,#fde68a}, meal:{#B91C1C,#FDBA74}, weather:{#0369A1,#BFDBFE},
  budget:{#ea580c,#fdba74}, suggestion:{#9333ea,#f0abfc} }
CATEGORY_COLORS = { city:#4A90D9, schedule:#5B8FF9, attraction:#5AD8A6, hotel:#F6BD16,
                    meal:#E8684A, weather:#6DC8EC, budget:#FF9845, suggestion:#B37FEB }  // tooltip/兜底

getKgNodeVisualPreset(rawSize, cat):
  base = rawSize>=70 ? 100 : rawSize>=45 ? 80 : 60    // 后端 symbolSize(70/45/35/30/28/25) → 三档
  size = round(base * KG_NODE_SIZE_SCALE(1.25))
  return { size, gradientStart, gradientEnd }
```

节点图形不是内置 circle，而是 `image://data:image/svg+xml,…`：
`buildFeatherCircleSvgDataUrl(size,start,end)` 画带 `linearGradient` 的圆（半径 `round(size*0.34)`，叠 `feGaussianBlur` 羽化），
并用 `kgNodeSymbolCache(size-start-end)` 缓存 dataURL，避免重复生成。

### 6.4 初始布局：度数最高的节点居中 + 分类扇区

`buildKgBoundaryPositionMap(nodes, edges, categories, width, height)`：

```
1) 统计每个节点在 edges 中出现的次数 → degree
2) rootNodeKey = degree 最大者（即 city_<城市> 或 trip_root），positionMap[root] = (cx, cy)
3) 其余节点按"归一化分类"分组；组按人数降序
4) 每组一个扇区：baseAngle = -π/2 + 2π*groupIndex/组数（从正上方顺时针）
   组内沿角度摊开：t = i/(n-1) - 0.5；angle = baseAngle + t*spread
                    spread = clamp(n*0.03, 0.55, 1.25)
   半径分层：layerFactors = [1, 0.9, 0.8, 0.7]；layerIndex = floor(i / layerStride)
   x = cx + cos(angle)*outerRadiusX*layerFactor；y = cy + sin(angle)*outerRadiusY*layerFactor
5) 用节点半径 + 8px 边距 clamp 回画布内
```

这些坐标作为 `x/y` 初值写入 series data；未命中时落到画布中心。

### 6.5 ECharts 配置要点

```ts
series: [{
  type: 'graph', layout: 'force',
  data: nodes.map(n => ({ ...n, x, y, fixed: Boolean(...), symbol: 'image://…', symbolSize: visual.size,
      itemStyle: { borderWidth: 0, shadowBlur: 0 },        // 渐变已画在 SVG 内，去掉描边阴影
      label: { show: size>=60, position:'inside', fontSize: 10|9|8, width: round(size*0.52),
               overflow:'truncate', ellipsis:'…', color:'#fff', fontWeight:'bold',
               formatter: 名字超过 7|6|5 字则截断加 '…' } })),
  links: edges.map(e => ({ ...e,
      lineStyle:{ color:'rgba(255,255,255,0.15)', width:1.5, curveness:0.1 },
      label:{ show:true, formatter: e.label||'', fontSize:10, color:'rgba(255,255,255,0.45)' } })),
  categories,
  roam: true, draggable: true,
  force: { initLayout:'none', repulsion: 520(窄屏 360), gravity: 0.06(窄屏 0.2),
           edgeLength: [95,220](窄屏 [60,140]), friction: 0.2, layoutAnimation: true },
  emphasis: { focus:'adjacency', lineStyle:{ width:4, color:'#d76e42' },
              itemStyle:{ borderColor:'#d76e42', borderWidth:3 } },
  edgeSymbol: ['none','arrow'], edgeSymbolSize: [0,8],
}]
```

- `initLayout:'none'` + 自算坐标 = **先按语义摆好，再让物理模拟微调**；比交给 ECharts 随机初始更稳定，每次刷新形状一致。
- **连线不是前端算的**：`links` 直接用后端 `edges` 的 `source/target` 字符串，ECharts 按 `id` 匹配端点。
- tooltip：节点显示 `name / 类型(getCategoryLabel) / detail(value)`；边显示 `label`。
- 图例在模板里手写 `.kg-legend`，每分类一个点（`getKgLegendDotStyle()` 返回同款 SVG 背景）+ 本地化名。
- 容器 `#kg-chart-container` 固定 `height: 600px`；窗口 resize 时整体重跑 `initKnowledgeGraph()`
  （因为初始坐标依赖容器宽高），并移除旧的 resize 监听防止泄漏。

---

## 7. 地图区（高德分支；Google 分支属范围外）

### 7.1 入口与代际号

```ts
initMap():
  generation = ++mapInitGeneration       // 每次初始化自增；异步回调里比对，避免旧实例覆盖新地图
  // （原项目此处先探测 Google key，有 key 则 initGoogleMap，失败/超时降级 —— 本 skill 跳过整段）
  await initAMap()
```

### 7.2 高德初始化

```ts
const mapJsKey = getRuntimeMapJsKey()   // localStorage 'tripstar.runtime.amap_web_js_key' → env VITE_AMAP_WEB_JS_KEY
if (!mapJsKey) { message.warning('请先在设置中配置高德地图 JS Key'); return }

const AMap = await AMapLoader.load({
  key: mapJsKey, version: '2.0',
  plugins: ['AMap.Marker','AMap.Polyline','AMap.InfoWindow','AMap.Driving','AMap.Walking'],
})
map = new AMap.Map('amap-container', {
  zoom: 12, center: [116.397128, 39.916527],    // [lng, lat]，注意顺序
  viewMode: '3D', mapStyle: 'amap://styles/darkblue',
  WebGLParams: { preserveDrawingBuffer: true },  // ★ 不开启，html2canvas 截出来是空白
})
await addAttractionMarkers(AMap)
```

容器 `<div id="amap-container">` 在 `.right-map` 内，`width/height:100%`；**父链上必须有一个可解析的确定高度**。

> ⚠️ **实测踩过的坑（必须照做）**：`.map-card` 若写成 `height:100%` + `min-height:500px`，
> 百分比高度**无法**从 `min-height` 解析 → `.ant-card-body` 变成 `height:auto` → `#amap-container` 实际高度 **0px**。
> 此时 AMap 2.0 执行 `map.add(markers)` 会在 `lngLatToContainer()` 里算出 NaN，抛
> `Invalid Object: Pixel(NaN, NaN)`，结果是**底图能出、景点标记全部丢失**（错误被 `initAMap` 的 catch 吞成
> `message.error('地图加载失败')`，很容易漏看）。
>
> 正确写法（本仓库已按此修正）：
>
> ```css
> .map-card { height: 500px; min-height: 500px; overflow: hidden; }  /* 不要用 height:100% */
> .map-card :deep(.ant-card-body) { height: 100%; padding: 0; }
> ```
>
> 验收：容器 `getBoundingClientRect().height > 0` 且 `#amap-container .tripstar-map-marker` 数量 = 景点数。

### 7.3 标记与气泡

```ts
// 只画有经纬度的景点，并保留 dayIndex / attrIndex / globalIndex
new AMap.Marker({
  position: [longitude, latitude],
  content: buildMarkerContent(dayIndex+1, attrIndex+1),  // 自定义 HTML：星形 SVG + 角标 "1-2"
  anchor: 'center', offset: new AMap.Pixel(0, 0), zIndex: 120 + index,
})
infoWindow = new AMap.InfoWindow({ isCustom: true, content: buildInfoWindowContent(attr),
                                   offset: new AMap.Pixel(0, -18), closeWhenClickMap: true })
marker.on('mouseover' → infoWindow.open(map, marker.getPosition()))
marker.on('mouseout'  → infoWindow.close())
marker.on('click'     → 再 open（兼容触屏）
map.add(markers)
```

`buildInfoWindowContent()` 输出 `.tripstar-map-tooltip` 四行：名称 / `第N天第M站` / 地址 / 游览分钟。
这些 class **必须放在无 scoped 的 `<style>`（4607–4706）**：气泡 DOM 由地图库插入，不受 scoped 作用域约束。
同段还覆写 `#amap-container .amap-info-content{background:transparent;border:none}` 与 `.amap-info-sharp{display:none}`。
所有注入文本都经 `escapeHtml()` 转义。

### 7.4 路线：真实道路 → 失败降级直线

```ts
drawRoutes(AMap, attractions):
  按 dayIndex 分组，组内按 attrIndex 排序
  preferredMode = detectRouteMode(day.transportation)
     /(步行|徒步|散步|walk)/i      → 'walking'
     /(驾车|开车|自驾|打车|出租车|car|drive|taxi)/i → 'driving'
     默认 'driving'
  相邻两点: searchRoutePath(AMap, mode, start, end)   // AMap.Walking / AMap.Driving(policy=LEAST_TIME)
      status==='complete' → extractRoutePath(result)（steps[].path 或 steps[].polyline，去重）
  成功用真实路径；失败或点数<2 → 退化为 [start, end] 直线
  new AMap.Polyline({ path, ...ROUTE_STYLE_PRESETS[实际使用的模式], showDir: true, zIndex: 90 })
map.add(polylines)；最后 map.setFitView([...markers, ...polylines])
```

| mode | color | weight | opacity | 线型 |
|---|---|---|---|---|
| driving | `#37b4ff` | 3.5 | 0.92 | solid，outline `rgba(4,19,32,.7)` |
| walking | `#6ad38f` | 3 | 0.9 | dashed `[12,8]` |
| straight | `#ffffff` | 1.5 | 0.62 | dashed `[10,10]` |

### 7.5 生命周期与刷新

- `ensureMapReady()`：已存在则 `map.resize()`，否则 `initMap()`。
- `refreshMap()`：`destroyCurrentMap()` → `nextTick()` → `initMap()`；按钮用 `mapRefreshing` 做 loading。
- `handleRuntimeSettingsUpdated()`（监听 `tripstar:runtime-settings-updated` 自定义事件）：销毁地图，若当前在地图分节则重建。
  **设置页改 Key 后无需刷新整页**。
- `onUnmounted` 必须 `destroyCurrentMap()`，否则地图实例与 WebGL 上下文泄漏。

---

## 8. 图片加载与代理

```ts
// 1) 行程内嵌直链（image_url）→ 走后端代理，规避 Referer 防盗链与时效签名
toProxiedPhotoUrl(url) = `${getRuntimeApiBaseUrl()}/api/poi/image?url=${encodeURIComponent(url)}`

// 2) 按景点名批量取图（并发 4，自建 worker 池）
loadAttractionPhotos():
  uniqueNames = days.flatMap(attractions.name) 去重，且跳过已缓存的
  并发 worker: GET `${apiBase}/api/poi/photo?name=&city=`
     → success && data.photo_url 时缓存 attractionPhotos[name] = `${apiBase}/api/poi/image?name=${name}`
  // ★ 不直接用返回的直链（限时签名会失效），一律改走 name 键代理，让后端在缓存 miss 时重搜新直链

// 3) 兜底与占位
getAttractionImage(name)   // 未加载时返回深底 SVG dataURL 占位图（#1a262f + 白字景点名）
handleImageError(event)    // 把 img.src 换成"加载失败"占位图，防止死循环
```

---

## 9. 导出 PNG（三段式）

```ts
exportAsImage():
  1) mapDataUrl = await captureMapScreenshot()
       - 容器不存在或 clientHeight === 0 → 返回 ''（导出不含地图，不报错）
       - 若 .right-map 被 v-show 隐藏 → 临时 display:block + 移到 left:-9999px，等 300ms 渲染
       - html2canvas(mapEl, { backgroundColor:'#1a1a2e', scale:2, useCORS:true, allowTaint:true,
           ignoreElements: el => /gmnoprint|amap-controls/.test(el.className) })  // 地图控件易渲染成白块
       - 还原隐藏状态 → toDataURL('image/png')
  2) exportContainer.innerHTML = buildExportHTML(mapDataUrl)
     绝对定位挪到 -9999px 并 append 到 body
  3) await 所有 <img> 的 onload/onerror（二维码、景点图），避免截到空白
  4) html2canvas(exportContainer, { backgroundColor:'#f0f2f5', scale:2, useCORS:true, allowTaint:true })
  5) removeChild → a[download=`${prefix}_${city}_${timestamp}.png`].click()
     message.loading/success/error 复用同一个 key:'export'
```

`buildExportHTML(mapDataUrl)` 是一套**独立浅色 HTML 模板**（宽 800px，与页面深色主题无关）：

| 区块 | 内容 |
|---|---|
| 标题 | `result.export.title`（城市）+ `subtitle`（日期区间/天数）+ `overall_suggestions` |
| 预算 | 四张子预算小卡 + 高亮总预算条 |
| 地图 | 仅当 `mapDataUrl` 非空 |
| 每日 | 每天一张白卡；景点 48% 宽双列（`object-fit:contain`，max-height 400px）；餐饮小标签 |
| 酒店 | `trip.hotel_recommendations`（历史字段，可能不存在）→ 蓝底列表 |
| 天气 | 深色卡（`#2b2d3c`）逐天：日期 / 白天 / 夜间 / 风向风力 |
| 页脚 | `api.qrserver.com` 生成 120px 二维码指向 `github.com/1sdv/TripStar` + 标语 |

> 为什么不直接截当前页面？页面是深色玻璃拟态且 `v-show` 只显示一节，截图会缺内容；
> 重新拼一份打印友好的 HTML 才能一次性导出全部信息，并且不依赖主题。

---

## 10. 样式系统

### 10.1 视觉基调（scoped 2977–4605）

| 元素 | 值 |
|---|---|
| 页面背景 | `linear-gradient(180deg,#0d171d 0%,#142430 58%,#0f1a22 100%)`（`.result-container`） |
| 遮罩 | `.lower-shade`：`position:fixed;inset:0`，`rgba(6,14,20,.72)`，顶部 28px 渐变过渡，`z-index:0`，`pointer-events:none` |
| 玻璃卡 | `.content-wrapper`：`background:rgba(12,23,32,.56)`；`backdrop-filter:blur(18px)`；`border:1.2px solid rgba(236,243,250,.2)`；`border-radius:22px`；`box-shadow:0 24px 80px rgba(4,11,18,.52)`；`padding:20px` |
| 文字 | 主 `#ecf3fa`；次 `rgba(228,236,245,.72)`；强调 `#ffe3d6` |
| 强调色 | 橙 `#d76e42`（菜单选中下划线、hover、KG 邻接高亮、按钮描边）；主按钮底色 `rgba(215,110,66,.24)` |
| 按钮 | `border-radius:999px`；默认态 `1.2px solid rgba(236,243,250,.24)` + `rgba(12,23,32,.56)`；高 34px；`font-size:12px`；`letter-spacing:.04em` |
| 分节卡片 | `.section-shellless`（去掉 Ant 卡片边框与内边距，只留玻璃底） |
| 天气卡 | `.weather-side` 背景取 `var(--weather-gradient)`（见 4.5），`.weather-gradient` 叠纹理层 |
| 动画 | `fadeInDown`（-20px→0）、`fadeInUp`（20px→0）+ 5 个 `weather-*`；global.css 另有 `heathing` / `cloudLoop` / `bounceInDown` |
| 响应式 | 唯一断点 `@media (max-width:768px)`：整体纵向堆叠、菜单横向滚动并隐藏滚动条、天气卡竖排（温度 46px）、预算明细 `min-width:620px` 横向可滚 |

### 10.2 全局样式（无 scoped，4607–4706）

只服务**地图标记与气泡**，因为这些 DOM 由高德库插入容器内，不受 scoped 作用域约束：

| 选择器 | 作用 |
|---|---|
| `:root` | `--tripstar-map-accent:#d76e42`、`--tripstar-map-accent-strong:#a14625`、`--tripstar-map-surface:rgba(17,29,38,.96)`、`--tripstar-map-border:rgba(215,110,66,.35)`、`--tripstar-map-text-main:#f6fbff`、`--tripstar-map-text-sub:rgba(240,246,252,.72)` |
| `.tripstar-map-marker` | 34×34 容器；`.__core` 20×20 星形 SVG；`.__index` 绝对定位在下方，15px 白色粗体 + `text-shadow` |
| `.tripstar-map-tooltip` | 透明无边框；`max-width:min(320px, calc(100vw - 40px))`；`pointer-events:none` |
| `.__line` / `.__line--title` | 12px `#ffd6c7`、nowrap；标题 15px 白色 700 |
| `#amap-container .amap-info-content` | `background:transparent;border:none;box-shadow:none;padding:0`（`!important`） |
| `#amap-container .amap-info-sharp` | `display:none`（去掉小尖角） |

---

## 11. 依赖的 i18n 键（`result.*` 命名空间）

`side.{overview,budget,map,days,graph,weather}`、`refreshMap`、`editTrip`、`saveChanges`、`cancelEdit`、`exportImage`、
`dateRange`、`noTripPlan`、`noTripPlanDesc`、`backCreateTrip`、`imageLoadFailed`、`minuteUnit`、`interCityTransport`、
`transferDay`、`transferInfo`、`dayDescription`、`dayTransport`、`dayAccommodation`、
`attractionTitle`、`hotelTitle`、`mealsTitle`、`meals.{breakfast,lunch,dinner,snack}`、
`field{Address,VisitDuration,VisitDurationMinutes,Description,Rating,Type,PriceRange,Distance}`、
`weatherDay`、`weatherNight`、`weatherPrecipitation`、`weatherHumidity`、`weatherWind`、`mapInfo.dayAttraction`、
`budget.{title,total,filterLabel,filterAll,attraction,hotel,meal,transport,sortLabel,sortAmountDesc,sortAmountAsc,sortDayAsc,sortDayDesc,detailType,detailDay,detailName,detailAmount,detailAction,editPrice,noDetails,editPrompt,editConfirm,pendingTitle,pendingEmpty,restore}`、
`graph.{type,detail,relation,categories.{city,schedule,attraction,hotel,meal,weather,budget,suggestion}}`、
`export.{title,subtitle,weatherTitle,dayTitle,mealTitle,durationLine,daytime,nighttime,noMealRecommendation,hotelFallback,perNight,footer,filePrefix}`、
`messages.{mapLoaded,mapLoadFailed,enterEditMode,changesSaved,editCanceled,keepOneAttraction,attractionDeleted,generatingImage,imageSuccess,imageFailed,budgetInvalidAmount,budgetAmountUpdated,budgetItemDeleted,budgetItemRestored}`、
`chat.*`（AIChat 组件）。通用键在 `common.*`：`dayNumber`、`noData`、`delete`、`loading`。
三种语言文件必须键对齐，缺键会回退 zh 或原样显示键名。

---

## 12. 复刻检查清单

- [ ] `activeSection` 分节 + `v-show`；菜单项按数据条件显隐。
- [ ] `applyTripPlanPayload()` 作为唯一数据入口，写全 `sessionStorage` 三个键（tripPlan/graphData/planId）。
- [ ] 直接访问 `?plan_id=` 或刷新后，能经 `/api/trip/status/{id}` 回补数据。
- [ ] 概览 Swiper 在 `nextTick` 后初始化，分节切换与数据变更时重建。
- [ ] 天气：6 种图标 + 天气渐变 + 三项展示值 + 日期本地化，缺数据一律回退 `'--'`。
- [ ] 预算：明细从行程反算；编辑/删除/恢复后总额自洽（`recalculateBudgetTotals`）。
- [ ] KG：分类归一化后可吃三语输出；根节点居中；`links` 用字符串 id；resize 时重建。
- [ ] 地图：`AMapLoader.load` 2.0 + `preserveDrawingBuffer:true`；气泡样式写在无 scoped 的 style 中。
- [ ] 图片：一律走 `/api/poi/image`，占位图兜底，`onerror` 不产生请求循环。
- [ ] 导出：地图单独截图 + 独立 HTML + `html2canvas(scale:2)`，`<img>` 先等加载完成。
- [ ] `onUnmounted` 清理 Swiper / 地图 / ECharts / resize 监听。