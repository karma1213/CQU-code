@echo off
chcp 65001 >nul
echo 重庆大学通知公告爬虫 - 每日自动更新
echo 开始时间: %date% %time%

"C:\Users\karma\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" "D:\Program Files\cherry\DS Agent\cqu_crawler.py"

echo 完成时间: %date% %time%
echo.
