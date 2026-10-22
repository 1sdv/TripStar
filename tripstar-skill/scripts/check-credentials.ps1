#requires -version 5.1
<#
.SYNOPSIS
  TripStar 凭据体检：高德 Key / 安全密钥 / 小红书 Cookie / LLM 配置。
  首次运行项目前建议先跑它。

.DESCRIPTION
  静态检查（默认）：两个 .env 是否存在、键是否齐全、格式是否像样。
  在线探测（-Online）：高德地理编码、LLM chat、后端 health、小红书取图。
  退出码：0 = 全部 PASS/WARN；1 = 存在 FAIL。

.EXAMPLE
  pwsh scripts/check-credentials.ps1
  pwsh scripts/check-credentials.ps1 -Online
  pwsh scripts/check-credentials.ps1 -Online -BaseUrl http://127.0.0.1:8000
#>
[CmdletBinding()]
param(
  [string]$RepoRoot,
  [switch]$Online,
  [string]$BaseUrl = 'http://localhost:8000',
  [int]$TimeoutSec = 12
)

$ErrorActionPreference = 'Continue'
$script:fail = 0
$script:warn = 0
$script:pass = 0

function Out-Ok   { param($m) $script:pass++; Write-Host "  PASS  $m" -ForegroundColor Green }
function Out-Warn { param($m) $script:warn++; Write-Host "  WARN  $m" -ForegroundColor Yellow }
function Out-Fail { param($m) $script:fail++; Write-Host "  FAIL  $m" -ForegroundColor Red }
function Out-Note { param($m) Write-Host "        $m" -ForegroundColor DarkGray }
function Mask      { param($v) if ([string]::IsNullOrEmpty($v)) { '(空)' } elseif ($v.Length -le 8) { '****' } else { $v.Substring(0,4) + '****' + "(len=$($v.Length))" } }

function Find-RepoRoot {
  param([string]$Start)
  $dir = [System.IO.Path]::GetFullPath($Start)
  while ($dir) {
    if (Test-Path (Join-Path $dir 'backend\app\api\main.py')) { return $dir }
    $parent = Split-Path $dir -Parent
    if (-not $parent -or $parent -eq $dir) { break }
    $dir = $parent
  }
  return $null
}

