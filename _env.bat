@echo off
rem Shared environment resolver for the CQU scripts.
rem Sets ROOT (this repo's folder), PY (executable), and PY_ARGS.
rem Callers do: call "%~dp0_env.bat" then use %ROOT%, %PY%, and %PY_ARGS%.

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "PY="
set "PY_ARGS="
if exist "%ROOT%\.venv\Scripts\python.exe" set "PY=%ROOT%\.venv\Scripts\python.exe"
if not defined PY (
  where py >nul 2>&1
  if not errorlevel 1 (
    set "PY=py"
    set "PY_ARGS=-3"
  )
)
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)
exit /b 0
