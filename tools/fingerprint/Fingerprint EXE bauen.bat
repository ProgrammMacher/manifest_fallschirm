@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_fingerprint_exe.ps1"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [FEHLER] EXE-Build fehlgeschlagen.
  pause
  exit /b %RC%
)
echo Build abgeschlossen.
echo EXE: build\fingerprint\dist\MANIFeST_Rechnerkennung.exe
echo Weitergabe nur per Download-Link, siehe README.txt in diesem Ordner.
pause
exit /b %RC%
