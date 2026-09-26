# 鱼皮 AI 闯关小程序 - 一键启动开发环境
# 并行启动：后端 uvicorn 8000 + 前端 pnpm dev:weapp
# 使用方式：PowerShell 5+  .\scripts\start-dev.ps1

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendDir  = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$PyExe        = Join-Path $BackendDir ".venv\Scripts\python.exe"
$TmpDir       = Join-Path $ProjectRoot ".tmp"

if (-not (Test-Path $TmpDir)) { New-Item -ItemType Directory -Path $TmpDir -Force | Out-Null }
$env:TMP  = $TmpDir
$env:TEMP = $TmpDir

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  鱼皮 AI 闯关小程序 MVP 开发环境启动" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ---- 检查后端虚拟环境
if (-not (Test-Path $PyExe)) {
  Write-Host "[ERR] 后端虚拟环境不存在：$PyExe" -ForegroundColor Red
  Write-Host "      请先执行 README 第①步：" -ForegroundColor Yellow
  Write-Host "      cd backend ; C:\ruanjian\python3\python.exe -m venv .venv ; .\.venv\Scripts\Activate.ps1 ; pip install -r requirements.txt" -ForegroundColor Yellow
  exit 1
}

# ---- 检查前端 node_modules
$NodeModules = Join-Path $FrontendDir "node_modules"
if (-not (Test-Path $NodeModules)) {
  Write-Host "[WARN] 前端 node_modules 不存在，正在执行 pnpm install ..." -ForegroundColor Yellow
  Push-Location $FrontendDir
  try { pnpm install } catch {
    Write-Host "[ERR] pnpm install 失败，请手动执行 cd frontend ; pnpm install" -ForegroundColor Red
    Pop-Location
    exit 1
  }
  Pop-Location
}

Write-Host "[1/2] 启动后端 FastAPI (uvicorn 127.0.0.1:8000，USE_MOCK_LLM=true)" -ForegroundColor Green
$BackendJob = Start-Job -Name "FishAI-Backend" -ScriptBlock {
  param($BackendDir, $PyExe, $TmpDir)
  $env:TMP  = $TmpDir
  $env:TEMP = $TmpDir
  $env:USE_MOCK_LLM = "true"
  Set-Location $BackendDir
  & $PyExe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
} -ArgumentList $BackendDir, $PyExe, $TmpDir

Start-Sleep -Seconds 3
$bj = Get-Job -Name "FishAI-Backend"
if ($bj.State -eq "Running") {
  Write-Host "      后端启动成功 (JobId=$($bj.Id))" -ForegroundColor Green
} else {
  Write-Host "[WARN] 后端可能启动中，查看日志：Receive-Job -Id $($bj.Id)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2/2] 启动前端 Taro (pnpm dev:weapp)" -ForegroundColor Green
$FrontendJob = Start-Job -Name "FishAI-Frontend" -ScriptBlock {
  param($FrontendDir, $TmpDir)
  $env:TMP  = $TmpDir
  $env:TEMP = $TmpDir
  Set-Location $FrontendDir
  pnpm dev:weapp
} -ArgumentList $FrontendDir, $TmpDir

Start-Sleep -Seconds 5
$fj = Get-Job -Name "FishAI-Frontend"
if ($fj.State -eq "Running") {
  Write-Host "      前端启动成功 (JobId=$($fj.Id))" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  开发环境已启动！" -ForegroundColor Green
Write-Host "  后端：http://127.0.0.1:8000/api/v1/health" -ForegroundColor Gray
Write-Host "  前端：微信开发者工具导入 $FrontendDir\dist" -ForegroundColor Gray
Write-Host ""
Write-Host "  查看后端日志：Receive-Job -Id $($bj.Id) -Keep" -ForegroundColor Gray
Write-Host "  查看前端日志：Receive-Job -Id $($fj.Id) -Keep" -ForegroundColor Gray
Write-Host "  停止环境：    Stop-Job -Name FishAI-Backend,FishAI-Frontend ; Remove-Job -Name FishAI-Backend,FishAI-Frontend" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
