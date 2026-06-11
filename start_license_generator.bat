@echo off
REM Start License Generator UI
REM This script starts the Flask web server for the license key generator

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║  Manifest Fallschirm - License Key Generator                  ║
echo ║  Starting server...                                            ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Activate Python venv
cd /d %~dp0
call venv\Scripts\activate.bat

REM Start Flask app
python admin_license_generator.py

pause
