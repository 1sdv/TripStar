# 12 · 首次运行：4 个凭据怎么拿、放哪里、怎么验证

> 这份文档是**第一次把项目跑起来前必读**。缺任何一个凭据，结果页都会"能打开但不完整"。
> 对应的自动体检脚本：`scripts/check-credentials.ps1`。

> ⛔ **给 AI 代理的硬性约定**：本文件是"缺配置时的唯一正确出路"。
> 当 `check-credentials.ps1` 报 FAIL，或仓库里根本没有 `.env` 时：
> **不要编造 TripPlan / 行程 / 天气 / 预算数据**，也不要把 `assets/sample-result.json` 说成"刚生成的结果"。
> 正确做法是停下来，按下面 §1（高德）/ §2（小红书）/ §3（模型）逐项让用户补齐，再跑一次体检。
> 只有在用户**明确**要"只看界面/离线预览"时，才可以拿 `assets/sample-result.json` 渲染，且必须标注为 demo 样例。

---

## 0. 一张表看清要什么

| # | 凭据 | 环境变量 | 放在哪 | 缺了会怎样 |
|---|---|---|---|---|
| 1 | 高德 **Web 服务** Key | `VITE_AMAP_WEB_KEY` | `backend/.env` | 地理编码/POI/天气/酒店全废 → 景点无经纬度、地图无标记、酒店空 |
| 2 | 高德 **Web端(JS API)** Key | `VITE_AMAP_WEB_JS_KEY` | `frontend/.env`（或设置页） | 「景点地图」空白，只提示"请先在设置中配置高德地图 JS Key" |
| 3 | 高德 **安全密钥 jscode** | `VITE_AMAP_SECURITY_JS_CODE` | `frontend/.env` | 地图灰格/一片蓝，控制台 `INVALID_USER_SCODE` |
| 4 | 小红书 **Cookie** | `XHS_COOKIE` | `backend/.env` | 景点搜索失败 → 任务 failed 且文案带【认证失败】 |
| 5 | **LLM** Key/Base/Model | `LLM_API_KEY`（或 `OPENAI_API_KEY`）等 | `backend/.env` | 任务直接 failed，`validate_config()` 只warning |

> 1/4/5 是**后端**环境变量，2/3 是**前端**（Vite 构建期注入）。
> 全部也可以在网页「设置」里填——写进 `backend/runtime_settings.json`，**优先级高于 `.env`**，且热生效（后端会重置单例，前端派发事件重建地图）。

---

## 1. 高德：三个值，两个服务平台，别搞混

控制台：<https://console.amap.com/>（原 lbs.amap.com）→ 登录/实名 → **应用管理 → 我的应用 → 创建新应用** → 进入应用 → **添加 Key**。

**一个 Key 只能绑一个「服务平台」**，本项目需要两个 Key：

### 1.1 `VITE_AMAP_WEB_KEY`（后端用，服务平台选 **Web服务**）

- 用途：服务端 REST —— 地理编码 `v3/geocode`、POI `v3/place/text`、路线、天气；
  同时作为 `uvx amap-mcp-server` 的 `AMAP_MAPS_API_KEY`（天气/酒店 Agent 的工具）。
- 校验（把 `KEY` 换掉，直接在浏览器/curl 打开）：

  ```
  https://restapi.amap.com/v3/geocode/geo?key=KEY&address=天安门&city=北京
  ```

  返回 `"status":"1"` 且 `geocodes[0].location` 有 `经度,纬度` → 可用。

  常见错误码：

  | 返回 | 含义 |
  |---|---|
  | `INVALID_USER_KEY` / `USERKEY_PLAT_NOMATCH` | Key 无效，或把它做成了 JS Key（服务平台选错） |
  | `DAILY_QUERY_OVER_LIMIT` | 超出当日免费配额 |
  | `INVALID_USER_SCODE` | 用了 JS Key 去调 Web 服务 |

### 1.2 `VITE_AMAP_WEB_JS_KEY`（前端用，服务平台选 **Web端(JS API)**）

- 用途：浏览器里 `AMapLoader.load({key})` 渲染地图、Marker、Polyline、路线规划。
- 在 Key 详情页里同时能拿到 **安全密钥（securityJsCode）** —— 见下一条。

