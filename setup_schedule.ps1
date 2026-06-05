# 重庆大学通知公告爬虫 - Windows 定时任务安装脚本
# 以管理员身份运行此脚本

$TaskName = "CQU_Crawler_Daily"
$ScriptPath = "D:\Program Files\cherry\DS Agent\run_crawler.bat"
$PythonPath = "C:\Users\karma\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$CrawlerPath = "D:\Program Files\cherry\DS Agent\cqu_crawler.py"

Write-Host "正在设置重庆大学通知公告爬虫定时任务..." -ForegroundColor Cyan

# 先测试爬虫能否正常运行
Write-Host "测试爬虫运行..." -ForegroundColor Yellow
& $PythonPath $CrawlerPath

if ($LASTEXITCODE -ne 0) {
    Write-Host "爬虫测试失败，请检查错误信息" -ForegroundColor Red
    exit 1
}

Write-Host "爬虫测试通过！" -ForegroundColor Green

# 创建定时任务 - 每天早上8:30运行
$Action = New-ScheduledTaskAction -Execute $ScriptPath
$Trigger = New-ScheduledTaskTrigger -Daily -At "08:30"
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$Principal = New-ScheduledTaskPrincipal -UserId "karma" -LogonType S4U -RunLevel Limited

try {
    Register-ScheduledTask -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description "重庆大学多站点通知公告每日自动抓取" `
        -Force

    Write-Host "`n定时任务创建成功！" -ForegroundColor Green
    Write-Host "任务名称: $TaskName" -ForegroundColor White
    Write-Host "执行时间: 每天 08:30" -ForegroundColor White
    Write-Host "执行脚本: $ScriptPath" -ForegroundColor White
    Write-Host "`n可通过「任务计划程序」查看和管理此任务" -ForegroundColor Cyan
} catch {
    Write-Host "`n定时任务创建失败: $_" -ForegroundColor Red
    Write-Host "`n请以管理员身份运行此脚本" -ForegroundColor Yellow
    Write-Host "或在「任务计划程序」中手动创建任务：" -ForegroundColor Yellow
    Write-Host "  1. 打开「任务计划程序」" -ForegroundColor Gray
    Write-Host "  2. 创建基本任务" -ForegroundColor Gray
    Write-Host "  3. 名称: CQU_Crawler_Daily" -ForegroundColor Gray
    Write-Host "  4. 触发器: 每天 08:30" -ForegroundColor Gray
    Write-Host "  5. 操作: 启动程序 -> $ScriptPath" -ForegroundColor Gray
}
