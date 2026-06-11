@echo off
setlocal EnableExtensions EnableDelayedExpansion

title MANIFeST OU - Setup und Start

echo ============================================
echo   MANIFeST OU - Setup und Start
echo ============================================
echo.

REM Immer im Projektordner starten (Ordner der .bat)
cd /d "%~dp0"

set "PROJECT_ROOT=%CD%"
set "LOCAL_PYTHON=%PROJECT_ROOT%\runtime\python\python.exe"
set "PROJECT_VENV_DIR=%PROJECT_ROOT%\venv"
set "VENV_DIR=%PROJECT_VENV_DIR%"
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
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "REQUIREMENTS_FILE=%PROJECT_ROOT%\requirements.txt"
set "APP_ENTRY_PY=%PROJECT_ROOT%\manifest_launcher.py"
set "APP_ENTRY_PYC=%PROJECT_ROOT%\manifest_launcher.pyc"
set "APP_ENTRY="
set "WHEELHOUSE_DIR=%PROJECT_ROOT%\packages"

echo [INFO] Projektordner: %PROJECT_ROOT%
echo [INFO] Runtime-Home: %MANIFEST_RUNTIME_HOME%
echo [INFO] venv-Zielordner: %VENV_DIR%
echo.

if not exist "%MANIFEST_RUNTIME_HOME%" (
  mkdir "%MANIFEST_RUNTIME_HOME%" >nul 2>&1
)

REM --------------------------------------------------
REM 1) Lokale Python-Runtime pruefen
REM --------------------------------------------------
if not exist "%LOCAL_PYTHON%" (
  echo [FEHLER] Lokale Python-Runtime fehlt:
  echo         %LOCAL_PYTHON%
  echo [HINWEIS] Erwartet wird runtime\python\python.exe im Projektordner.
  pause
  exit /b 1
)

echo [OK] Lokale Python-Runtime gefunden: %LOCAL_PYTHON%

REM --------------------------------------------------
REM 2) Virtuelle Umgebung erstellen (falls nicht vorhanden)
REM --------------------------------------------------
if not exist "%VENV_PYTHON%" (
  echo [INFO] Erstelle virtuelle Umgebung in "%VENV_DIR%" ...
  "%LOCAL_PYTHON%" -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [FEHLER] venv konnte nicht erstellt werden.
    echo [HINWEIS] Bitte Schreibrechte auf den Zielordner pruefen.
    pause
    exit /b 1
  )
  echo [OK] venv erstellt.
) else (
  "%VENV_PYTHON%" --version >nul 2>&1
  if errorlevel 1 (
    echo [WARNUNG] Vorhandene venv ist ungueltig. Erzeuge venv neu ...
    rmdir /s /q "%VENV_DIR%"
    "%LOCAL_PYTHON%" -m venv "%VENV_DIR%"
    if errorlevel 1 (
      echo [FEHLER] venv konnte am Projektort nicht neu erstellt werden.
      echo [HINWEIS] Bitte Schreibrechte auf "%PROJECT_VENV_DIR%" pruefen.
      pause
      exit /b 1
    )
    echo [OK] venv wurde neu erstellt.
  ) else (
    echo [OK] venv bereits vorhanden.
  )
)

echo.

REM --------------------------------------------------
REM 4) requirements installieren
REM --------------------------------------------------
if not exist "%REQUIREMENTS_FILE%" (
  echo [FEHLER] requirements.txt nicht gefunden unter:
  echo         %REQUIREMENTS_FILE%
  pause
  exit /b 1
)

if not exist "%WHEELHOUSE_DIR%" (
  echo [FEHLER] Lokaler Paketordner fehlt:
  echo         %WHEELHOUSE_DIR%
  echo [HINWEIS] Fuer autarke Installation muss der Ordner packages mitgeliefert werden.
  pause
  exit /b 1
)

dir /b "%WHEELHOUSE_DIR%\*.whl" >nul 2>&1
if errorlevel 1 (
  echo [FEHLER] Keine Wheel-Dateien im Ordner packages gefunden.
  echo [HINWEIS] Erwartet: %WHEELHOUSE_DIR%\*.whl
  pause
  exit /b 1
)

echo [INFO] Installiere Abhaengigkeiten strikt offline aus packages ...
"%VENV_PYTHON%" -m pip install --no-index --find-links "%WHEELHOUSE_DIR%" -r "%REQUIREMENTS_FILE%"
if errorlevel 1 (
  echo [FEHLER] Offline-Installation aus packages fehlgeschlagen.
  pause
  exit /b 1
)
echo [OK] Offline-Abhaengigkeiten installiert.

echo.

REM --------------------------------------------------
REM 4b) Preflight fuer benoetigte Kernmodule
REM --------------------------------------------------
echo [INFO] Pruefe Kernmodule (Flask/SQLAlchemy/Requests/Waitress) ...
"%VENV_PYTHON%" -c "import flask, sqlalchemy, requests, waitress"
if errorlevel 1 (
  echo [FEHLER] Mindestens ein Kernmodul fehlt in der venv.
  echo [HINWEIS] Pruefe den Inhalt von packages und requirements.txt.
  pause
  exit /b 1
)
echo [OK] Kernmodule verfuegbar.

echo.
echo [INFO] Versuche Offline-Selbstheilung fuer PDF-Runtime (GTK/Cairo/Pango) ...
"%VENV_PYTHON%" -c "from app.helpers.pdf_runtime import ensure_weasyprint_pdf_runtime; ok, msg = ensure_weasyprint_pdf_runtime(); print('[OK] ' + msg if ok else '[WARNUNG] ' + msg)"

echo.
echo [INFO] Pruefe PDF-Runtime (WeasyPrint + native Bibliotheken) ...
"%VENV_PYTHON%" -c "from weasyprint import HTML; HTML(string='<h1>ok</h1>').write_pdf()"
if errorlevel 1 (
  echo [WARNUNG] WeasyPrint ist installiert, aber native Bibliotheken fehlen oder sind nicht ladbar.
  echo [HINWEIS] PDF-Export wird auf diesem Rechner fehlschlagen (loads/statistics/report.pdf, billing/invoices/pdf).
  echo [HINWEIS] Erwartet wird eine lokale GTK/Cairo/Pango-Runtime unter third_party\gtk\bin oder runtime\gtk\bin.
) else (
  echo [OK] PDF-Runtime verfuegbar.
)

echo.

REM --------------------------------------------------
REM 5) App starten
REM --------------------------------------------------
if exist "%APP_ENTRY_PYC%" (
  set "APP_ENTRY=%APP_ENTRY_PYC%"
) else if exist "%APP_ENTRY_PY%" (
  set "APP_ENTRY=%APP_ENTRY_PY%"
)

if "%APP_ENTRY%"=="" (
  echo [FEHLER] Einstiegsskript nicht gefunden (weder .pyc noch .py):
  echo         %APP_ENTRY_PYC%
  echo         %APP_ENTRY_PY%
  pause
  exit /b 1
)

echo [INFO] Starte App ueber %APP_ENTRY% ...
echo [HINWEIS] Dieses Fenster bleibt aktiv, solange die App laeuft.
echo.

"%VENV_PYTHON%" "%APP_ENTRY%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [INFO] App wurde normal beendet.
) else (
  echo [WARNUNG] App wurde mit Exit-Code %EXITCODE% beendet.
)

pause
exit /b %EXITCODE%
