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

set "INSTALL_SECRETS_SCRIPT=%PROJECT_ROOT%\tools\license\install_runtime_secrets.py"
set "SECRETS_PATH=%MANIFEST_SECRETS_PATH%"
set "LICENSE_KEY_INPUT="
set "ADMIN_PASSWORD_INPUT="
set "ADMIN_PASSWORD_CONFIRM_INPUT="
set "DB_ADMIN_PASSWORD_INPUT="
set "DB_ADMIN_PASSWORD_CONFIRM_INPUT="

if not exist "%MANIFEST_RUNTIME_HOME%" (
    mkdir "%MANIFEST_RUNTIME_HOME%" >nul 2>&1
)

REM --------------------------------------------------
REM Lokale Python-Runtime pruefen (enthaelt bereits alle Abhaengigkeiten,
REM kein separater venv-Schritt unter Program Files noetig/erlaubt)
REM --------------------------------------------------
if not exist "%LOCAL_PYTHON%" (
    echo [FEHLER] Lokale Python-Runtime fehlt:
    echo         %LOCAL_PYTHON%
    echo [HINWEIS] Erwartet wird runtime\python\python.exe im Projektordner.
    pause
    exit /b 1
)

"%LOCAL_PYTHON%" -c "import flask, sqlalchemy, requests, waitress, cryptography, werkzeug" >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Mindestens ein Kernmodul fehlt in der mitgelieferten Runtime.
    echo [HINWEIS] Die Installation ist unvollstaendig. Bitte MANIFeST OU neu installieren.
    pause
    exit /b 1
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
echo Verwende Python aus der mitgelieferten Runtime:
"%LOCAL_PYTHON%" --version
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

"%LOCAL_PYTHON%" "%APP_ENTRY%"
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
set "ADMIN_PASSWORD_CONFIRM_INPUT="
set /p "ADMIN_PASSWORD_CONFIRM_INPUT=Admin-Passwort wiederholen: "
if "%ADMIN_PASSWORD_INPUT%"=="" (
    echo [FEHLER] Admin-Passwort darf nicht leer sein.
    exit /b 1
)
if not "%ADMIN_PASSWORD_INPUT%"=="%ADMIN_PASSWORD_CONFIRM_INPUT%" (
    echo [FEHLER] Die beiden Eingaben fuer das Admin-Passwort stimmen nicht ueberein.
    exit /b 1
)

set "DB_ADMIN_PASSWORD_INPUT="
set /p "DB_ADMIN_PASSWORD_INPUT=DB-Admin-Passwort: "
set "DB_ADMIN_PASSWORD_CONFIRM_INPUT="
set /p "DB_ADMIN_PASSWORD_CONFIRM_INPUT=DB-Admin-Passwort wiederholen: "
if "%DB_ADMIN_PASSWORD_INPUT%"=="" (
    echo [FEHLER] DB-Admin-Passwort darf nicht leer sein.
    exit /b 1
)
if not "%DB_ADMIN_PASSWORD_INPUT%"=="%DB_ADMIN_PASSWORD_CONFIRM_INPUT%" (
    echo [FEHLER] Die beiden Eingaben fuer das DB-Admin-Passwort stimmen nicht ueberein.
    exit /b 1
)

echo.
echo [INFO] Erzeuge Runtime-Secrets ...
set "MANIFEST_INSTALL_LICENSE_KEY=%LICENSE_KEY_INPUT%"
set "MANIFEST_INSTALL_ADMIN_PASSWORD=%ADMIN_PASSWORD_INPUT%"
set "MANIFEST_INSTALL_ADMIN_PASSWORD_CONFIRM=%ADMIN_PASSWORD_CONFIRM_INPUT%"
set "MANIFEST_INSTALL_DB_ADMIN_PASSWORD=%DB_ADMIN_PASSWORD_INPUT%"
set "MANIFEST_INSTALL_DB_ADMIN_PASSWORD_CONFIRM=%DB_ADMIN_PASSWORD_CONFIRM_INPUT%"
"%LOCAL_PYTHON%" "%INSTALL_SECRETS_SCRIPT%" --secrets-path "%SECRETS_PATH%"
set "SECRETS_EXITCODE=%ERRORLEVEL%"
set "MANIFEST_INSTALL_LICENSE_KEY="
set "MANIFEST_INSTALL_ADMIN_PASSWORD="
set "MANIFEST_INSTALL_ADMIN_PASSWORD_CONFIRM="
set "MANIFEST_INSTALL_DB_ADMIN_PASSWORD="
set "MANIFEST_INSTALL_DB_ADMIN_PASSWORD_CONFIRM="
set "LICENSE_KEY_INPUT="
set "ADMIN_PASSWORD_INPUT="
set "ADMIN_PASSWORD_CONFIRM_INPUT="
set "DB_ADMIN_PASSWORD_INPUT="
set "DB_ADMIN_PASSWORD_CONFIRM_INPUT="
if not "%SECRETS_EXITCODE%"=="0" (
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
