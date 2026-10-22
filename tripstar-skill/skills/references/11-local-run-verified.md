# 11 · 本机实测运行与结果页验收（已验证）

本文件记录**在真实环境里跑通**的命令、踩到的坑和验收结论，优先级高于 `10-runbook.md` 的通用步骤。
所有结论都来自实测（2026-02，Windows 10 + Node 22.16 + conda py311）。

> 为便于公开分享，文档里的解释器路径统一用占位符：`<PY>` = 你的 `python.exe` 全路径，
> `<PY_ENV>` = 该环境的根目录（其下有 `Lib\site-packages`）。替换成你自己的即可。

---

## 1. 实测环境事实

| 项 | 值 |
|---|---|
| Python 解释器 | 一个 conda 环境（本例 3.11.13）：记作 `<PY>`（如 `D:\conda\envs\py311\python.exe`） |
| site-packages | 记作 `<PY_ENV>\Lib\site-packages` |
| 依赖状态 | fastapi 0.141.1 / uvicorn 0.54.0 / pydantic 2.14.1 / hello_agents 0.2.8 / httpx 0.28.1 / openai 2.54.0 / aiosqlite 0.22.1 **均已安装** |
| 缺失/冲突 | `fastmcp` 导入失败（见 §3），但 `hello_agents.tools.MCPTool` 可正常导入 |
| 后端配置 | `backend/.env`（LLM 走火山方舟 ark、`XHS_COOKIE` 已配、`VITE_AMAP_WEB_KEY` 已配、**`GOOGLE_MAPS_API_KEY` 已配**） |
| 前端配置 | `frontend/.env`（`VITE_API_BASE_URL=http://localhost:8000`、`VITE_AMAP_WEB_JS_KEY`、`VITE_AMAP_SECURITY_JS_CODE`） |
| 端口 | 后端 8000、前端 5173 |

> ⚠️ 这份 `.env` 里 **Google Maps Key 是配置了的**，所以 `get_map_provider()` 返回 `"google"`，
> 前端 `initMap()` 也会先尝试 Google Maps JS。本 skill 的范围是"排除 Google"，见 §5 的建议。

---

## 2. 致命坑①：conda 环境启动即崩（`site` 模块 GBK 解码失败）

### 现象

直接运行会立刻崩溃，连 `--version` 都过不去：

```
Fatal Python error: init_import_site: Failed to import the site module
...
File "<frozen site>", line 188, in addpackage
UnicodeDecodeError: 'gbk' codec can't decode byte 0x94 in position 6: illegal multibyte sequence
```

### 根因

该环境里有 **editable 安装的 `.pth` 文件，内容含中文路径**（如 `E:\0研0\...`）。这些 `.pth` 以 UTF-8 保存，
而 `site.addpackage()` 用系统 locale（中文 Windows = GBK）解码，第 7 个字节 `0x94` 正好是「研」的 UTF-8 尾字节 → 崩溃。

`PYTHONUTF8=1` / `chcp 65001` **都无效**（`site` 在 UTF-8 模式生效前就用 locale 读了 `.pth`）。

### 解法（推荐 `-S` + `PYTHONPATH`）

```powershell
$env:PYTHONPATH = "<PY_ENV>\Lib\site-packages"
& "<PY>" -S -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

`-S` 跳过 `site` 初始化（不再读 `.pth`），`PYTHONPATH` 补回 site-packages。实测依赖全部可导入、服务正常。

> 副作用：`.pth` 里的 `google.*` 命名空间包不会注册。本项目的 amap/xhs/LLM 链路不依赖它，无影响
> （但 `import google.generativeai` 之类会失败）。

### 定位坏文件的诊断命令

```powershell
$sp = "<PY_ENV>\Lib\site-packages"
Get-ChildItem $sp -Filter *.pth | ForEach-Object {
  $t = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
  if ($t -match '[^\x00-\x7F]') { "含非 ASCII（可能是元凶）: $($_.Name)" }
}
```

彻底修复（任选）：把那些 editable `.pth` 的目标目录改成纯 ASCII 路径，或删除不用的 editable 安装。

---

## 3. 坑②：`fastmcp` 与 pydantic 2.14 不兼容

```
ImportError: cannot import name 'eval_type_backport' from 'pydantic._internal._typing_extra'
```

`fastmcp`（依赖 bundled `mcp`）调用了 pydantic 2.14 已移除的内部符号。
**影响面**：`hello_agents.tools.MCPTool` 本身能导入，实测规划链路可跑；若后续用到 `fastmcp` 协议端点才需要处理。
**备选修法**：`pip install "pydantic<2.12"` 或升级 `mcp/fastmcp`。不要为此降级整体环境而不做回归。

---

## 4. 实测启动命令

### 后端（本机可用）

```powershell
cd <repo>\backend
$env:PYTHONPATH = "<PY_ENV>\Lib\site-packages"
$env:PYTHONUTF8 = "1"
& "<PY>" -S -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

