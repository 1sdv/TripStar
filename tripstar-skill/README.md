# TripStar 复刻指南（PI-Desktop 插件 / skill-pack）

把 TripStar（HelloAgents 多智能体智能旅行规划）这个项目**完整沉淀成一份可运行的 skill**：
后端任务链路、小红书取数、高德地图、知识图谱构建，以及**重点**——结果展示页的前端实现规范。
范围明确排除 Google Maps 相关服务（`google_map_service.py` 与 `Result.vue` 的 Google 分支）。

## 结构

```
tripstar-skill/
├─ manifest.json                       插件清单（contributes.skills 指向主文档）
├─ main.js                             入口（本插件无运行时逻辑）
├─ README.md                           本文件
├─ skills/
│  ├─ tripstar-trip-planner.md         ★ 主 skill：会被注入系统提示，含速查与索引
│  └─ references/
│     ├─ 01-architecture.md            架构、目录职责、端到端时序、失败降级
│     ├─ 02-backend-api.md             全部 HTTP/WS 端点、任务状态机、持久化 JSON
│     ├─ 03-services.md                小红书签名与两级缓存、高德 MCP、LLM 客户端
│     ├─ 04-agents.md                  多智能体提示词、工具调用协议、JSON 修复流水线
│     ├─ 05-memory.md                  偏好记忆：衰减/合并/TOP-K/SQLite
│     ├─ 06-knowledge-graph.md         图谱构建八步规则与已知坑
│     ├─ 07-result-frontend.md         ★★ 结果展示页逐段实现规范（12 章，最详细）
│     ├─ 08-app-frontend.md            路由/API 层/i18n/设计系统/Landing/组件
│     ├─ 09-contracts.md               Pydantic ↔ TypeScript 全字段对照
│     ├─ 10-runbook.md                 运行、配置、验证、排障、最小子集
│     ├─ 11-local-run-verified.md      ★ 本机实测：conda/GBK 坑、CORS、地图修复、28 项验收
│     └─ 12-credentials-setup.md       ★★ 首次运行：高德 Key / 安全密钥 / 小红书 Cookie / 模型怎么拿
├─ scripts/
│  ├─ check-credentials.ps1            ★ 凭据体检（静态 + 在线探测，PASS/WARN/FAIL）
│  ├─ start-backend.ps1                起后端（自动建 venv + 装依赖）
│  ├─ start-frontend.ps1               起前端 / 构建 / 预览
│  ├─ verify.ps1                       冒烟验证（后端接口 + 可选前端构建）
│  └─ ui-assert.js                     ★ 结果页 UI 断言（浏览器控制台/自动化注入）
└─ assets/
   └─ sample-result.json              真实 TripPlanResponse（西安 3 日，33 节点 / 37 边）
```

## 安装为 PI-Desktop 插件

