@echo off
setlocal

echo ============================================
echo   Manifest Fallschirm – Entwicklungsstart
echo ============================================
echo.

REM --------------------------------------------------
REM In Projektverzeichnis wechseln
REM --------------------------------------------------
cd /d "%~dp0"

REM --------------------------------------------------
REM Python/venv robust prüfen (ohne PATH-Abhaengigkeit)
REM --------------------------------------------------
set "PROJECT_ROOT=%CD%"
set "LOCAL_PYTHON=%PROJECT_ROOT%\runtime\python\python.exe"
set "VENV_PYTHON=%PROJECT_ROOT%\venv\Scripts\python.exe"
set "REQUIREMENTS_FILE=%PROJECT_ROOT%\requirements.txt"
set "WHEELHOUSE_DIR=%PROJECT_ROOT%\packages"
set "VENV_REBUILT=0"

REM --------------------------------------------------
REM Virtuelle Umgebung sicherstellen (DEV!)
REM --------------------------------------------------
call :ensure_venv
if errorlevel 1 (
    pause
    exit /b 1
)

if "%VENV_REBUILT%"=="1" (
    echo [INFO] Installiere Offline-Abhaengigkeiten aus packages ...
    if not exist "%REQUIREMENTS_FILE%" (
        echo [FEHLER] requirements.txt nicht gefunden: %REQUIREMENTS_FILE%
        pause
        exit /b 1
    )
    if not exist "%WHEELHOUSE_DIR%" (
        echo [FEHLER] packages-Ordner fehlt: %WHEELHOUSE_DIR%
        pause
        exit /b 1
    )
    "%VENV_PYTHON%" -m pip install --no-index --find-links "%WHEELHOUSE_DIR%" -r "%REQUIREMENTS_FILE%"
    if errorlevel 1 (
        echo [FEHLER] Offline-Abhaengigkeiten konnten nicht installiert werden.
        pause
        exit /b 1
    )
)

echo Verwende Python aus virtueller Umgebung:
"%VENV_PYTHON%" --version
echo.

REM --------------------------------------------------
REM DEV-Environment setzen (wichtig!)
REM --------------------------------------------------
set MANIFEST_ENV=dev
set MANIFEST_ADMIN_PASSWORD=OU74#
set MANIFEST_DB_ADMIN_PASSWORD=Richter24-1
set FLASK_ENV=development
set FLASK_DEBUG=1
set MANIFEST_WERKZEUG_LOG_LEVEL=INFO
set MANIFEST_REQUEST_LOG_CONSOLE=1
set PYTHONUNBUFFERED=1

REM --------------------------------------------------
REM Flask im DEV-Modus starten (WICHTIG!)
REM NICHT flask run verwenden!
REM --------------------------------------------------
echo Starte Flask Development Server...
echo.

start "Flask DEV Server" cmd /k ""%VENV_PYTHON%" run.py"

REM --------------------------------------------------
REM Warten bis der Server wirklich lauscht, dann Browser öffnen
REM --------------------------------------------------
set "WAIT_SECONDS=15"
set /a ELAPSED=0

:wait_for_server
netstat -ano | findstr ":5000" | findstr "LISTENING" >nul
if not errorlevel 1 goto :open_browser

if %ELAPSED% GEQ %WAIT_SECONDS% goto :timeout_browser

timeout /t 1 >nul
set /a ELAPSED+=1
goto :wait_for_server

:open_browser
start "" http://127.0.0.1:5000/pwa
goto :after_browser

:timeout_browser
echo [WARNUNG] Server war nach %WAIT_SECONDS% Sekunden noch nicht erreichbar.
echo [HINWEIS] Browser wird nicht automatisch geoeffnet. Bitte Serverfenster pruefen.

:after_browser

echo.
echo DEV-Server gestartet.
pause
exit /b 0

:ensure_venv
if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" --version >nul 2>&1
    if not errorlevel 1 exit /b 0
    echo [WARNUNG] Vorhandene venv ist ungueltig. Erzeuge venv neu ...
) else (
    echo [WARNUNG] Keine gueltige venv gefunden. Erzeuge venv aus lokaler Runtime ...
)

if not exist "%LOCAL_PYTHON%" (
    echo [FEHLER] Weder venv noch lokale Runtime gefunden.
    echo Erwartet: venv\Scripts\python.exe oder runtime\python\python.exe
    exit /b 1
)

if exist "%PROJECT_ROOT%\venv" (
    rmdir /s /q "%PROJECT_ROOT%\venv"
)

"%LOCAL_PYTHON%" -m venv "%PROJECT_ROOT%\venv"
if errorlevel 1 (
    echo [FEHLER] venv konnte nicht erstellt werden.
    exit /b 1
)
set "VENV_REBUILT=1"

"%VENV_PYTHON%" --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python in der venv ist nicht funktionsfaehig.
    exit /b 1
)
exit /b 0