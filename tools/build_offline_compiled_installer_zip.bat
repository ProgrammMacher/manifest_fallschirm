@echo off
setlocal

cd /d "%~dp0.."

echo [Build] Erzeuge COMPILED Offline-Installer-ZIP aus Projektordner...
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\build_offline_compiled_installer_zip.ps1"
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [FEHLER] Compiled-Build fehlgeschlagen. Exit-Code: %EXIT_CODE%
  exit /b %EXIT_CODE%
)

echo.
echo [OK] Compiled-Build erfolgreich.
exit /b 0