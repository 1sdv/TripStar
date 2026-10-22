#requires -version 5.1
<#
.SYNOPSIS
  TripStar 冒烟验证：后端健康 / 配置读取 / 任务历史，可选前端构建。

.DESCRIPTION
  以退出码表达结果：0 = 全部通过；1 = 有检查失败。
  后端未启动时会给出明确提示（不是脚本错误）。

.EXAMPLE
  pwsh scripts/verify.ps1
  pwsh scripts/verify.ps1 -BaseUrl http://127.0.0.1:8000 -BuildFrontend
#>
[CmdletBinding()]
param(
  [string]$BaseUrl = 'http://localhost:8000',
  [string]$RepoRoot,
  [switch]$BuildFrontend,
  [int]$TimeoutSec = 8
)

$ErrorActionPreference = 'Continue'
$script:failed = 0
$script:passed = 0

function Write-Result {
  param([string]$Name, [bool]$Ok, [string]$Detail = '')
  if ($Ok) {
    $script:passed++
    Write-Host ("  [PASS] {0}{1}" -f $Name, $(if ($Detail) { " — $Detail" } else { '' })) -ForegroundColor Green
  } else {
    $script:failed++
    Write-Host ("  [FAIL] {0}{1}" -f $Name, $(if ($Detail) { " — $Detail" } else { '' })) -ForegroundColor Red
  }
}

function Invoke-Api {
  param([string]$Path, [string]$Method = 'Get', $Body)
  $uri = ($BaseUrl.TrimEnd('/')) + $Path
  $args = @{ Uri = $uri; Method = $Method; TimeoutSec = $TimeoutSec; ErrorAction = 'Stop' }
  if ($Body) { $args.ContentType = 'application/json'; $args.Body = $Body }
  return Invoke-RestMethod @args
}

Write-Host "== TripStar 冒烟验证 ==" -ForegroundColor Cyan
Write-Host "后端: $BaseUrl"
Write-Host ""

# 1) 健康检查
Write-Host "1) 后端存活" -ForegroundColor Yellow
$health = $null
try {
  $health = Invoke-Api -Path '/health'
  Write-Result 'GET /health' ($health.status -eq 'healthy' -or $null -ne $health.status) ("status=" + $health.status)
} catch {
  Write-Result 'GET /health' $false "无法连接后端（是否已启动？$($_.Exception.Message)）"
  Write-Host "`n后端不可达，跳过后续检查。" -ForegroundColor Red
  exit 1
}

# 2) 运行时配置
Write-Host "2) 运行时配置" -ForegroundColor Yellow
try {
  $settings = Invoke-Api -Path '/api/settings'
  $data = $settings.data
  Write-Result 'GET /api/settings' ($null -ne $data) ''

  $secretMasked = { param($v) if ([string]::IsNullOrEmpty($v)) { '未配置' } elseif ($v -match '•') { '已配置(掩码)' } else { '已配置' } }
  Write-Host ('     openai_api_key   : ' + (& $secretMasked $data.openai_api_key))
  Write-Host ('     openai_base_url  : ' + ($(if ($data.openai_base_url) { $data.openai_base_url } else { '(空)' })))
  Write-Host ('     openai_model     : ' + ($(if ($data.openai_model) { $data.openai_model } else { '(空)' })))
  Write-Host ('     vite_amap_web_key: ' + (& $secretMasked $data.vite_amap_web_key))
  Write-Host ('     amap_web_js_key  : ' + (& $secretMasked $data.vite_amap_web_js_key))
  Write-Host ('     xhs_cookie       : ' + (& $secretMasked $data.xhs_cookie))

  if ([string]::IsNullOrEmpty($data.openai_api_key)) {
    Write-Host '     提示: LLM Key 未配置 → 规划任务会失败' -ForegroundColor DarkYellow
  }
  if ([string]::IsNullOrEmpty($data.xhs_cookie)) {
    Write-Host '     提示: 小红书 Cookie 未配置 → 景点搜索会失败' -ForegroundColor DarkYellow
  }
  if ([string]::IsNullOrEmpty($data.vite_amap_web_key)) {
    Write-Host '     提示: 高德 Web 服务 Key 未配置 → 地理编码/POI/天气工具不可用' -ForegroundColor DarkYellow
  }
} catch {
  Write-Result 'GET /api/settings' $false $_.Exception.Message
}

# 3) 任务历史（验证 JSON 持久化链路）
Write-Host "3) 任务持久化" -ForegroundColor Yellow
try {
  $history = Invoke-Api -Path '/api/trip/history?limit=3'
  $count = @($history.items).Count
  Write-Result 'GET /api/trip/history' ($null -ne $history.items) ("已完成计划 $count 条")
} catch {
  Write-Result 'GET /api/trip/history' $false $_.Exception.Message
}

# 4) 地图能力自检（不依赖 Key，只看端点是否注册）
Write-Host "4) 端点注册" -ForegroundColor Yellow
try {
  $null = Invoke-Api -Path '/api/map/health'
  Write-Result 'GET /api/map/health' $true ''
} catch {
  # 高德未配置时该端点可能返回 5xx，只要不是 404 就说明路由存在
  $msg = $_.Exception.Message
  $is404 = $msg -match '404'
  Write-Result 'GET /api/map/health' (-not $is404) $msg
}

# 5) 可选：前端构建
if ($BuildFrontend) {
  Write-Host "5) 前端类型检查与构建" -ForegroundColor Yellow
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
  $root = if ($RepoRoot) { $RepoRoot } else { Find-RepoRoot -Start $PSScriptRoot }
  if (-not $root) {
    Write-Result 'npm run build' $false '未找到仓库根目录'
  } else {
    $frontend = Join-Path $root 'frontend'
    Push-Location $frontend
    try {
      npm run build
      Write-Result 'npm run build' ($LASTEXITCODE -eq 0) "exit=$LASTEXITCODE"
    } catch {
      Write-Result 'npm run build' $false $_.Exception.Message
    } finally {
      Pop-Location
    }
  }
}

Write-Host ""
Write-Host ("== 结果: {0} 通过, {1} 失败 ==" -f $script:passed, $script:failed) -ForegroundColor $(if ($script:failed -eq 0) { 'Green' } else { 'Red' })
exit $(if ($script:failed -eq 0) { 0 } else { 1 })