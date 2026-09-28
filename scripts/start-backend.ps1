#Requires -Version 5.1
<#
.SYNOPSIS
  Start FastAPI backend on http://0.0.0.0:8000
.PARAMETER Detached
  Open a new PowerShell window and return immediately.
.EXAMPLE
  .\scripts\start-backend.ps1
  .\scripts\start-backend.ps1 -Detached
#>
param(
  [switch]$Detached,
  [switch]$SkipMysql,
  [string]$HostAddress = '0.0.0.0',
  [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"

if ($Detached) {
  $argList = @(
    '-NoExit',
    '-ExecutionPolicy', 'Bypass',
    '-File', (Join-Path $PSScriptRoot 'start-backend.ps1')
  )
  if ($SkipMysql) { $argList += '-SkipMysql' }
  $argList += @('-HostAddress', $HostAddress, '-Port', "$Port")
  Start-Process powershell.exe -ArgumentList $argList -WorkingDirectory $RepoRoot | Out-Null
  Write-Ok "Backend window launched"
  exit 0
}

Write-Host ""
Write-Step "==== Start Backend ===="
Write-Host "  root: $RepoRoot"

if (-not $SkipMysql) {
  if (-not (Ensure-MysqlRunning)) { exit 1 }
}

$py = Get-BackendPython
if (-not $py) {
  Write-Err "Python not found. Create backend\.venv first:"
  Write-Host "  cd backend"
  Write-Host "  C:\ruanjian\python3\python.exe -m venv .venv"
  Write-Host "  .\.venv\Scripts\Activate.ps1"
  Write-Host "  pip install -r requirements.txt"
  exit 1
}
Write-Ok "Python: $py"

if (-not (Test-Path (Join-Path $BackendDir '.env'))) {
  Write-Warn "backend\.env missing. Copy backend\.env.example to backend\.env and fill configs."
}

if (Test-PortListening $Port) {
  Write-Warn "Port $Port already in use. Stop it first: .\scripts\stop-dev.ps1"
  exit 1
}

Set-Location $BackendDir
Write-Step "[Backend] uvicorn app.main:app --reload --host $HostAddress --port $Port"
Write-Host "  docs:   http://127.0.0.1:$Port/docs"
Write-Host "  health: http://127.0.0.1:$Port/api/v1/health"
Write-Host ""

& $py -m uvicorn app.main:app --reload --host $HostAddress --port $Port
