$ErrorActionPreference = 'Stop'

# Baut die Endanwender-EXE "MANIFeST_Rechnerkennung.exe" mit PyInstaller.
# Entwickler-only: nutzt eine eigene Build-Umgebung unter build\fingerprint\venv.
# Projekt-Abhaengigkeiten und die portable Runtime bleiben unveraendert.

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BuildDir    = Join-Path $ProjectRoot 'build\fingerprint'
$VenvDir     = Join-Path $BuildDir 'venv'
$DistDir     = Join-Path $BuildDir 'dist'
$WorkDir     = Join-Path $BuildDir 'work'
$ExeName     = 'MANIFeST_Rechnerkennung.exe'
$AppPy       = Join-Path $PSScriptRoot 'fingerprint_app.py'
$FingerprintPy = Join-Path $ProjectRoot 'app\security\hardware_fingerprint.py'
$Icon        = Join-Path $ProjectRoot 'app\static\img\manifest_ou.ico'

if (-not (Test-Path $AppPy)) { throw "fingerprint_app.py fehlt: $AppPy" }
if (-not (Test-Path $FingerprintPy)) { throw "hardware_fingerprint.py fehlt: $FingerprintPy" }
if (-not (Test-Path $Icon)) { throw "Icon fehlt: $Icon" }

# 1) Eigene Build-Umgebung (getrennt vom Projekt-venv und der Runtime)
if (-not (Test-Path (Join-Path $VenvDir 'Scripts\python.exe'))) {
    Write-Host 'Erzeuge Build-Umgebung unter build\fingerprint\venv ...'
    $SystemPython = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $SystemPython) { $SystemPython = 'py' }
    & $SystemPython -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw 'venv konnte nicht erzeugt werden.' }
}
$Py = Join-Path $VenvDir 'Scripts\python.exe'

# 2) Nur 64-Bit-Python bauen: ein 32-Bit-Build liest eine andere MachineGuid
#    und wuerde eine falsche Rechner-Kennung liefern.
$ArchCheck = & $Py -c "import struct; print(struct.calcsize('P') * 8)"
if ($ArchCheck -ne '64') {
    throw "Nur 64-Bit-Python ist erlaubt (gefunden: $ArchCheck Bit). Bitte 64-Bit-Python als 'python' im PATH verwenden."
}

# 3) PyInstaller nur in der Build-Umgebung installieren (Internet auf Entwicklerrechner noetig)
Write-Host 'Installiere PyInstaller in der Build-Umgebung ...'
& $Py -m pip install --upgrade pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'pip install pyinstaller fehlgeschlagen.' }

# 4) EXE bauen: eine Datei, kein Konsolenfenster, hardware_fingerprint.py als Quelle
Write-Host 'Baue MANIFeST_Rechnerkennung.exe ...'
New-Item -ItemType Directory -Force -Path $DistDir, $WorkDir | Out-Null
& $Py -m PyInstaller `
    --onefile `
    --windowed `
    --clean `
    --noconfirm `
    --name 'MANIFeST_Rechnerkennung' `
    --icon $Icon `
    --paths (Join-Path $ProjectRoot 'app\security') `
    --distpath $DistDir `
    --workpath $WorkDir `
    --specpath $BuildDir `
    $AppPy
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller-Build fehlgeschlagen.' }

$Exe = Join-Path $DistDir $ExeName
if (-not (Test-Path $Exe)) { throw "EXE nicht gefunden: $Exe" }

Write-Host ''
Write-Host 'Fertig:' -ForegroundColor Green
Write-Host "  EXE:              $Exe"
Write-Host ("  SHA256 EXE:       " + (Get-FileHash $Exe -Algorithm SHA256).Hash)
Write-Host ("  SHA256 Quelle:    " + (Get-FileHash $FingerprintPy -Algorithm SHA256).Hash + "  (app\security\hardware_fingerprint.py)")
Write-Host ''
Write-Host 'Manuelle Pruefung vor Weitergabe:'
Write-Host '  1. EXE auf einem Testrechner per Doppelklick starten.'
Write-Host '  2. Angezeigte Kennung muss identisch sein mit:'
Write-Host '     python -c "from app.security.hardware_fingerprint import get_machine_fingerprint; print(get_machine_fingerprint())"'
Write-Host '  3. EXE nur per Download-Link weitergeben (siehe README.txt), nie als Mail-Anhang.'
