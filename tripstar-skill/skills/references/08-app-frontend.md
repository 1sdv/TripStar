# 08 · 前端骨架（路由 / API 层 / i18n / 设计系统 / Landing / 组件）

## 1. 启动与路由（`main.ts`，34 行）

```ts
createApp(App).use(router).use(Antd).use(i18n).mount('#app')
router = createRouter({ history: createWebHistory(), routes: [
  { path: '/',       name: 'Landing', component: () => import('./views/Landing.vue') },
  { path: '/result', name: 'Result',  component: () => import('./views/Result.vue') },
]})
```

- 两条路由都**懒加载**：首页不为 echarts / html2canvas / swiper / 地图 SDK 付首屏成本。
- `Result.vue` 通过 `route.query.plan_id` + `sessionStorage` 取数据，详情见 07。
- **`views/Home.vue` 是遗留页面**：`main.ts` 未注册、全项目也没有任何 `import … Home.vue`，可忽略或删除。
- 全局样式只 import 两处：`ant-design-vue/dist/reset.css` 与 `./styles/global.css`。

### `vite.config.ts` 关键点

| 配置 | 作用 |
|---|---|
| `server.port = 5173`、`proxy['/api'].target = http://localhost:8000` | 开发期同源代理 |
| `resolve.alias['@'] = src` | 全项目 `@/components/...` |
| 插件 `tripstar-inject-amap-security-code` | 构建/启动时把 `VITE_AMAP_SECURITY_JS_CODE` 注入 `index.html` 的 `__AMAP_SECURITY_JS_CODE__`（避免 Vite 对 `%ENV%` 的内置扫描告警） |
| `build.rollupOptions.output.manualChunks` | 把 `echarts/zrender`→`echarts`、`html2canvas`、`swiper`、`amap-jsapi-loader/@googlemaps`→`maps` 拆包 |

## 2. API 层（`src/services/api.ts`，456 行）

### 2.1 baseURL 解析

```ts
ENV_API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
resolveDefaultApiBaseUrl(): env → window.location.origin（同源部署）→ 'http://localhost:8000'
getRuntimeApiBaseUrl():  localStorage['tripstar.runtime.api_base_url'] || 默认
setRuntimeApiBaseUrl(v)   // 尾斜杠会被去掉
```

axios 实例：`timeout: 0`（等长任务）、`Content-Type: application/json`；
**请求拦截器里每次设置 `config.baseURL = getRuntimeApiBaseUrl()`**（支持运行期改后端地址，无需刷新）。

### 2.2 运行时配置键（localStorage）

| 键 | 用途 |
|---|---|
| `tripstar.runtime.api_base_url` | 后端地址 |
| `tripstar.runtime.amap_web_js_key` | 高德 JS API Key（地图组件直接用） |
| `tripstar.runtime.google_maps_api_key` | ★ 范围外（前端的 Google 分支会读它，复刻时删掉） |
| `tripstar.user_id` | 匿名用户 ID（记忆模块用） |

`RUNTIME_SETTINGS_UPDATED_EVENT = 'tripstar:runtime-settings-updated'`：`saveRuntimeSettings()` 成功后
`window.dispatchEvent(new CustomEvent(...))`，`Result.vue` 监听它来重建地图。

### 2.3 导出函数

