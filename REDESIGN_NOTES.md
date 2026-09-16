# Landing 重设计 · Star Almanac（星图领航）

本分支只重写了 **`frontend/src/views/Landing.vue`** 的 UI，未改动任何功能逻辑、后端、路由或 i18n 词条。

## 设计方向

在保留原模板「编辑部 / 旅行手账」骨架的基础上，落到 TripStar 自己的概念上：

- **Star Almanac / 星图领航**：呼应 "TripStar" 之名——每个目的地是一颗星，AI 智能体把它们连成一条星座航线；规划过程即「点亮星座」。
- **日 / 夜双色**：暖羊皮纸的白日手账 × 深青夜空星图，取代原来的单色深青雾气 hero。强调色用 **陶土橙 + 墨青(ink-teal)** 双色。
- **字体**：`Newsreader`（编辑年鉴衬线）+ 项目现有 `Outfit`（正文）+ `IBM Plex Mono`（星表编号感）。

## 功能保持不变（逐项核对）

- `handleSubmit` 全流程一字未改：校验 → 组装 `TripFormData` → `generateTripPlan` 的 `onTaskCreated / onTaskEvent` 回调 → `sessionStorage` 写入 → 跳转 `/result`。
- 表单仍使用 Ant Design 组件：`a-date-picker` 依旧返回 `Dayjs`，`handleSubmit` 依赖的 `.format('YYYY-MM-DD')` 照常工作。
- 多城市增删、兴趣多选、历史记录列表、加载进度阶段阈值（30 / 50 / 70 / 100）与原实现完全一致。
- `NavBar` 仍作为原组件引入，设置弹窗 / 语言切换 / CTA 功能完整保留，仅通过 `:deep()` 换肤。
- 文案全部复用已有 i18n key（`home.heroBadge` / `home.titleLine` / `home.nav.cta` 等），中 / 英 / 日三语均已存在。

## 只改了外观

- 移除纯装饰的雾气 / 视差 `computed` 与 `onScroll` 监听，以及 creative-tim demo 外链图片（`antoine-barres.jpg` / `clouds.png`）。
- hero 右侧改为纯 CSS/SVG 的夜空星图（无外部图片）。
- 加载动画由竖排 stepper 改为「星座连线随进度点亮」。
- 用 `:deep()` 为 Antd 控件与 NavBar 换肤，未触碰它们的脚本。

## 本地验证清单

```bash
cd frontend
npm install
npm run dev      # 首页星图与表单正常、NavBar 变暖色
# 填城市 + 日期提交 → 星座 stepper 随进度点亮 → 跳转 /result
npm run build    # 会跑 vue-tsc，应无类型错误
```

## 已知小项（本次未处理，供后续）

- Antd 的下拉 / 日期浮层是 teleport 到 `body` 的，`:deep()` 够不到：关着的输入框已换肤，展开的浮层仍是 Antd 默认样式。要统一需在 `styles/global.css` 加一小段全局样式。
- `components/NavBar.vue` 中 GitHub 链接指向 `github.com/1sdv/TripStar`，与实际仓库不符，建议单独修正。
- 下一步计划：将 4699 行的 `Result.vue` 按 `useMap` / `useKnowledgeGraph` / `useBudget` 抽成 composables（保持功能不变）。
