# 智能 AI 闯关小程序 - 前端单独启动（兼容旧路径）
# 推荐改用仓库根目录：
#   .\scripts\start-frontend.ps1
#   或一键：.\scripts\start-dev.ps1 / start-dev.bat

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
& "$RepoRoot\scripts\start-frontend.ps1" @args
