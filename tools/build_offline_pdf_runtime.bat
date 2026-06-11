@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."
set "PROJECT_ROOT=%CD%"
set "TARGET_GTK=%PROJECT_ROOT%\runtime\gtk"
set "ARCHIVE=%PROJECT_ROOT%\runtime\gtk-runtime-win64.zip"

set "SRC1=%ProgramFiles%\GTK3-Runtime Win64"
set "SRC2=%ProgramFiles%\GTK3 Runtime Win64"
set "SRC3=%ProgramFiles(x86)%\GTK3-Runtime Win64"
set "SRC4=%ProgramFiles(x86)%\GTK3 Runtime Win64"
set "SRC="

if exist "%SRC1%\bin\libcairo-2.dll" set "SRC=%SRC1%"
if not defined SRC if exist "%SRC2%\bin\libcairo-2.dll" set "SRC=%SRC2%"
if not defined SRC if exist "%SRC3%\bin\libcairo-2.dll" set "SRC=%SRC3%"
if not defined SRC if exist "%SRC4%\bin\libcairo-2.dll" set "SRC=%SRC4%"

if not defined SRC (
  echo [FEHLER] Keine lokale GTK3-Runtime gefunden.
  echo [HINWEIS] Erwartet unter "Program Files\GTK3-Runtime Win64".
  exit /b 1
)

echo [INFO] Quelle: %SRC%

if exist "%TARGET_GTK%" (
  rmdir /s /q "%TARGET_GTK%"
)

xcopy "%SRC%\*" "%TARGET_GTK%\" /E /I /Y >nul
if errorlevel 1 (
  echo [FEHLER] Kopieren der GTK-Runtime fehlgeschlagen.
  exit /b 1
)

if not exist "%TARGET_GTK%\bin\libcairo-2.dll" (
  echo [FEHLER] runtime\gtk\bin ist unvollstaendig.
  exit /b 1
)

echo [OK] Laufzeit kopiert nach runtime\gtk

if exist "%ARCHIVE%" del /f /q "%ARCHIVE%" >nul 2>&1

tar -a -c -f "%ARCHIVE%" -C "%PROJECT_ROOT%\runtime" gtk
if errorlevel 1 (
  echo [WARNUNG] ZIP-Archiv konnte nicht erstellt werden.
  echo [HINWEIS] runtime\gtk ist dennoch vorhanden und nutzbar.
  exit /b 0
)

echo [OK] Offline-Archiv erstellt: %ARCHIVE%
exit /b 0
