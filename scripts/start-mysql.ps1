#Requires -Version 5.1
<#
.SYNOPSIS
  Start local MySQL used by this project (default: C:\ruanjian\mysql).
.EXAMPLE
  .\scripts\start-mysql.ps1
#>
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"

Write-Host ""
Write-Step "==== Start MySQL ===="
if (Ensure-MysqlRunning) { exit 0 }
exit 1