### 1.3 `VITE_AMAP_SECURITY_JS_CODE`（安全密钥 jscode）

- 2021-12 之后新申请的 JS API Key **必须**配安全密钥，否则地图请求被拒。
- 本项目的注入方式（已实现，无需改代码）：`vite.config.ts` 在构建/启动时把
  `VITE_AMAP_SECURITY_JS_CODE` 替换进 `index.html` 的 `__AMAP_SECURITY_JS_CODE__` 占位符，
  等价于官方要求的 `window._AMapSecurityConfig = { securityJsCode: '...' }`。
- **改了它必须重启 dev server**（构建期注入，HMR 不生效）。
- 校验：地图能出瓦片、控制台无 `INVALID_USER_SCODE` / `USERKEY_PLAT_NOMATCH`。

### 落地写法

`backend/.env`
```dotenv
VITE_AMAP_WEB_KEY=你的Web服务Key
```

`frontend/.env`
```dotenv
VITE_AMAP_WEB_JS_KEY=你的JSAPIKey
VITE_AMAP_SECURITY_JS_CODE=你的安全密钥
```

> 也支持在网页「设置」里改前端的 JS Key（写入 localStorage，立即生效），但**安全密钥只能走 `.env`**（构建期注入）。

---

## 2. 小红书 Cookie：从浏览器抄，注意格式与寿命

### 2.1 获取步骤

1. 浏览器（建议专用小号）登录 <https://www.xiaohongshu.com>，随便搜一个词、打开一篇笔记，确保是已登录态。
2. `F12` → **Network** 面板 → 刷新页面 → 点任意一个 `xhr/fetch` 请求（域名 `edith.xiaohongshu.com` 或 `www.xiaohongshu.com`）。
3. 右侧 **Headers → Request Headers** 里找到 `cookie:` 一行，**复制整行的值**（不要带 `cookie:` 前缀）。
4. 粘贴进 `backend/.env`：

   ```dotenv
   XHS_COOKIE=a1=xxxx; webId=xxxx; web_session=xxxx; gid=xxxx; xsecappid=xhs-pc-web; ...
   ```

### 2.2 格式与常见坑

- 必须是 `k=v; k=v; ...` 的**请求头字符串**形式。项目里的 `normalize_xhs_cookie()` 也兼容
  **JSON 格式**（浏览器插件导出的 `[{name,value},...]` 或对象）会自动转换，所以粘错格式不一定报错，但**建议用上面第 3 步的原始串**。
- 建议包含登录态字段（尤其 `web_session`，未登录游客态可能只有 `a1`，会导致搜索结果为空）。
- `.env` 值里有 `#` 时建议整体用双引号包起来（dotenv 会把 `#` 之后当注释）。
- **寿命**：`a1` 相对长期，`web_session` 有期限；频繁请求会触发风控。过期表现：
  后端日志/任务错误里出现 `【认证失败】` 或 `code=300011` → 重新按 §2.1 抄一次。
- **风险提示**：这是非官方 Web 接口 + 签名直连，仅适合个人学习研究；高频调用可能触发风控甚至封号，不要用于生产或商业用途。

### 2.3 校验（需要后端在跑）

```powershell
# 1) 取图直链（内部会走一次小红书搜索）
Invoke-RestMethod "http://localhost:8000/api/poi/photo?name=西湖"
# 期望：success=True 且 data.photo_url 非空

# 2) 走代理取真实图片字节
Invoke-WebRequest "http://localhost:8000/api/poi/image?name=西湖" -UseBasicParsing | Select-Object StatusCode, Content-Type
# 期望：200 + image/jpeg（或 image/webp）
```

---

## 3. 模型配置：一个 Key + 一个 Base URL + 一个 Model

项目用 `openai` SDK 打 **OpenAI 兼容**接口，所以只要是"兼容 OpenAI 协议"的平台都能用。
三个值都能被 `.env`、环境变量、网页设置页三处覆盖（优先级：设置页 > 环境变量 > `.env`）。

> ⚠️ **实测踩过的坑**：设置页保存后会写 `backend/runtime_settings.json`，它**盖住 `.env`**。
> 曾出现"`.env` 里写的模型已下线（`InvalidEndpoint.ClosedEndpoint`），但设置页早已换成另一个可用模型" →
> 直接看 `.env` 会误判为失败。**排查顺序：先 `GET /api/settings`（或读 `runtime_settings.json`），再看 `.env`。**
> `scripts/check-credentials.ps1` 已按这个优先级取值，并会提示"设置页覆盖生效"。

