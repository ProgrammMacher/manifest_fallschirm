@echo off
setlocal

cd /d "%~dp0"
echo ============================================
echo   MANIFeST OU - Maschinen-Fingerprint
echo ============================================
echo.

set "FINGERPRINT="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "get_machine_fingerprint.ps1"`) do (
	set "FINGERPRINT=%%i"
)

if not defined FINGERPRINT (
	echo [FEHLER] Kein Fingerprint ermittelt.
	echo Bitte PowerShell-Ausfuehrung pruefen.
	echo.
	pause
	exit /b 1
)

echo Fingerprint:
echo %FINGERPRINT%
echo.
echo Hinweis: Diese Zeile komplett kopieren und an den Lizenzgeber senden.
echo.
pause
