@echo off
setlocal
call "%~dp0_env.bat"

if not defined PY (
    echo No Python found. Run install-cqu-code.bat first.
    pause
    exit /b 1
)

"%PY%" %PY_ARGS% "%ROOT%\diagnose_sources.py" --browser
echo.
echo Results are in the diag\ folder (report.txt + raw pages).
pause
endlocal
