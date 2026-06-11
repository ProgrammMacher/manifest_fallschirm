@echo off
setlocal

cd /d "%~dp0"

echo ============================================
echo   Manifest Fallschirm - WAITRESS DEV START
echo ============================================
echo.

echo [INFO] Starte portablen Dev-Modus mit Waitress...
call "%~dp0start_manifest_prod.bat" --dev
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [INFO] Waitress Dev-Start beendet.
) else (
  echo [WARNUNG] Waitress Dev-Start mit Exit-Code %EXITCODE% beendet.
)

exit /b %EXITCODE%
