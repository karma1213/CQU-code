@echo off
setlocal
rem Stop only the CQU notice/news server process trees.
rem This script intentionally does not kill every python.exe process.

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$targets = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('python.exe','pythonw.exe') -and $_.CommandLine -match '(?i)(notice_server\.py|news_server\.py)' });" ^
  "$targetIds = @($targets | ForEach-Object { $_.ProcessId });" ^
  "$roots = @($targets | Where-Object { $targetIds -notcontains $_.ParentProcessId });" ^
  "foreach ($target in $roots) { taskkill.exe /PID $target.ProcessId /T /F }"

if errorlevel 1 (
    echo Failed to stop CQU Notice Hub services.
    exit /b 1
)
echo CQU Notice Hub services stopped.
endlocal
