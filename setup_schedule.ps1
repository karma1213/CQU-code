# 重庆大学通知公告爬虫 - Windows 定时任务安装脚本
# 以管理员身份运行此脚本。所有路径自动取自本脚本所在目录。

$ErrorActionPreference = "Stop"

$Root       = $PSScriptRoot
if (-not $Root) { $Root = Split-Path -Parent $MyInvocation.MyCommand.Definition }
$TaskName   = "CQU_Crawler_Daily"
$ScriptPath = Join-Path $Root "run_crawler.bat"
$CrawlerPath= Join-Path $Root "cqu_crawler.py"

# Python：优先项目虚拟环境，其次 py -3，最后 python
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonPath = $VenvPython
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonPath = (Get-Command py).Source
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonPath = (Get-Command python).Source
} else {
    Write-Host "未找到 Python，请先安装 Python 3 或运行 install-cqu-code.bat" -ForegroundColor Red
    exit 1
}

Write-Host "项目目录: $Root" -ForegroundColor Cyan
Write-Host "Python  : $PythonPath" -ForegroundColor Cyan

foreach ($p in @($ScriptPath, $CrawlerPath)) {
    if (-not (Test-Path $p)) {
        Write-Host "缺少文件: $p" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n测试爬虫运行..." -ForegroundColor Yellow
if ($PythonPath -like "*\py.exe") {
    & $PythonPath -3 $CrawlerPath
} else {
    & $PythonPath $CrawlerPath
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "爬虫测试失败，请检查错误信息" -ForegroundColor Red
    exit 1
}
Write-Host "爬虫测试通过！" -ForegroundColor Green

# 当前登录用户，不再写死账号名
$CurrentUser = "$env:USERDOMAIN\$env:USERNAME"

$Action    = New-ScheduledTaskAction -Execute $ScriptPath -WorkingDirectory $Root
$Trigger   = New-ScheduledTaskTrigger -Daily -At "08:30"
$Settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$Principal = New-ScheduledTaskPrincipal -UserId $CurrentUser -LogonType S4U -RunLevel Limited

try {
    Register-ScheduledTask -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description "重庆大学多站点通知公告每日自动抓取" `
        -Force | Out-Null

    Write-Host "`n定时任务创建成功！" -ForegroundColor Green
    Write-Host "任务名称: $TaskName" -ForegroundColor White
    Write-Host "执行时间: 每天 08:30" -ForegroundColor White
    Write-Host "执行用户: $CurrentUser" -ForegroundColor White
    Write-Host "执行脚本: $ScriptPath" -ForegroundColor White
    Write-Host "`n可通过「任务计划程序」查看和管理此任务" -ForegroundColor Cyan
} catch {
    Write-Host "`n定时任务创建失败: $_" -ForegroundColor Red
    Write-Host "`n请以管理员身份运行此脚本" -ForegroundColor Yellow
    Write-Host "或在「任务计划程序」中手动创建任务：" -ForegroundColor Yellow
    Write-Host "  1. 打开「任务计划程序」" -ForegroundColor Gray
    Write-Host "  2. 创建基本任务" -ForegroundColor Gray
    Write-Host "  3. 名称: $TaskName" -ForegroundColor Gray
    Write-Host "  4. 触发器: 每天 08:30" -ForegroundColor Gray
    Write-Host "  5. 操作: 启动程序 -> $ScriptPath" -ForegroundColor Gray
}