### 3.1 变量名对应关系（支持两套别名）

| 用途 | 别名（二者其一即可） | 说明 |
|---|---|---|
| API Key | `LLM_API_KEY` / `OPENAI_API_KEY` | 必须 |
| Base URL | `LLM_BASE_URL` / `OPENAI_BASE_URL` | 兼容端点根路径，通常以 `/v1` 结尾 |
| 模型 | `LLM_MODEL_ID` / `OPENAI_MODEL` | 平台侧的模型 ID / 接入点 ID |

### 3.2 常见三种来源

**A. OpenAI 官方**
- Key：<https://platform.openai.com/api-keys> → Create new secret key（`sk-...`）
- `LLM_BASE_URL=https://api.openai.com/v1`，`LLM_MODEL_ID=gpt-4o-mini`（或你账号可用的模型）
- 注意：国内直连常需代理；本项目 LLM 客户端**主动清空了系统代理**（`trust_env=False`），若你依赖代理访问 OpenAI，需自行在 base_url 侧解决。

**B. 火山方舟 Ark（本机 `.env` 用的就是这套）**
- 控制台：<https://console.volcengine.com/ark> → API Key 管理 → 创建 API Key
- `LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3`
- `LLM_MODEL_ID`：填**推理接入点 ID（`ep-xxxxxxxx`）**，或平台直接支持、且已启用的模型 ID
- 坑：方舟需要先在「在线推理」里为该模型**创建接入点**，否则会报模型不存在；只建了 Key 没建接入点会 `404 model not found`。

**C. 其它 OpenAI 兼容平台（任选）**
- DeepSeek：`https://api.deepseek.com/v1` + `deepseek-chat`
- 阿里百炼（兼容模式）：`https://dashscope.aliyuncs.com/compatible-mode/v1` + `qwen-plus`
- 智谱：`https://open.bigmodel.cn/api/paas/v4` + `glm-4`
- 自建 vLLM/Ollama：`http://127.0.0.1:8000/v1`（注意别和后端 8000 冲突）+ 你的模型名

> 模型能力要求：要能稳定输出**长 JSON**（整个行程 > 10k tokens 输出）。太小的模型极易被截断，
> 会走到 JSON 修复/重试路径，甚至失败。建议 32k+ 上下文的模型。

### 3.3 校验

```powershell
# 看后端读到什么（密钥被掩码）
Invoke-RestMethod "http://localhost:8000/api/settings" | ConvertTo-Json -Depth 4

# 直接打一次极小请求（把三个变量替换成你的）
$h = @{ Authorization = "Bearer $env:LLM_API_KEY"; 'Content-Type' = 'application/json' }
$b = @{ model = $env:LLM_MODEL_ID; messages = @(@{ role='user'; content='ping' }); max_tokens = 5 } | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post -Uri "$($env:LLM_BASE_URL)/chat/completions" -Headers $h -Body $b
# 期望：返回 choices[0].message.content
```

常见错误：

| 报错 | 原因 |
|---|---|
| `401 Unauthorized` | Key 错/过期，或 base_url 与 Key 不属于同一平台 |
| `400 InvalidEndpoint.ClosedEndpoint` | **火山方舟**：该推理接入点已关闭/不可用 → 去「在线推理」启用，或换可用的 `ep-xxxx` / 模型 ID |
| `400 we could not parse the JSON body` | 请求体带了 BOM 或被当成非 UTF-8。本项目 `openai` SDK 正常；手工用 PowerShell/curl 测试时要保证 **UTF-8 无 BOM**（PS 5.1 的 `Set-Content -Encoding UTF8` 会写 BOM，用 `[IO.File]::WriteAllText($p,$json,(New-Object Text.UTF8Encoding($false)))`） |
| `404 model not found` | 模型 ID 写错；方舟未创建推理接入点 |
| `404 Not Found`（路径） | base_url 少了/多了 `/v1` |
| 一直超时 | 网络/代理问题（本项目已 `trust_env=False` 且清空代理环境变量） |

### 3.4 落地写法

