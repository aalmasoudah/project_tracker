@echo off
setlocal
cd /d "%~dp0"
title Insight Tracker - Local Launcher

echo Starting Insight Tracker, n8n, Telegram automation, and local services...
set "INSIGHT_ARGS="
if "%INSIGHT_NO_BROWSER%"=="1" set "INSIGHT_ARGS=-NoBrowser"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\restart_local_demo.ps1" %INSIGHT_ARGS%
set "INSIGHT_EXIT=%ERRORLEVEL%"

if not "%INSIGHT_EXIT%"=="0" (
  echo.
  echo Startup did not complete. Review the error above.
)

if not "%INSIGHT_NO_PAUSE%"=="1" (
  echo.
  echo Press any key to close this window. Running services will stay active.
  pause >nul
)

exit /b %INSIGHT_EXIT%
