@echo off
echo ============================================
echo   Manifest Fallschirm - Flask Neustart
echo ============================================
echo.

REM In das Verzeichnis dieser Batch-Datei wechseln
cd /D "%~dp0"

set "PROJECT_ROOT=%CD%"
set "LOCAL_PYTHON=%PROJECT_ROOT%\runtime\python\python.exe"
set "VENV_PYTHON=%PROJECT_ROOT%\venv\Scripts\python.exe"
set "REQUIREMENTS_FILE=%PROJECT_ROOT%\requirements.txt"
set "WHEELHOUSE_DIR=%PROJECT_ROOT%\packages"
set "VENV_REBUILT=0"
set "MANIFEST_ENV=dev"

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

echo Beende laufenden Flask-Server...
taskkill /IM python.exe /F >nul 2>&1

echo Loesche Session-Daten...
del "app\session_data\*" /Q >nul 2>&1

echo Starte Flask neu...
"%VENV_PYTHON%" -m flask run
exit /b %ERRORLEVEL%

:ensure_venv
if exist "%VENV_PYTHON%" (
	"%VENV_PYTHON%" --version >nul 2>&1
	if not errorlevel 1 exit /b 0
	echo [WARNUNG] Vorhandene venv ist ungueltig. Erzeuge venv neu ...
) else (
	echo [WARNUNG] Keine gueltige venv gefunden. Erzeuge venv aus lokaler Runtime ...
)

if not exist "%LOCAL_PYTHON%" (
	echo [FEHLER] Lokale Runtime fehlt: %LOCAL_PYTHON%
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
