@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   Manifest Fallschirm – PRODUKTIVSTART
echo   (Waitress + GUI + PDF + E-Mail)
echo ============================================
echo.

REM --------------------------------------------------
REM In Projektverzeichnis wechseln
REM --------------------------------------------------
cd /d "%~dp0"

set "DEV_MODE=0"
if /i "%1"=="--dev" (
    set "DEV_MODE=1"
    set "MANIFEST_ENV=dev"
)

set "PROJECT_ROOT=%CD%"
set "LOCAL_PYTHON=%PROJECT_ROOT%\runtime\python\python.exe"
set "PROJECT_VENV_DIR=%PROJECT_ROOT%\venv"
set "PROGRAMDATA_ROOT=%ProgramData%"
if "%PROGRAMDATA_ROOT%"=="" set "PROGRAMDATA_ROOT=C:\ProgramData"
set "INSTALLED_RUNTIME_HOME=%PROGRAMDATA_ROOT%\ManifestFallschirm"
set "INSTALLED_SECRETS_PATH=%INSTALLED_RUNTIME_HOME%\secrets\auth_config.json"

if exist "%INSTALLED_SECRETS_PATH%" (
    set "MANIFEST_RUNTIME_HOME=%INSTALLED_RUNTIME_HOME%"
    set "MANIFEST_SECRETS_PATH=%INSTALLED_SECRETS_PATH%"
) else (
    if not defined MANIFEST_RUNTIME_HOME set "MANIFEST_RUNTIME_HOME=%PROJECT_ROOT%"
    if not defined MANIFEST_SECRETS_PATH set "MANIFEST_SECRETS_PATH=%PROJECT_ROOT%\data\secrets\auth_config.json"
)

set "VENV_DIR=%MANIFEST_RUNTIME_HOME%\venv"
if /I "%MANIFEST_RUNTIME_HOME%"=="%PROJECT_ROOT%" set "VENV_DIR=%PROJECT_ROOT%\venv"
set "REQUIREMENTS_FILE=%PROJECT_ROOT%\requirements.txt"
set "WHEELHOUSE_DIR=%PROJECT_ROOT%\packages"
set "INSTALL_SECRETS_SCRIPT=%PROJECT_ROOT%\tools\license\install_runtime_secrets.py"
set "SECRETS_PATH="
set "LICENSE_KEY_INPUT="
set "ADMIN_PASSWORD_INPUT="
set "DB_ADMIN_PASSWORD_INPUT="
set "VENV_REBUILT=0"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
if exist "%VENV_DIR%\Scripts\python.exe" (
    set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
)
set "SECRETS_PATH=%MANIFEST_SECRETS_PATH%"

if not exist "%MANIFEST_RUNTIME_HOME%" (
    mkdir "%MANIFEST_RUNTIME_HOME%" >nul 2>&1
)