启动日志应包含：`📦 已加载 N 个持久化旅行任务`、6 项配置状态（高德 Key/Google Key/小红书 Cookie/LLM 均显示"已配置"）、`✅ 配置验证通过`。

### 前端

```powershell
cd <repo>\frontend
npm run dev -- --port 5173 --host 127.0.0.1
```

> 若在自动化/沙箱里启动（进程会被父 shell 回收），可用 WMI 创建脱离进程：
> `Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="cmd /c cd /d <dir> && ... > log 2>&1"}`

### 打开结果页

```
http://localhost:5173/result?plan_id=<历史任务ID>
```

`backend/data/trip_tasks/*.json` 里任一 `status=completed` 的 `task_id` 都行（本机实测用 `6c83aff5`，西安 3 日）。
结果页会 `GET /api/trip/status/{id}` 回补数据并写 sessionStorage。

---

## 5. 坑③：CORS 只允许 localhost，用 127.0.0.1 打开会全站 Network Error

实测：以 `http://127.0.0.1:5173` 打开结果页 → 控制台：

```
发送请求: GET /api/trip/status/6c83aff5
响应错误: undefined Network Error
结果页从后端回补旅行计划失败: Error: Network Error
```

页面停在空状态（`.empty-state-panel`）。原因：`backend/.env` 的
`CORS_ORIGINS=http://localhost:5173,http://localhost:3000` **不含 127.0.0.1 变体**，
而前端 `VITE_API_BASE_URL=http://localhost:8000`，跨源被拦。

**修法（任选）**：
- 用 `http://localhost:5173` 打开（最简单，实测通过）；
- 或把 `CORS_ORIGINS` 补全为
  `http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000`。
- 后端默认值本来就包含 127.0.0.1 变体，是本机 `.env` 覆盖掉了。

---

## 6. 坑④（已修）：地图只剩底图、景点标记全丢 —— 容器高度 0

### 现象

进入「景点地图」分节后：底图能出来，但**没有任何景点标记**；控制台报

```
Google Maps 加载失败，即将降级到高德地图: Error: Google Maps 加载超时...
地图加载失败: Error: Invalid Object: Pixel(NaN, NaN)
  at addAttractionMarkers (src/views/Result.vue:1883)
```

### 根因

`#amap-container` 的 inline 样式是 `width:100%;height:100%`，而它的父级 `.ant-card-body`
也只有 `height:100%`，再往上的 `.map-card` 原本写的是 **`height:100%` + `min-height:500px`**。
CSS 规则：**百分比高度无法从 `min-height` 解析** → `.ant-card-body` 高度变 auto → 容器实际高度 **0**。
实测容器宽度 610px、**高度恒为 0px**。AMap 2.0 在 0 高度容器上执行 `map.add(overlays)` 时
`lngLatToContainer()` 返回 NaN → 抛 `Invalid Object: Pixel(NaN, NaN)` → 整批 marker 加不进去。

### 修复（已应用到 `frontend/src/views/Result.vue`）

```css
.map-card {
  height: 500px;      /* 原来是 height: 100%，改为确定高度 */
  min-height: 500px;
  overflow: hidden;
}
```

### 验证

| 状态 | 容器尺寸 | `.tripstar-map-marker` | 控制台 |
|---|---|---|---|
| 修复前 | 610 × **0** | **0** | `Pixel(NaN, NaN)` |
| 修复后 | 610 × 498 | **8**（1-1…3-2 全部标记） | 无该错误 |

复刻时务必记住：**给地图容器一个可解析的确定高度**（px 或 vh），不要依赖百分比穿过 `min-height`。

---

## 7. 结果页验收（本机实测 28/28 通过）

把 `scripts/ui-assert.js` 的内容粘到 DevTools 控制台（或在自动化里作为 evaluate 表达式），
它会自动切换六个分节并断言 DOM。实测输出：

