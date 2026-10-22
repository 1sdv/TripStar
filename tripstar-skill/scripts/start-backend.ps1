#requires -version 5.1
<#
.SYNOPSIS
  启动 TripStar 后端（FastAPI）。首次运行会自动创建 .venv 并安装依赖。

.DESCRIPTION
  - 自动向上查找仓库根（含 backend/app/api/main.py 的目录），也可用 -RepoRoot 指定。
  - 优先使用 uv（uv venv / uv pip install）；没有 uv 时回退到 python -m venv + pip。
  - 启动后前台运行 uvicorn（Ctrl+C 退出）。

.EXAMPLE
  pwsh scripts/start-backend.ps1
  pwsh scripts/start-backend.ps1 -RepoRoot D:\code\TripStar -Port 8000
#>
[CmdletBinding()]
param(
  [string]$RepoRoot,
  [int]$Port = 8000,
  [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'

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

if (-not $RepoRoot) {
  $RepoRoot = Find-RepoRoot -Start $PSScriptRoot
}
if (-not $RepoRoot) {
  throw "未找到仓库根目录（应包含 backend\app\api\main.py）。请用 -RepoRoot 指定。"
}
if (-not (Test-Path (Join-Path $RepoRoot 'backend\app\api\main.py'))) {
  throw "不是有效的 TripStar 仓库根目录：$RepoRoot（缺少 backend\app\api\main.py）"
}

$backend = Join-Path $RepoRoot 'backend'
$venv = Join-Path $backend '.venv'
$venvPy = Join-Path $venv 'Scripts\python.exe'
$req = Join-Path $backend 'requirements.txt'

Write-Host "仓库根: $RepoRoot" -ForegroundColor Cyan
Write-Host "后端目录: $backend" -ForegroundColor Cyan

$hasUv = [bool](Get-Command uv -ErrorAction SilentlyContinue)
$hasPy = [bool](Get-Command python -ErrorAction SilentlyContinue)

if (-not (Test-Path $venvPy)) {
  if ($SkipInstall) { throw "虚拟环境不存在且指定了 -SkipInstall：$venv" }
  Write-Host "创建虚拟环境..." -ForegroundColor Yellow
  if ($hasUv) {
    Push-Location $backend; try { uv venv .venv } finally { Pop-Location }
  } elseif ($hasPy) {
    Push-Location $backend; try { python -m venv .venv } finally { Pop-Location }
  } else {
    throw "既没有 uv 也没有 python，请先安装其一（推荐：winget install astral-sh.uv）。"
  }
}

if (-not $SkipInstall) {
  Write-Host "安装/校验依赖（requirements.txt）..." -ForegroundColor Yellow
  if ($hasUv) {
    uv pip install --python $venvPy -r $req
  } else {
    & $venvPy -m pip install --upgrade pip
    & $venvPy -m pip install -r $req
  }
}

if (-not (Test-Path (Join-Path $backend '.env'))) {
  Write-Host "提示: 未发现 backend\.env —— 服务可启动，但 LLM/小红书/高德相关功能会失败。" -ForegroundColor DarkYellow
  if (Test-Path (Join-Path $backend '.env.example')) {
    Write-Host "      可复制 .env.example 为 .env 后填入 Key。" -ForegroundColor DarkYellow
  }
}

Write-Host "启动 uvicorn (http://localhost:$Port) ..." -ForegroundColor Green
Push-Location $backend
try {
  & $venvPy -m uvicorn 'app.api.main:app' --host 0.0.0.0 --port $Port --reload
} finally {
  Pop-Location
}