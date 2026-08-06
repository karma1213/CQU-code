@echo off
rem Scheduled-task entry point: crawl only, no browser.
setlocal
call "%~dp0_env.bat"

if not defined PY (
    echo No Python found.
    exit /b 1
)

"%PY%" %PY_ARGS% "%ROOT%\cqu_crawler.py"
endlocal & exit /b %ERRORLEVEL%
