@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   Manifest Fallschirm – Entwicklungsstart
echo ============================================
echo.

REM In das Verzeichnis der Batch-Datei wechseln
cd /d "%~dp0"

set "PROJECT_ROOT=%CD%"
set "LOCAL_PYTHON=%PROJECT_ROOT%\runtime\python\python.exe"
set "VENV_PYTHON=%PROJECT_ROOT%\venv\Scripts\python.exe"
set "REQUIREMENTS_FILE=%PROJECT_ROOT%\requirements.txt"
set "WHEELHOUSE_DIR=%PROJECT_ROOT%\packages"
set "VENV_REBUILT=0"

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

REM Alte Python-Prozesse auf Port 5000 beenden (verhindert Doppelstart)
echo Pruefe auf laufende Flask-Instanzen...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr "0.0.0.0:5000"') do (
    taskkill /PID %%p /F >nul 2>&1
)
echo Alte Instanzen beendet (falls vorhanden).
echo.

REM Virtuelle Umgebung aktivieren (falls vorhanden)
if exist "venv\Scripts\activate.bat" (
    echo Aktiviere virtuelle Umgebung...
    call venv\Scripts\activate.bat
    echo Virtuelle Umgebung aktiviert.
    echo.
) else (
    echo Keine virtuelle Umgebung gefunden. Starte ohne venv.
    echo.
)

REM ============================================================
REM Admin-Passwörter für die Session
REM ============================================================

REM Voll-Admin (alle Funktionen)
set "MANIFEST_ADMIN_PASSWORD=OU74#"

REM Datenbank-Admin (nur Datenbank sichern / exportieren / laden)
set "MANIFEST_DB_ADMIN_PASSWORD=Richter24-1"

REM ============================================================
REM Lokale IPv4-Adresse ermitteln (für QR / Mobile Zugriff)
REM - nimmt die erste gefundene IPv4, die nicht 127.0.0.1 ist
REM - falls keine gefunden wird: leer lassen (App zeigt dann "kein Netzwerk")
REM ============================================================
set "MANIFEST_LOCAL_IP="

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4-Adresse" /c:"IPv4 Address"') do (
    set "IP=%%a"
    set "IP=!IP: =!"
    if not "!IP!"=="" if not "!IP!"=="127.0.0.1" (
        set "MANIFEST_LOCAL_IP=!IP!"
        goto :ip_found
    )
)

:ip_found
if "%MANIFEST_LOCAL_IP%"=="" (
    echo [INFO] Keine lokale IPv4-Adresse gefunden. Mobiler Zugriff ggf. nicht verfuegbar.
) else (
    echo [INFO] Lokale IPv4-Adresse erkannt: %MANIFEST_LOCAL_IP%
)

REM ============================================================
REM Flask-App setzen
REM ============================================================
set "MANIFEST_ENV=dev"
set "FLASK_APP=app"

REM Portbelegung pruefen: wenn bereits belegt, laeuft evtl. alter Prozess ohne aktuelle ENV
netstat -ano | findstr ":5000" | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo [WARNUNG] Port 5000 ist bereits belegt.
    echo [WARNUNG] Bitte vorhandenen Server zuerst beenden und dann dieses Skript erneut starten.
    echo [HINWEIS] Sonst werden geaenderte Admin-Passwoerter/ENV nicht uebernommen.
    pause
    exit /b 1
)

echo Starte Manifest-Server...
echo.

REM Flask im Hintergrund starten (explizit mit venv-Python)
start "Flask Server" cmd /k ""%VENV_PYTHON%" run.py"

REM Warten bis der Server wirklich lauscht
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
echo Server gestartet. Fenster kann offen bleiben.
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