```
TripStar UI: 28 pass / 0 fail
OK   DATA 页面已装载 TripPlan [city=西安]
OK   SKELETON .result-container
OK   SKELETON 分区导航 ≥5 项 [行程概览 | 预算明细 | 景点地图 | 每日行程 | 知识图谱 | 天气信息]
OK   OVERVIEW 概览卡片 >0 [slides=8]
OK   OVERVIEW Swiper 已实例化
OK   OVERVIEW 日期/建议 meta [2026-09-16 至 2026-09-18 Plan ID: 6c83aff5 ...]
OK   BUDGET 分区可见
OK   BUDGET 总额为数字 [total=1549]
OK   BUDGET 子项 ≥4 [4 项]
OK   BUDGET 明细行 >0 [19 行]
OK   DAYS 卡片可见
OK   DAYS 天数面板 >0 [3 天]
OK   DAYS 首日景点 >0 [3 个]
OK   DAYS 首日餐饮 >0
OK   WEATHER 分区可见
OK   WEATHER 温度形如 N°C [23°C]
OK   WEATHER 天气文字非空 [晴]
OK   WEATHER CSS 图标已选中 [sunny]
OK   WEATHER 未来几天列表 >0 [3 天]
OK   WEATHER 明细 5 行 [5 行]
OK   KG 分区可见
OK   KG 图例 8 类 [8 类]
OK   KG canvas 已创建 [743x750]
OK   KG 画布已绘制像素 [painted≈82000~101000]
OK   MAP 分区可见
OK   MAP 高德容器有内容 [5 个子节点]
OK   MAP 瓦片/画布已渲染 [2 个]
OK   MAP 景点标记 >0 [8 或 16]
```

说明：
- `KG 画布已绘制像素` 用 `getImageData` 统计非透明像素，是"图真的画出来了"最硬的证据（数字随窗口尺寸变化）。
- `MAP 景点标记` 计数会因 AMap 内部是否额外生成节点而在 8 / 16 之间浮动，断言只要求 >0。
- 两种地图配置（`GOOGLE_MAPS_API_KEY` 有值 / 置空）实测都能 28/28；置空时少了 5s Google 超时等待。

### 已知且非阻塞的行为

| 现象 | 说明 |
|---|---|
| 控制台 `Failed to load Google Maps script` + 5 秒后 `Google Maps 加载超时` | 配了 Google Key 但网络/代理不通，5s 后自动降级高德，**功能正常** |
| ECharts `Can't get DOM width or height` 告警 | 在分节隐藏（`v-show` → 0 尺寸）时重复 init/resize 会出现；KG 可见后仍正常绘制 |
| 点「导出攻略」时若当前不在「景点地图」分节 | `captureMapScreenshot()` 判定容器不可见 → **导出图不含地图**（既有行为，非 bug）；要含地图请先切到地图分节再导出 |

---

## 8. 想彻底避开 Google（符合本 skill 的范围）

把 `GOOGLE_MAPS_API_KEY` 置空（`.env` 或设置页写空串），效果：

1. `get_map_provider()` → `amap`：地理编码/POI 直接用高德，不再有 Google 短路逻辑；
2. 前端 `initMap()` 跳过 Google，**少 5 秒等待**、控制台不再刷 `Failed to load Google Maps script`；
3. `_fallback_amap_weather`（仅 Google 分支触发）自然失效——高德分支本来就不降级。

实测两种配置下结果页均正常，但置空体验更干净。

---

## 9. 验收清单（照抄即可）

- [ ] `backend/.env`、`frontend/.env` 存在且含 LLM / XHS / 高德 Key。
- [ ] 后端用 **`-S` + `PYTHONPATH`** 启动成功，日志出现"已加载 N 个持久化旅行任务"。
- [ ] 前端 `npm run dev` 起在 5173，**用 `localhost` 而不是 `127.0.0.1`** 打开。
- [ ] 访问 `/result?plan_id=<completed task_id>` 不再是空状态。
- [ ] 粘贴 `scripts/ui-assert.js`，结果 `fail: 0`。
- [ ] 「景点地图」能看到底图 + 编号标记（`1-1`…），控制台无 `Pixel(NaN, NaN)`。
- [ ] 「导出攻略」能触发下载（先切到地图分节可让导出图含地图）。