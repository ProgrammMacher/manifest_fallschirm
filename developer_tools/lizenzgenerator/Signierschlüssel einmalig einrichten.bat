@echo off
setlocal
cd /d "%~dp0"
set "PROJECT_ROOT=%~dp0..\.."
set "PYTHON=%PROJECT_ROOT%\venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo [FEHLER] Projekt-venv nicht gefunden: %PYTHON%
  pause
  exit /b 1
)
"%PYTHON%" "%~dp0initialize_signing_key.py"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" pause
exit /b %RC%