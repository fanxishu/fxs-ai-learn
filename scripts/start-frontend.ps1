#Requires -Version 5.1
<#
.SYNOPSIS
  Start Taro weapp frontend watch build (output: frontend/dist).
.PARAMETER Detached
  Open a new PowerShell window and return immediately.
.EXAMPLE
  .\scripts\start-frontend.ps1
  .\scripts\start-frontend.ps1 -Detached
#>
param(
  [switch]$Detached
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"

if ($Detached) {
  Start-Process powershell.exe -ArgumentList @(
    '-NoExit',
    '-ExecutionPolicy', 'Bypass',
    '-File', (Join-Path $PSScriptRoot 'start-frontend.ps1')
  ) -WorkingDirectory $RepoRoot | Out-Null
  Write-Ok "Frontend window launched"
  exit 0
}

Write-Host ""
Write-Step "==== Start Frontend ===="
Write-Host "  root: $FrontendDir"

$nodeModules = Join-Path $FrontendDir 'node_modules'
if (-not (Test-Path $nodeModules)) {
  Write-Warn "node_modules missing, running npm install ..."
  Push-Location $FrontendDir
  try {
    npm install
    if ($LASTEXITCODE -ne 0) { throw "npm install failed with code $LASTEXITCODE" }
  } finally {
    Pop-Location
  }
}

Set-Location $FrontendDir
Write-Step "[Frontend] npm run dev:weapp"
Write-Host "  Open WeChat DevTools with directory: $FrontendDir\dist"
Write-Host ""

npm run dev:weapp