REM --------------------------------------------------
REM Virtuelle Umgebung prüfen
REM --------------------------------------------------
call :ensure_venv
if errorlevel 1 (
    pause
    exit /b
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

REM --------------------------------------------------
REM Runtime-Secrets pruefen/erzeugen (Produktivbetrieb)
REM --------------------------------------------------
if /I not "%MANIFEST_ENV%"=="dev" (
    if not exist "%SECRETS_PATH%" (
        echo [WARNUNG] Secrets-Datei fehlt: %SECRETS_PATH%
        call :provision_runtime_secrets
        if errorlevel 1 (
            pause
            exit /b 1
        )
    )
)

REM --------------------------------------------------
REM Klare Ausgabe: welches Python wird genutzt
REM --------------------------------------------------
echo Verwende Python aus virtueller Umgebung:
"%VENV_PYTHON%" --version
echo.

REM --------------------------------------------------
REM Manifest Launcher starten (Waitress)
REM - Admin / ENV / GTK / Logging kommt aus manifest_launcher.py
REM --------------------------------------------------
REM DEV-MODUS: Wenn MANIFEST_ENV=dev gesetzt ist (oder --dev uebergeben wird),
REM            wird die Lizenz-/Secrets-Pruefung uebersprungen.
REM --------------------------------------------------
if /i "%1"=="--dev" set "MANIFEST_ENV=dev"
if /i "%MANIFEST_ENV%"=="dev" (
    echo [DEV] Starte im Entwicklermodus – Lizenzpruefung deaktiviert
    set "MANIFEST_ENV=dev"
    set "MANIFEST_ADMIN_PASSWORD=OU74#"
    set "MANIFEST_DB_ADMIN_PASSWORD=Richter24-1"
    set "FLASK_DEBUG=0"
    set "PYTHONUNBUFFERED=1"
    echo.
)

echo Starte Manifest (Waitress)...
echo.

REM --------------------------------------------------
REM Lokale IPv4-Adresse ermitteln (fuer QR / Mobile Zugriff)
REM --------------------------------------------------
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
if "!MANIFEST_LOCAL_IP!"=="" (
    echo [INFO] Keine lokale IPv4-Adresse gefunden. Mobiler Zugriff ggf. nicht verfuegbar.
) else (
    echo [INFO] Lokale IPv4-Adresse erkannt: !MANIFEST_LOCAL_IP!
)
echo.

set "APP_ENTRY=manifest_launcher.py"
if exist "manifest_launcher.pyc" (
    set "APP_ENTRY=manifest_launcher.pyc"
)

"%VENV_PYTHON%" "%APP_ENTRY%"
set "EXITCODE=%ERRORLEVEL%"

echo.
echo Manifest wurde beendet.
pause
exit /b %EXITCODE%

:provision_runtime_secrets
if not exist "%INSTALL_SECRETS_SCRIPT%" (
    echo [FEHLER] Setup-Skript fuer Runtime-Secrets fehlt:
    echo         %INSTALL_SECRETS_SCRIPT%
    exit /b 1
)

echo.
echo ============================================
echo   Einmalige Erstkonfiguration (Lizenz)
echo ============================================
echo.
echo Bitte Lizenzschluessel und Passwoerter eingeben.
echo [HINWEIS] Die Eingabe ist im CMD-Fenster sichtbar.
echo.

set "LICENSE_KEY_INPUT="
set /p "LICENSE_KEY_INPUT=Lizenzschluessel: "
if "%LICENSE_KEY_INPUT%"=="" (
    echo [FEHLER] Lizenzschluessel darf nicht leer sein.
    exit /b 1
)

set "ADMIN_PASSWORD_INPUT="
set /p "ADMIN_PASSWORD_INPUT=Admin-Passwort: "
if "%ADMIN_PASSWORD_INPUT%"=="" (
    echo [FEHLER] Admin-Passwort darf nicht leer sein.
    exit /b 1
)

set "DB_ADMIN_PASSWORD_INPUT="
set /p "DB_ADMIN_PASSWORD_INPUT=DB-Admin-Passwort: "
if "%DB_ADMIN_PASSWORD_INPUT%"=="" (
    echo [FEHLER] DB-Admin-Passwort darf nicht leer sein.
    exit /b 1
)

echo.
echo [INFO] Erzeuge Runtime-Secrets ...
"%VENV_PYTHON%" "%INSTALL_SECRETS_SCRIPT%" --license-key "%LICENSE_KEY_INPUT%" --admin-password "%ADMIN_PASSWORD_INPUT%" --db-admin-password "%DB_ADMIN_PASSWORD_INPUT%"
if errorlevel 1 (
    echo [FEHLER] Runtime-Secrets konnten nicht erzeugt werden.
    exit /b 1
)

if not exist "%SECRETS_PATH%" (
    echo [FEHLER] Secrets-Datei wurde nicht erstellt: %SECRETS_PATH%
    exit /b 1
)

echo [OK] Runtime-Secrets erstellt: %SECRETS_PATH%
echo.
exit /b 0

:ensure_venv
if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" --version >nul 2>&1
    if not errorlevel 1 exit /b 0
    echo [WARNUNG] Vorhandene venv ist ungueltig. Erzeuge venv neu ...
) else (
    echo [WARNUNG] Virtuelle Umgebung nicht gefunden. Erzeuge venv neu ...
)

if not exist "%LOCAL_PYTHON%" (
    echo [FEHLER] Lokale Python-Runtime fehlt:
    echo         %LOCAL_PYTHON%
    echo [HINWEIS] Erwartet wird runtime\python\python.exe im Projektordner.
    exit /b 1
)

if exist "%VENV_DIR%" (
    rmdir /s /q "%VENV_DIR%"
)

"%LOCAL_PYTHON%" -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [FEHLER] venv konnte nicht erstellt werden: "%VENV_DIR%"
        echo [HINWEIS] Bitte Schreibrechte auf den Zielordner pruefen.
        exit /b 1
    )
set "VENV_REBUILT=1"

"%VENV_PYTHON%" --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python in der venv ist nicht funktionsfaehig.
    exit /b 1
)
exit /b 0