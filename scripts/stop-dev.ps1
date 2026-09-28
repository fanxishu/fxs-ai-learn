#Requires -Version 5.1
<#
.SYNOPSIS
  Stop local frontend/backend (and optionally MySQL) started for this project.
.PARAMETER IncludeMysql
  Also stop mysqld listening on 3306.
.EXAMPLE
  .\scripts\stop-dev.ps1
  .\scripts\stop-dev.ps1 -IncludeMysql
#>
param(
  [switch]$IncludeMysql
)

$ErrorActionPreference = 'Continue'
. "$PSScriptRoot\common.ps1"

Write-Host ""
Write-Step "==== Stop local services ===="

Stop-PortProcess -Port 8000 -Label 'backend:8000'
Stop-MatchingProcesses -Pattern 'uvicorn app\.main:app' -Label 'uvicorn'
Stop-MatchingProcesses -Pattern 'dev:weapp|@tarojs/cli|taro build --type weapp' -Label 'taro'

if ($IncludeMysql) {
  Stop-PortProcess -Port 3306 -Label 'mysql:3306'
  Stop-MatchingProcesses -Pattern 'mysqld\.exe' -Label 'mysqld'
}

Write-Ok "Done"
Write-Host ""
