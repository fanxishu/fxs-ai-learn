#Requires -Version 5.1
<#
.SYNOPSIS
  One-click local start: MySQL + backend + frontend (two new windows).
.EXAMPLE
  .\scripts\start-dev.ps1
#>
param(
  [switch]$SkipMysql
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  智能 AI 闯关 - 本地开发一键启动" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not $SkipMysql) {
  if (-not (Ensure-MysqlRunning)) { exit 1 }
}

if (Test-PortListening 8000) {
  Write-Warn "Port 8000 already in use. Will not start another backend."
} else {
  & "$PSScriptRoot\start-backend.ps1" -Detached -SkipMysql
}

& "$PSScriptRoot\start-frontend.ps1" -Detached

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  已打开后端 / 前端独立窗口" -ForegroundColor Green
Write-Host "  后端: http://127.0.0.1:8000/docs" -ForegroundColor Gray
Write-Host "  健康检查: http://127.0.0.1:8000/api/v1/health" -ForegroundColor Gray
Write-Host "  前端产物: $FrontendDir\dist  （导入微信开发者工具）" -ForegroundColor Gray
Write-Host "  停止全部: .\scripts\stop-dev.ps1" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
