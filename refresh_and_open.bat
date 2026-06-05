@echo off
chcp 65001 >nul
echo 正在抓取重庆大学通知公告...
echo ----------------------------------------

"C:\Users\karma\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" "D:\Program Files\cherry\DS Agent\cqu_crawler.py"

echo ----------------------------------------
if %ERRORLEVEL% equ 0 (
    echo 抓取完成！正在打开页面...
    start "" "D:\Program Files\cherry\DS Agent\index.html"
) else (
    echo 抓取出错，请检查网络连接或重试
    pause
)
