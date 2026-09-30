@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Fingerprint ermitteln.ps1"
if errorlevel 1 (
  echo.
  echo [FEHLER] Fingerprint konnte nicht ermittelt werden.
  pause
  exit /b 1
)
echo.
pause