@echo off
setlocal

cd /d "%~dp0.."

echo [Build] Erzeuge Inno Setup Installer (offline)...
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\build_inno_offline_setup.ps1"
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [FEHLER] Inno Setup Build fehlgeschlagen. Exit-Code: %EXIT_CODE%
  exit /b %EXIT_CODE%
)

echo.
echo [OK] Setup.exe erfolgreich gebaut.
exit /b 0
