#requires -version 5.1
<#
.SYNOPSIS
  启动 TripStar 前端（Vite dev server）。缺少 node_modules 时自动 npm install。

.EXAMPLE
  pwsh scripts/start-frontend.ps1
  pwsh scripts/start-frontend.ps1 -Mode build        # 只做类型检查 + 打包
  pwsh scripts/start-frontend.ps1 -Port 5173
#>
[CmdletBinding()]
param(
  [string]$RepoRoot,
  [ValidateSet('dev', 'build', 'preview')]
  [string]$Mode = 'dev',
  [int]$Port = 5173
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

if (-not $RepoRoot) { $RepoRoot = Find-RepoRoot -Start $PSScriptRoot }
if (-not $RepoRoot) { throw "未找到仓库根目录（应包含 backend\app\api\main.py）。请用 -RepoRoot 指定。" }
if (-not (Test-Path (Join-Path $RepoRoot 'frontend\package.json'))) {
  throw "不是有效的 TripStar 仓库根目录：$RepoRoot（缺少 frontend\package.json）"
}

$frontend = Join-Path $RepoRoot 'frontend'
if (-not (Test-Path (Join-Path $frontend 'package.json'))) { throw "未找到 frontend\package.json：$frontend" }

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "未找到 npm，请先安装 Node.js 18+。"
}

Write-Host "前端目录: $frontend" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
  Write-Host "安装依赖（npm install）..." -ForegroundColor Yellow
  Push-Location $frontend; try { npm install } finally { Pop-Location }
}

if (-not (Test-Path (Join-Path $frontend '.env'))) {
  Write-Host "提示: 未发现 frontend\.env —— 地图需要 VITE_AMAP_WEB_JS_KEY（可在页面设置里填，运行时生效）。" -ForegroundColor DarkYellow
}

Push-Location $frontend
try {
  switch ($Mode) {
    'dev' {
      Write-Host "启动 Vite dev server (http://localhost:$Port) ..." -ForegroundColor Green
      npm run dev -- --port $Port
    }
    'build' {
      Write-Host "类型检查 + 打包（vue-tsc && vite build）..." -ForegroundColor Green
      npm run build
    }
    'preview' {
      Write-Host "预览 dist ..." -ForegroundColor Green
      npm run preview
    }
  }
} finally {
  Pop-Location
}