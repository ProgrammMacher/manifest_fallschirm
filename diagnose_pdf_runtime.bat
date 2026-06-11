@echo off
setlocal EnableExtensions

cd /d "%~dp0"
set "PROJECT_ROOT=%CD%"
set "LOG_DIR=%PROGRAMDATA%\ManifestFallschirm\logs"
set "LOG_FILE=%LOG_DIR%\pdf_runtime_diagnose.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH:mm:ss"') do set "RUN_TS=%%i"
if not defined RUN_TS set "RUN_TS=%DATE%_%TIME%"

> "%LOG_FILE%" echo ============================================
>> "%LOG_FILE%" echo PDF Runtime Diagnose
>> "%LOG_FILE%" echo ============================================
>> "%LOG_FILE%" echo Timestamp: %RUN_TS%
>> "%LOG_FILE%" echo Project: %PROJECT_ROOT%
>> "%LOG_FILE%" echo.

echo ============================================
echo PDF Runtime Diagnose
echo ============================================
echo Logdatei: %LOG_FILE%
echo.

call :log "[1/5] Archive-Check"
call :check_archive "%PROJECT_ROOT%\runtime\gtk-runtime-win64.zip"
call :check_archive "%PROJECT_ROOT%\runtime\gtk-runtime.zip"
call :check_archive "%PROJECT_ROOT%\packages\gtk-runtime-win64.zip"
call :check_archive "%PROJECT_ROOT%\packages\gtk-runtime.zip"
call :check_archive "%PROJECT_ROOT%\third_party\gtk-runtime-win64.zip"
call :check_archive "%PROJECT_ROOT%\third_party\gtk-runtime.zip"

call :log ""
call :log "[2/5] Lokale GTK-Pfade"
call :check_dir "%PROJECT_ROOT%\runtime\gtk\bin"
call :check_dir "%PROJECT_ROOT%\third_party\gtk\bin"

call :log ""
call :log "[3/5] DLL-Status in lokalen GTK-Pfaden"
call :check_local_dll "%PROJECT_ROOT%\runtime\gtk\bin" "libcairo-2.dll"
call :check_local_dll "%PROJECT_ROOT%\runtime\gtk\bin" "libpango-1.0-0.dll"
call :check_local_dll "%PROJECT_ROOT%\runtime\gtk\bin" "libgobject-2.0-0.dll"
call :check_local_dll "%PROJECT_ROOT%\third_party\gtk\bin" "libcairo-2.dll"
call :check_local_dll "%PROJECT_ROOT%\third_party\gtk\bin" "libpango-1.0-0.dll"
call :check_local_dll "%PROJECT_ROOT%\third_party\gtk\bin" "libgobject-2.0-0.dll"

call :log ""
call :log "[4/5] Systemweite DLL-Aufloesung (where.exe)"
call :check_system_dll "libcairo-2.dll"
call :check_system_dll "libpango-1.0-0.dll"
call :check_system_dll "libgobject-2.0-0.dll"

call :log ""
call :log "[5/5] Python/WeasyPrint Selbstheilung + finaler PDF-Test"
set "PYTHON_EXE=%PROJECT_ROOT%\venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%PROJECT_ROOT%\runtime\python\python.exe"

if not exist "%PYTHON_EXE%" (
  call :log "[FEHLER] Kein Python gefunden (weder venv noch runtime)."
  goto :finish
)

call :log "[INFO] Python: %PYTHON_EXE%"

>> "%LOG_FILE%" echo [CMD] Selbstheilung: ensure_weasyprint_pdf_runtime()
"%PYTHON_EXE%" -c "from app.helpers.pdf_runtime import ensure_weasyprint_pdf_runtime; ok,msg=ensure_weasyprint_pdf_runtime(); print('SELF_HEAL_OK' if ok else 'SELF_HEAL_FAIL'); print(msg)" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
  call :log "[WARNUNG] Selbstheilung wurde mit Fehler beendet. Details in Log."
) else (
  call :log "[OK] Selbstheilung ausgefuehrt."
)

>> "%LOG_FILE%" echo [CMD] Finaler PDF-Test: WeasyPrint write_pdf()
"%PYTHON_EXE%" -c "from weasyprint import HTML; HTML(string='<h1>pdf-runtime-diagnose</h1>').write_pdf(); print('PDF_TEST_OK')" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
  call :log "[FEHLER] Finaler PDF-Test fehlgeschlagen."
) else (
  call :log "[OK] Finaler PDF-Test erfolgreich."
)

:finish
call :log ""
call :log "Diagnose abgeschlossen."
call :log "Logdatei: %LOG_FILE%"

echo.
echo Diagnose abgeschlossen.
echo Logdatei: %LOG_FILE%
pause
exit /b 0

:log
set "MSG=%~1"
echo %MSG%
>> "%LOG_FILE%" echo %MSG%
exit /b 0

:check_archive
set "ARCH=%~1"
if exist "%ARCH%" (
  call :log "[OK] Archiv gefunden: %ARCH%"
) else (
  call :log "[INFO] Archiv fehlt: %ARCH%"
)
exit /b 0

:check_dir
set "DIRPATH=%~1"
if exist "%DIRPATH%" (
  call :log "[OK] Verzeichnis gefunden: %DIRPATH%"
) else (
  call :log "[INFO] Verzeichnis fehlt: %DIRPATH%"
)
exit /b 0

:check_local_dll
set "DLLDIR=%~1"
set "DLLNAME=%~2"
if exist "%DLLDIR%\%DLLNAME%" (
  call :log "[OK] DLL lokal vorhanden: %DLLDIR%\%DLLNAME%"
) else (
  call :log "[INFO] DLL lokal fehlt: %DLLDIR%\%DLLNAME%"
)
exit /b 0

:check_system_dll
set "DLLNAME=%~1"
set "FOUND=0"
for /f "delims=" %%p in ('where.exe %DLLNAME% 2^>nul') do (
  if "%FOUND%"=="0" call :log "[OK] DLL systemweit gefunden (%DLLNAME%):"
  set "FOUND=1"
  call :log "      %%p"
)
if "%FOUND%"=="0" call :log "[INFO] DLL systemweit nicht gefunden: %DLLNAME%"
exit /b 0