`backend/.env`
```dotenv
LLM_API_KEY=你的Key
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_MODEL_ID=你的模型ID或接入点ID
LLM_TIMEOUT=600
TRIP_PLANNER_TIMEOUT=180
```

---

## 4. 一次性自检（推荐）

```powershell
pwsh scripts/check-credentials.ps1                 # 只查 .env 完整性 + 静态格式
pwsh scripts/check-credentials.ps1 -Online         # 额外做真实网络探测（高德/LLM/小红书/后端）
pwsh scripts/check-credentials.ps1 -Online -BaseUrl http://localhost:8000
```

输出逐项给出 `PASS / WARN / FAIL` 与**下一步该做什么**。下面是本机实测（真实输出，密钥已掩码）：

```text
[1/5] VITE_AMAP_WEB_KEY (backend/.env)       PASS  <前4位>****(len=32)
[2/5] VITE_AMAP_WEB_JS_KEY (frontend/.env)   PASS  <前4位>****(len=32)
[3/5] VITE_AMAP_SECURITY_JS_CODE             PASS  <前4位>****(len=32)
[4/5] XHS_COOKIE                             PASS  <前4位>****(len=701)，含 a1 + web_session
[5/5] LLM_*                                  PASS  Key <前4位>****(len=36) / Base https://ark... / Model <你的模型ID>

== 在线探测 ==
[net-1] 高德地理编码   PASS  geocode OK（116.397463,39.909187）
[net-2] LLM chat       FAIL  HTTP 400 — Bad Request
                              响应体：{"error":{"code":"InvalidEndpoint.ClosedEndpoint", ...}}
                              方舟接入点已关闭/不可用：去「在线推理」启用该模型，或把 LLM_MODEL_ID 换成可用的 ep-xxxx / 模型 ID
[net-3] 后端健康       PASS  health OK：healthy
[net-4] 小红书取图     PASS  取图直链 OK（长度 <n>）

== 结果：10 PASS / 0 WARN / 1 FAIL ==
```

> 这个 FAIL 是**真实且有价值的**示例：静态看配置齐全，但方舟的接入点没开，一跑规划就会失败。
> 脚本会打印服务端返回体并直接给修复方向，不需要你自己去猜 400 的原因。
> `[net-4] 小红书取图` 需要后端已启动；后端没起时该项为 WARN（不算失败）。

---

## 5. 缺凭据时的表现对照表（排障用）

| 缺失 | 现象 | 定位点 |
|---|---|---|
| `VITE_AMAP_WEB_KEY` | 任务能跑但有景点无坐标 → 地图无标记；酒店/天气为空 | 后端日志 `高德地理编码查阅失败`；`/api/map/health` |
| `VITE_AMAP_WEB_JS_KEY` | 地图卡片为空 + toast「请先在设置中配置高德地图 JS Key」 | 前端控制台 |
| `VITE_AMAP_SECURITY_JS_CODE` | 地图灰格/蓝底，控制台 `INVALID_USER_SCODE` | 需重启 dev server 后重试 |
| `XHS_COOKIE` | 任务 failed，文案 `【认证失败】`；或景点质量差（搜到无关内容） | 后端日志 `小红书搜索失败 (code=300011)` |
| `LLM_*` | 任务 failed；`/api/trip/health` 正常但 `plan` 一直 processing 后失败 | 设置页 `/api/settings`、`_llm_repair_json` 日志 |
| 全部缺失 | 服务能启、页面能开、但点"开始规划"必失败 | `validate_config()` 的 warning 列表 |

---

## 6. 首次运行顺序（照着走）

1. 拿 4 个凭据 → 分别写进 `backend/.env` 与 `frontend/.env`（见 §1–§3）。
2. `pwsh scripts/check-credentials.ps1 -Online` → 全 PASS（小红书一项需要后端已启动）。
3. 启后端（本机 conda 需 `-S` + `PYTHONPATH`，见 `11-local-run-verified.md` §2）。
4. 启前端，**用 `http://localhost:5173` 打开**（CORS 只放行 localhost）。
5. 填表单提交一次真实规划 → 观察进度条走完 6 个阶段。
6. 进结果页逐区检查 → 粘 `scripts/ui-assert.js` 期望 `28 pass / 0 fail`。
7. 若地图没标记：先看容器高度（`11` §6），再看 JS Key / 安全密钥。