#Requires -Version 5.1
<#
.SYNOPSIS
  Shared helpers for local start/stop scripts.
#>

$script:RepoRoot = Split-Path -Parent $PSScriptRoot
$script:BackendDir = Join-Path $RepoRoot 'backend'
$script:FrontendDir = Join-Path $RepoRoot 'frontend'

$script:DefaultMysqlHome = 'C:\ruanjian\mysql'
$script:DefaultPythonCandidates = @(
  (Join-Path $BackendDir '.venv\Scripts\python.exe'),
  'C:\ruanjian\python3\python.exe',
  'python'
)

function Write-Step([string]$Message, [string]$Color = 'Cyan') {
  Write-Host $Message -ForegroundColor $Color
}

function Write-Ok([string]$Message) { Write-Host "  OK  $Message" -ForegroundColor Green }
function Write-Warn([string]$Message) { Write-Host " WARN $Message" -ForegroundColor Yellow }
function Write-Err([string]$Message) { Write-Host " ERR  $Message" -ForegroundColor Red }

function Test-PortListening([int]$Port) {
  try {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
      Select-Object -First 1
    return $null -ne $conn
  } catch {
    $line = netstat -ano | Select-String ":$Port\s+.*LISTENING"
    return $null -ne $line
  }
}

function Get-BackendPython {
  foreach ($candidate in $DefaultPythonCandidates) {
    if ($candidate -eq 'python') {
      $cmd = Get-Command python -ErrorAction SilentlyContinue
      if ($cmd) { return $cmd.Source }
      continue
    }
    if (Test-Path $candidate) { return $candidate }
  }
  return $null
}

function Ensure-MysqlRunning {
  param(
    [string]$MysqlHome = $env:FXS_MYSQL_HOME
  )
  if (-not $MysqlHome) { $MysqlHome = $DefaultMysqlHome }

  if (Test-PortListening 3306) {
    Write-Ok "MySQL already listening on 3306"
    return $true
  }

  $mysqld = Join-Path $MysqlHome 'bin\mysqld.exe'
  $myIni = Join-Path $MysqlHome 'my.ini'
  if (-not (Test-Path $mysqld)) {
    Write-Err "mysqld not found: $mysqld"
    Write-Warn "Set FXS_MYSQL_HOME or start MySQL manually, then retry."
    return $false
  }

  Write-Step "[MySQL] starting $mysqld ..."
  $args = @()
  if (Test-Path $myIni) {
    $args += "--defaults-file=$($myIni -replace '\\','/')"
  }
  Start-Process -FilePath $mysqld -ArgumentList $args -WindowStyle Hidden | Out-Null

  for ($i = 1; $i -le 20; $i++) {
    Start-Sleep -Seconds 1
    if (Test-PortListening 3306) {
      Write-Ok "MySQL ready (after ${i}s)"
      return $true
    }
  }

  Write-Err "MySQL did not open port 3306 in time"
  return $false
}

function Stop-PortProcess([int]$Port, [string]$Label) {
  try {
    $pids = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
      Select-Object -ExpandProperty OwningProcess -Unique
  } catch {
    $pids = @()
  }

  foreach ($procId in $pids) {
    if (-not $procId -or $procId -eq 0) { continue }
    try {
      $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
      Write-Step "[stop] $Label PID=$procId ($($proc.ProcessName))"
      Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    } catch {}
  }
}

function Stop-MatchingProcesses([string]$Pattern, [string]$Label) {
  Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and ($_.CommandLine -match $Pattern) } |
    ForEach-Object {
      Write-Step "[stop] $Label PID=$($_.ProcessId)"
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}