1. 把整个 `tripstar-skill/` 目录放入 PI-Desktop 插件目录（或按平台方式导入本目录）：
   `%USERPROFILE%\.pi-desktop\plugins\installed\tripstar.guide\`
2. 在 PI-Desktop 中启用 "TripStar 复刻指南"。
3. 启用后 `skills/tripstar-trip-planner.md` 会作为 skill 注入系统提示；
   需要细节时按主文档的索引去读 `references/*.md`。

也可以当作纯文档包使用：不安装，直接把 `skills/` 目录作为知识文档阅读。

## 使用方式

- **第 0 步（别跳过）：备齐并体检凭据** —— 高德两个 Key + 安全密钥、小红书 Cookie、模型 Key。
  `pwsh scripts/check-credentials.ps1 -Online`，逐项 PASS/WARN/FAIL 并给出修复方向；
  获取步骤见 `skills/references/12-credentials-setup.md`
- 想跑起来：`pwsh scripts/start-backend.ps1` + `pwsh scripts/start-frontend.ps1`
  （本机 conda 环境要加 `-S` + `PYTHONPATH`，见 `references/11-local-run-verified.md` §2）
- 想验证环境：`pwsh scripts/verify.ps1`（加 `-BuildFrontend` 会跑 `vue-tsc && vite build`）
- 想验证**结果页真的能展示**：打开 `/result?plan_id=<task_id>`，把 `scripts/ui-assert.js` 粘进控制台，
  期望 `28 pass / 0 fail`（实测基线见 11 §7）
- 想离线看结果页：按 `skills/references/10-runbook.md` 第 6 节，把 `assets/sample-result.json`
  写进 `sessionStorage` 后访问 `/result?plan_id=…`（无需后端与任何 Key）。
  ⚠️ 它是**仓库内的历史样例**，只用于界面验证，**不是**新生成的行程——不要拿它冒充生成结果。
- 想复刻展示页：直接照 `07-result-frontend.md` 的 12 章清单逐块实现

## 哪些文件该提交（push 前看这里）

`tripstar-skill/` 里**没有密钥**，全部可以提交；真正的密钥在两个 `.env` 与 `backend/runtime_settings.json`，
而这三者都已被根 `.gitignore` 忽略（`.env`、`.env.*`、`backend/runtime_settings.json`、
`backend/data/trip_tasks`、`backend/data/photo_cache`）。push 前自查一遍：

```powershell
git status --short tripstar-skill        # 应该只看到 docs/scripts/assets
git check-ignore -v backend/.env backend/runtime_settings.json backend/data/trip_tasks
```

| 文件 | 建议 | 说明 |
|---|---|---|
| `manifest.json` / `main.js` / `README.md` | 提交 | 插件外壳 |
| `skills/tripstar-trip-planner.md` | 提交 | 主 skill（占位符 `<PY>`/`<PY_ENV>`，无本机路径） |
| `references/01–10`、`12` | 提交 | 通用文档；12 里示例输出已脱敏 |
| `references/11-local-run-verified.md` | 提交（已脱敏）或按需忽略 | 内容是"本地实测发现+28 项验收"，已把解释器/站点路径改成占位符；若不想公开个人工作记录，把下面一行加进 `.gitignore` |
| `scripts/*.ps1` / `ui-assert.js` | 提交 | 都是通用工具，无硬编码路径 |
| `assets/sample-result.json` | 提交 | 演示用计划数据（不含任何凭据）；如果不想公开真实行程内容，可换成虚构城市 |

```gitignore
# 可选：不公开个人本地实测记录
tripstar-skill/skills/references/11-local-run-verified.md
```

> 另外：如果你在网页「设置」里填过 Key，`backend/runtime_settings.json` 会含**真实密钥**——
> 它已被忽略，但**不要**用 `git add -f` 强加。

## 两个必须知道的坑（实测）

1. **结果页用 `localhost:5173` 打开，不要用 `127.0.0.1`** —— 后端 `CORS_ORIGINS` 只放行 localhost，
   否则 `GET /api/trip/status/{id}` 报 `Network Error`，页面停在空状态。
2. **地图容器必须有确定高度** —— `.map-card` 原用 `height:100%` + `min-height:500px`，百分比高度穿不过
   `min-height`，容器实际高度 0 时 AMap 会抛 `Invalid Object: Pixel(NaN, NaN)`，**景点标记全部丢失**。
   本仓库已改为 `height: 500px`（`frontend/src/views/Result.vue`），复刻时务必照做。

## 脚本说明

所有脚本都会**从自身位置向上查找仓库根**（判定依据：存在 `backend/app/api/main.py`），
也可显式传 `-RepoRoot`。因此插件目录不必与项目目录同级。

```powershell
pwsh scripts/start-backend.ps1 -Port 8000
pwsh scripts/start-frontend.ps1 -Mode build
pwsh scripts/verify.ps1 -BaseUrl http://127.0.0.1:8000 -BuildFrontend
```

## 范围声明

| 在范围内 | 不在范围内（Google Maps） |
|---|---|
| `amap_service.py`（高德 MCP）、`map_dispatcher.py`、高德地理编码限速 | `google_map_service.py` |
| `Result.vue` 的高德分支（Markers / InfoWindow / Polyline / 路线降级） | `initGoogleMap`、`addGoogleAttractionMarkers`、`drawGoogleRoutes`、`google*` 状态 |
| 知识图谱构建与 ECharts 渲染 | Google Weather API 相关分支与 `_fallback_amap_weather` 的触发条件 |

`map_dispatcher.get_map_provider()` 的开关仍保留说明：`google_maps_api_key` 为空即走高德分支，
复刻时把 provider 固定为 `amap` 即可。

## 版本

- 依据项目快照：`frontend/src/views/Result.vue` 4706 行、`backend/app/agents/trip_planner_agent.py` 1134 行、
  `backend/app/services/xhs_service.py` 759 行（文档中的行号均以此为准）。
- 插件版本 1.0.0。