| 函数 | 端点 | 备注 |
|---|---|---|
| `submitTripPlan(form)` | `POST /api/trip/plan` | 自动注入 `user_id`；返回 `{task_id, plan_id, ws_url}` |
| `pollTaskStatus(id)` | `GET /api/trip/status/{id}` | 结果页回补用 |
| `getTripHistory(limit=8)` | `GET /api/trip/history` | Landing 历史列表 |
| `generateTripPlan(form, {onTaskCreated, onTaskEvent})` | 提交 + WS | 内部 `subscribeTripTask()` |
| `resumeTripPlan(taskId, opts)` | `GET status` → 必要时重连 WS `/api/trip/ws/{id}` | 断线/刷新恢复 |
| `healthCheck()` | `GET /health` | — |
| `getBackendRuntimeSettings()` / `updateBackendRuntimeSettings()` | `GET/PUT /api/settings` | 密钥掩码回传 |
| `getRuntimeSettings()` / `saveRuntimeSettings()` | 组合上面 + localStorage | 保存后触发事件 |
| `getRuntimeMapJsKey()` / `setRuntimeMapJsKey()` | localStorage | 高德 JS Key |
| `getOrCreateUserId()` | localStorage | `crypto.randomUUID()` |
| `listUserMemory()` / `addExplicitMemory()` / `deleteMemoryItem()` / `clearUserMemory()` | `/api/memory/*` | 设置页管理偏好 |

### 2.4 WebSocket 订阅

```ts
subscribeTripTask(wsUrl, options): Promise<TripPlanResponse>
  socket.onmessage → JSON.parse → options.onTaskEvent(event)
      status==='completed' → 用 event.result resolve（无 result 则 reject）
      status==='failed'    → reject(event.error || event.message)
  onerror / onclose(未 settle) → reject
  // settled 后 socket.close()；ws_url 为相对路径时拼 ws(s)://<apiBase>
```

## 3. 类型契约

见 `09-contracts.md`（`src/types/index.ts` 全量字段 + 与 Pydantic 的差异）。

## 4. i18n

- `i18n/messages.ts`：`SUPPORTED_LOCALES = ['zh-CN','ja-JP','en-US']`、`DEFAULT_LOCALE='zh-CN'`、`messages` 组装三份 JSON。
- `i18n/index.ts`：`createI18n({ legacy:false, locale: 初始值, fallbackLocale:'zh-CN', globalInjection:true, messages })`；
  初始语言 = `localStorage['tripstar-locale']` → 浏览器 `navigator.language` → 默认；`setAppLocale()` 同步 `<html lang>`。
- 顶层命名空间：`app`、`common`、`api`、`settings`、`home`、`result`（`Result.vue` 的键清单见 07 第 11 节）。
- 后端也吃语言：`TripFormData.language = getCurrentLocale()`，影响 LLM 输出语言与知识图谱分类名。

## 5. 设计系统（`src/styles/global.css`，7429 行）

- 来源是 Paper Kit 2 风格的模板样式（按钮 `.btn.btn-danger.btn-round`、`.demo-icons`、`.media-post`、`.lightbox` 等），
  加上项目自己的动画（`@keyframes heathing` L214、`cloudLoop` L6947、`bounceInDown` L8017、`nc-icon-spin` L8430）与 `body` 基础样式（L269）。
- 页面级视觉（深色玻璃拟态、橙色强调）**不在 global.css**，而在各视图的 `<style scoped>` 里（`Result.vue`、`Landing.vue`）。
- 复刻建议：若要最小化，只保留 `body` 基础 + 按钮/表单类 + 需要的 keyframes；其余模板类可裁掉。
- 字体：组件会 import Google Fonts（`Nunito Sans`、`Raleway`，见 `OverviewAttractionCard.vue`），离线环境需替换为系统字体栈。

## 6. Landing 页（`views/Landing.vue`，1337 行）

### 6.1 表单

`reactive<LandingFormData>`：`{ cities: [{city:'', days:2}], start_date: Dayjs|null, transportation:'公共交通', accommodation:'经济型酒店', preferences: [], free_text_input: '' }`

- 城市可增删（`addCity`/`removeCity`，最多 5 个，至少 1 个）；`totalDays = Σ days`；`computedEndDate = start + totalDays-1`。
- 偏好来自 `interestOptions`：历史文化/自然风光/美食/购物/艺术/休闲（`togglePreference`）。
- 校验：至少一个城市名非空、必须选开始日期、总天数 ≤ 30。

### 6.2 提交与进度