# 解析 .env：返回 hashtable（去掉引号、忽略注释与空行）
function Read-DotEnv {
  param([string]$Path)
  $map = @{}
  if (-not (Test-Path $Path)) { return $map }
  foreach ($raw in (Get-Content $Path -Encoding UTF8)) {
    $line = $raw.Trim()
    if (-not $line -or $line.StartsWith('#')) { continue }
    if ($line.StartsWith('export ')) { $line = $line.Substring(7).Trim() }
    $i = $line.IndexOf('=')
    if ($i -lt 1) { continue }
    $k = $line.Substring(0, $i).Trim()
    $v = $line.Substring($i + 1).Trim()
    if ($v.Length -ge 2 -and (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'")))) {
      $v = $v.Substring(1, $v.Length - 2)
    }
    $map[$k] = $v
  }
  return $map
}

function Pick {
  param($Map, [string[]]$Keys)
  foreach ($k in $Keys) { if ($Map.ContainsKey($k) -and -not [string]::IsNullOrWhiteSpace($Map[$k])) { return @{ key = $k; value = $Map[$k] } } }
  return $null
}

# ---------- 定位仓库 ----------
if (-not $RepoRoot) { $RepoRoot = Find-RepoRoot -Start $PSScriptRoot }
if (-not $RepoRoot) { Write-Host "未找到仓库根（需含 backend\app\api\main.py），请用 -RepoRoot 指定" -ForegroundColor Red; exit 1 }

$backendEnvPath  = Join-Path $RepoRoot 'backend\.env'
$frontendEnvPath = Join-Path $RepoRoot 'frontend\.env'
$backendEnv  = Read-DotEnv $backendEnvPath
$frontendEnv = Read-DotEnv $frontendEnvPath

Write-Host "== TripStar 凭据体检 ==" -ForegroundColor Cyan
Write-Host "仓库: $RepoRoot"
Write-Host "backend/.env : $(if (Test-Path $backendEnvPath) { '存在' } else { '缺失' })   frontend/.env : $(if (Test-Path $frontendEnvPath) { '存在' } else { '缺失' })"

# 两个 .env 都不存在：这是"零配置"场景，给出明确的停止指引
if ((-not (Test-Path $backendEnvPath)) -and (-not (Test-Path $frontendEnvPath))) {
  Write-Host ""
  Write-Host "!! 检测不到任何 .env —— 本项目此时无法生成真实行程（LLM/小红书/高德 全部缺失）。" -ForegroundColor Red
  Write-Host "   第一步：从模板复制（模板已带注释说明每项含义）" -ForegroundColor Yellow
  Write-Host "     Copy-Item backend\.env.example  backend\.env"
  Write-Host "     Copy-Item frontend\.env.example frontend\.env"
  Write-Host "   第二步：按 references/12-credentials-setup.md 填入" -ForegroundColor Yellow
  Write-Host "     §1 高德：VITE_AMAP_WEB_KEY（Web服务） / VITE_AMAP_WEB_JS_KEY + VITE_AMAP_SECURITY_JS_CODE（JS API）"
  Write-Host "     §2 小红书：XHS_COOKIE（浏览器 Network 里复制 cookie 整行）"
  Write-Host "     §3 模型：LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_ID（任何 OpenAI 兼容平台）"
  Write-Host "   第三步：填完重跑本脚本（加 -Online）直到 0 FAIL" -ForegroundColor Yellow
  Write-Host "   ⛔ 在凭据就绪前，不要用编造数据冒充结果；仅界面演示请用 assets/sample-result.json 并标注 demo。" -ForegroundColor Red
  Write-Host ""
}
Write-Host ""

# ---------- 1. 高德 Web 服务 Key（后端） ----------
Write-Host "[1/5] 高德 Web 服务 Key（VITE_AMAP_WEB_KEY，backend/.env）" -ForegroundColor Yellow
$amapWeb = Pick $backendEnv @('VITE_AMAP_WEB_KEY')
if (-not $amapWeb) {
  Out-Fail "未配置"
  Out-Note "去 console.amap.com → 应用管理 → 创建应用 → 添加 Key → 服务平台选【Web服务】"
  Out-Note "详见 references/12-credentials-setup.md §1.1"
} else {
  Out-Ok "已配置 $((Mask $amapWeb.value))"
}

# ---------- 2. 高德 JS API Key（前端） ----------
Write-Host "[2/5] 高德 Web端(JS API) Key（VITE_AMAP_WEB_JS_KEY，frontend/.env）" -ForegroundColor Yellow
$amapJs = Pick $frontendEnv @('VITE_AMAP_WEB_JS_KEY')
if (-not $amapJs) {
  Out-Fail "未配置（也可在网页「设置」里填，会存 localStorage）"
  Out-Note "同上控制台，另建一个 Key，服务平台选【Web端(JS API)】"
} else {
  Out-Ok "已配置 $((Mask $amapJs.value))"
  if ($amapWeb -and $amapJs.value -eq $amapWeb.value) {
    Out-Fail "与 Web 服务 Key 相同：一个 Key 只能绑一个服务平台，地图会报 USERKEY_PLAT_NOMATCH"
  }
}

# ---------- 3. 高德安全密钥 ----------
Write-Host "[3/5] 高德安全密钥（VITE_AMAP_SECURITY_JS_CODE，frontend/.env）" -ForegroundColor Yellow
$amapCode = Pick $frontendEnv @('VITE_AMAP_SECURITY_JS_CODE')
if (-not $amapCode) {
  Out-Fail "未配置 → 地图会灰格/蓝底，控制台 INVALID_USER_SCODE"
  Out-Note "在 JS API Key 详情页可看到「安全密钥 jscode」；改完必须重启 dev server（构建期注入）"
} else {
  $len = $amapCode.value.Length
  if ($len -lt 16) { Out-Warn "长度异常（$len），一般 32 位十六进制" } else { Out-Ok "已配置 $((Mask $amapCode.value))" }
}

# ---------- 4. 小红书 Cookie ----------
Write-Host "[4/5] 小红书 Cookie（XHS_COOKIE，backend/.env）" -ForegroundColor Yellow
$xhs = Pick $backendEnv @('XHS_COOKIE')
if (-not $xhs) {
  Out-Fail "未配置 → 景点搜索失败，任务报【认证失败】"
  Out-Note "浏览器登录 xiaohongshu.com → F12 → Network → 任意请求 → 复制 Request Headers 里 cookie 的整行值"
  Out-Note "详见 references/12-credentials-setup.md §2"
} else {
  $v = $xhs.value
  if ($v.TrimStart().StartsWith('{') -or $v.TrimStart().StartsWith('[')) {
    Out-Warn "看起来是 JSON 格式：项目会自动转换，但更建议用请求头原始串"
  }
  $hasA1 = $v -match '(^|;\s*)a1='
  $hasSession = $v -match '(^|;\s*)web_session='
  if (-not $hasA1) { Out-Warn "缺少 a1 字段，可能不是完整 Cookie" }
  if (-not $hasSession) { Out-Warn "缺少 web_session（未登录态？搜索结果可能为空）" }
  if ($hasA1 -and $hasSession) { Out-Ok "已配置 $((Mask $v))，含 a1 + web_session" }
  elseif ($hasA1) { Out-Warn "已配置 $((Mask $v))，但可能不是登录态" }
  if ($v.Length -gt 3000) { Out-Warn "长度 $($v.Length) 偏大，确认没把整段请求头复制进来" }
}

# ---------- 5. LLM 配置 ----------
Write-Host "[5/5] 模型配置（LLM_* / OPENAI_*，backend/.env）" -ForegroundColor Yellow
$llmKey  = Pick $backendEnv @('LLM_API_KEY','OPENAI_API_KEY')
$llmBase = Pick $backendEnv @('LLM_BASE_URL','OPENAI_BASE_URL')
$llmModel= Pick $backendEnv @('LLM_MODEL_ID','OPENAI_MODEL')
if (-not $llmKey) {
  Out-Fail "API Key 未配置"
  Out-Note "OpenAI: platform.openai.com/api-keys ｜ 火山方舟: console.volcengine.com/ark → API Key 管理"
} else { Out-Ok "Key $((Mask $llmKey.value))（$($llmKey.key)）" }

if (-not $llmBase) { Out-Warn "Base URL 未配置，将回退 https://api.openai.com/v1" }
else {
  if ($llmBase.value -notmatch '^https?://') { Out-Fail "Base URL 不是 http(s) 地址：$($llmBase.value)" }
  else { Out-Ok "Base URL $($llmBase.value)" }
}
if (-not $llmModel) { Out-Warn "Model 未配置，将回退 gpt-4" }
else { Out-Ok "Model $($llmModel.value)" }

# 设置页覆盖提示：runtime_settings.json 优先于 .env
$runtimeFile = Join-Path $RepoRoot 'backend\runtime_settings.json'
if (Test-Path $runtimeFile) {
  try {
    $rt = Get-Content $runtimeFile -Raw -Encoding UTF8 | ConvertFrom-Json
    $rtModel = [string]$rt.openai_model
    if ($rtModel -and $llmModel -and $rtModel -ne $llmModel.value) {
      Out-Warn "设置页覆盖生效：实际使用 $rtModel（.env 里是 $($llmModel.value)）"
      Out-Note "排查/验收请以 http://后端/api/settings 或 runtime_settings.json 为准；-Online 探测会自动用生效值"
    } elseif ($rtModel) {
      Out-Note "设置页已覆盖 LLM 模型（与 .env 相同：$rtModel）"
    }
  } catch { }
}

if ($llmBase -and $llmBase.value -match 'volces\.com') {
  Out-Note "火山方舟：模型 ID 可填推理接入点 ep-xxxx；需先在「在线推理」创建接入点，否则 404 model not found"
}

# ---------- 在线探测 ----------
if ($Online) {
  Write-Host ""
  Write-Host "== 在线探测 ==" -ForegroundColor Cyan

  # 高德 Web 服务
  if ($amapWeb) {
    Write-Host "[net-1] 高德地理编码" -ForegroundColor Yellow
    try {
      $u = "https://restapi.amap.com/v3/geocode/geo?key=$($amapWeb.value)&address=%E5%A4%A9%E5%AE%89%E9%97%A8&city=%E5%8C%97%E4%BA%AC"
      $r = Invoke-RestMethod -Uri $u -TimeoutSec $TimeoutSec
      if ($r.status -eq '1' -and $r.geocodes.Count -gt 0) { Out-Ok "geocode OK（$($r.geocodes[0].location)）" }
      else { Out-Fail "geocode 失败：status=$($r.status) info=$($r.info) infocode=$($r.infocode)" ; Out-Note "USERKEY_PLAT_NOMATCH=平台选错；INVALID_USER_KEY=Key 无效或未实名" }
    } catch { Out-Fail "请求失败：$($_.Exception.Message)" }
  }

  # 后端生效配置：设置页写入 runtime_settings.json，优先级高于 .env
  $eff = $null
  try { $eff = (Invoke-RestMethod -Uri "$($BaseUrl.TrimEnd('/'))/api/settings" -TimeoutSec $TimeoutSec).data } catch { }
  # 后端不可达时退回读设置页持久化的覆盖值（runtime_settings.json），避免拿 .env 旧值误判
  if (-not $eff) {
    $rtFile = Join-Path $RepoRoot 'backend\runtime_settings.json'
    if (Test-Path $rtFile) {
      try { $eff = Get-Content $rtFile -Raw -Encoding UTF8 | ConvertFrom-Json } catch { }
      if ($eff) { Write-Host "        （后端不可达，生效值取自 runtime_settings.json）" -ForegroundColor DarkGray }
    }
  }

  # LLM
  if ($llmKey) {
    Write-Host "[net-2] LLM chat/completions" -ForegroundColor Yellow
    # 以后端生效值为准（设置页 > 环境变量 > .env），否则会拿 .env 的旧值误判
    $base = if ($eff -and $eff.openai_base_url) { ([string]$eff.openai_base_url).TrimEnd('/') }
            elseif ($llmBase) { $llmBase.value.TrimEnd('/') }
            else { 'https://api.openai.com/v1' }
    $model = if ($eff -and $eff.openai_model) { [string]$eff.openai_model }
             elseif ($llmModel) { $llmModel.value }
             else { 'gpt-4' }
    if ($eff -and $eff.openai_model -and $llmModel -and ([string]$eff.openai_model -ne $llmModel.value)) {
      Out-Note "生效模型来自设置页：$($eff.openai_model)（.env 里是 $($llmModel.value)）—— 以后者为准"
    }
    try {
      $json = @{ model = $model; messages = @(@{ role = 'user'; content = 'ping' }); max_tokens = 16 } | ConvertTo-Json -Depth 6 -Compress
      # 必须用 UTF-8 字节数组：PowerShell 5.1 的字符串 body 有可能带 BOM，
      # 服务端会回 `we could not parse the JSON body of your request`
      $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
      $r = Invoke-RestMethod -Method Post -Uri "$base/chat/completions" `
        -Headers @{ Authorization = "Bearer $($llmKey.value)" } `
        -ContentType 'application/json; charset=utf-8' -Body $bytes -TimeoutSec $TimeoutSec
      if ($r.choices.Count -gt 0) { Out-Ok "chat OK（model=$($r.model)）" }
      else { Out-Warn "返回但无 choices：$($r | ConvertTo-Json -Depth 3 -Compress)" }
    } catch {
      $msg = $_.Exception.Message
      $resp = $_.Exception.Response
      $respTxt = ''
      if ($resp) { try { $sr = New-Object System.IO.StreamReader($resp.GetResponseStream()); $respTxt = $sr.ReadToEnd() } catch { } }
      # PowerShell 5.1 下 Invoke-RestMethod 常把错误体放在 ErrorDetails 里
      if ([string]::IsNullOrWhiteSpace($respTxt) -and $_.ErrorDetails -and $_.ErrorDetails.Message) {
        $respTxt = [string]$_.ErrorDetails.Message
      }
      Out-Fail ("调用失败：HTTP " + $(if ($resp) { [int]$resp.StatusCode } else { '?' }) + " — " + $msg)
      if ($respTxt) { Out-Note ("响应体：" + $respTxt.Substring(0, [Math]::Min(400, $respTxt.Length))) }
      if ($respTxt -match 'ClosedEndpoint|InvalidEndpoint') {
        Out-Note "方舟接入点已关闭/不可用：去「在线推理」启用该模型，或把 LLM_MODEL_ID 换成可用的 ep-xxxx / 模型 ID"
      } elseif ($respTxt -match 'could not parse the JSON body') {
        Out-Note "请求体被当成非法 JSON：确认 UTF-8 无 BOM（本脚本已处理），并检查 base_url 是 OpenAI 兼容端点"
      } elseif ($msg -match '401') {
        Out-Note "Key 无效，或 Key 与 Base URL 不属于同一平台"
      } elseif ($msg -match '404') {
        Out-Note "模型不存在 / base_url 少了或多了 /v1 / 方舟未创建接入点"
      } elseif ($msg -match 'timeout|超时') {
        Out-Note "网络或代理问题（客户端已 trust_env=False，不走系统代理）"
      }
    }
  }

  # 后端
  Write-Host "[net-3] 后端健康" -ForegroundColor Yellow
  try {
    $h = Invoke-RestMethod -Uri "$($BaseUrl.TrimEnd('/'))/health" -TimeoutSec $TimeoutSec
    Out-Ok "health OK：$($h.status)（$($h.service)）"
  } catch {
    Out-Warn "后端未启动或不可达（$BaseUrl）——小红书探测需要后端，可先启后端再跑"
  }

  # 小红书（经后端）
  if ($xhs) {
    Write-Host "[net-4] 小红书取图（经后端 /api/poi/photo）" -ForegroundColor Yellow
    try {
      $r = Invoke-RestMethod -Uri "$($BaseUrl.TrimEnd('/'))/api/poi/photo?name=%E8%A5%BF%E6%B9%96" -TimeoutSec 30
      if ($r.success -and $r.data.photo_url) { Out-Ok "取图直链 OK（长度 $($r.data.photo_url.Length)）" }
      else { Out-Warn "未取到图片：$($r | ConvertTo-Json -Depth 3 -Compress)" }
    } catch {
      Out-Warn "调用失败：$($_.Exception.Message)（后端未启动时会这样）"
    }
  }
}

# ---------- 汇总 ----------
Write-Host ""
Write-Host ("== 结果：{0} PASS / {1} WARN / {2} FAIL ==" -f $script:pass, $script:warn, $script:fail) -ForegroundColor $(if ($script:fail -eq 0) { 'Green' } else { 'Red' })
if ($script:fail -gt 0) {
  Write-Host "下一步：按上面 FAIL 的提示补齐凭据；完整获取步骤见 references/12-credentials-setup.md" -ForegroundColor Yellow
  Write-Host "⛔ 补齐前无法生成真实行程：请如实告知用户缺什么，不要编造 TripPlan 或用样例数据冒充结果。" -ForegroundColor Red
  exit 1
}
if (-not $Online) {
  Write-Host "静态检查通过。建议再跑一次带 -Online 的在线探测：pwsh scripts/check-credentials.ps1 -Online" -ForegroundColor Cyan
}
exit 0