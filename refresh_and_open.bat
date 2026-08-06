@echo off
setlocal
call "%~dp0_env.bat"

if not defined PY (
    echo No Python found. Run install-cqu-code.bat first.
    pause
    exit /b 1
)

"%PY%" %PY_ARGS% "%ROOT%\cqu_crawler.py"
set "RC=%ERRORLEVEL%"

if "%RC%"=="0" (
    start "" "%ROOT%\index.html"
) else (
    echo.
    echo Crawler failed with exit code %RC%.
    echo Run diagnose.bat to find out why.
    pause
)
endlocal & exit /b %RC%