```ts
handleSubmit():
  清空 sessionStorage 的 tripPlan/graphData/planId
  组装 TripFormData（city=第一个城市，cities[]，start/end，travel_days=totalDays，language=getCurrentLocale()）
  await generateTripPlan(form, {
    onTaskCreated: t => planCode = t.plan_id || t.task_id,
    onTaskEvent:  e => { planCode = e.plan_id; loadingProgress = clamp(e.progress,0,100); loadingStatus = e.message || getStageStatusText(e.stage) }
  })
  成功 → 写 sessionStorage（tripPlan / graphData / planId）→ 500ms 后 router.push('/result?plan_id=…')
  失败 → 清缓存 + message.error
```

### 6.3 进度 stepper（模板 187–245）

四段式节点，按 `loadingProgress` 阈值切换 active/completed：

| 阈值 | 节点 | 文案键 |
|---|---|---|
| 0–30 | 景点搜索 | `home.loading.searchingAttractions` / `searchedAttractions` |
| 30–50 | 天气查询 | `queryingWeather` / `queriedWeather` |
| 50–70 | 酒店推荐 | `recommendingHotels` / `recommendedHotels` |
| 70–100 | 行程生成 | `generatingPlan` / `done` |

`getStageStatusText(stage)` 把后端 stage 映射成文案（submitted/initializing→initializing，attraction_search→searchingAttractions，
weather_search→queryingWeather，hotel_search→recommendingHotels，planning/graph_building→generatingPlan，completed→done）。
视觉：`spinner-small` 旋转点 + `step-divider` 进度条 + 顶部大字号 `stepper-title`（`planCode`）。

### 6.4 历史与滚动效果

- `loadHistoryPlans()` → `getTripHistory(8)`；点击 `openHistoryPlan(planId)`：清 tripPlan/graphData，
  只留 `planId`，然后 `router.push({path:'/result', query:{plan_id}})`（由结果页回源后端）。
- 滚动视差：`heroProgress`/`toneProgress` 计算样式（背景位移、雾层透明度 `fogEnabled`、表单淡入 `formRevealStyle`），
  配合 global.css 的云层与雾气动画。这是纯装饰，复刻时可去掉。

## 7. 组件

| 组件 | props | emits | 职责 |
|---|---|---|---|
| `NavBar.vue`（545 行） | 无 | `brand-click`、`cta-click` | 品牌/导航/语言切换 + 设置弹窗（读写 `/api/settings`、调用 `saveRuntimeSettings`、偏好记忆管理） |
| `AIChat.vue`（1160 行） | `tripPlan: TripPlan \| null` | — | 右下角问答浮层：`POST /api/chat/ask`，含 3 个快速问题（价格/适合人群/餐饮），空计划时禁用输入 |
| `OverviewAttractionCard.vue`（217 行） | `item: OverviewAttractionItem`、`imageSrc: string`、`active: boolean` | `hover`、`select-day`、`image-error` | 概览 Swiper 单卡：图片、名称、地址、时长、门票、`show more` |

`NavBar` 的设置弹窗字段与 `BackendRuntimeSettings` 一一对应（含 `api_base_url` 与 `vite_amap_web_js_key`），
保存后把高德 JS Key 写入 localStorage 并派发刷新事件——**地图无需刷新页面即可换 Key**。

## 8. 前端约定与坑

1. `getRuntimeApiBaseUrl()` 在每次请求时求值，不要把它缓存到模块常量后再读（会拿不到运行期修改）。
2. 结果页的图片 URL 一律拼 `getRuntimeApiBaseUrl()`，不要写死 `/api`（同源部署时 `origin` 已含前缀）。
3. 三语 JSON 必须键对齐，缺失键会回退 zh；`messages` 里**不要**用同名 key 覆盖不同语义。
4. `sessionStorage` 只存 3 个键，`localStorage` 存配置与用户 ID，两者不要混用。
5. 遗留 `Home.vue` 与 `OverviewAttractionCard` 里的 Google Fonts import 是复刻时需要清理的两处。