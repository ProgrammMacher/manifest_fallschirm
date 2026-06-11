# Start License Generator UI
# PowerShell version with better error handling

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host @"
╔════════════════════════════════════════════════════════════════╗
║  Manifest Fallschirm - License Key Generator                  ║
║  Starting web server...                                        ║
╚════════════════════════════════════════════════════════════════╝

" -ForegroundColor Cyan

# Check if venv exists
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "❌ Python virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

# Activate venv
& "venv\Scripts\Activate.ps1"

# Start Flask app
Write-Host "🚀 Opening browser at http://localhost:5555" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

Start-Sleep -Milliseconds 500
Start-Process "http://localhost:5555"

python admin_license_generator.py
