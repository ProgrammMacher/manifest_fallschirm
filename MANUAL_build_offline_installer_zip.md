# Manual: build_offline_installer_zip.ps1

Dieses Handbuch beschreibt, wie du mit [tools/build_offline_installer_zip.ps1](tools/build_offline_installer_zip.ps1) ein sauberes Offline-Installer-ZIP aus dem Projektordner erzeugst.

## Ziel

Das Skript erstellt ein verteilbares ZIP-Paket fuer Rechner ohne Internetzugang.

Wichtige Eigenschaften:

1. Nur interne Projektpfade werden verwendet.
2. Keine externen Downloads.
3. Klare Include/Exclude-Regeln.
4. Ausgabe unter [build](build).

## Schnellstart

### Variante A: Doppelklick

Starte [tools/build_offline_installer_zip.bat](tools/build_offline_installer_zip.bat).

### Variante B: PowerShell

Im Projektordner ausfuehren:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "tools/build_offline_installer_zip.ps1"
```

## Ergebnis

Nach erfolgreichem Lauf erzeugt das Skript:

1. Ein Staging-Verzeichnis: [build](build) mit Name manifest_offline_installer_YYYYMMDD_HHMMSS
2. Ein ZIP-Archiv: [build](build) mit Name manifest_offline_installer_YYYYMMDD_HHMMSS.zip
3. Eine Inhaltsdokumentation im jeweiligen Staging-Ordner:
   OFFLINE_INSTALLER_CONTENTS.txt

Hinweis: Der genaue Zeitstempel ist bei jedem Lauf neu.

## Enthaltene Inhalte (Include)

Ordner:

1. app
2. runtime
3. packages
4. migrations
5. data

Dateien:

1. setup_start_manifest.bat
2. start_manifest_prod.bat
3. start_manifest_prod.vbs
4. diagnose_pdf_runtime.bat
5. manifest_launcher.py
6. run_migrations.py
7. requirements.txt
8. MANUAL_setup_start_manifest.md
9. error_response.html

## Ausgeschlossene Inhalte (Exclude)

Das Skript schliesst u. a. aus:

1. app/session_data/*
2. app/uploads/*
3. data/archive/*
4. data/backup/*
5. data/temp/*
6. logs/*
7. __pycache__/*
8. *.pyc, *.pyo, *.log

Zusatz: Entwicklungsordner wie venv und tests werden gar nicht inkludiert.

## Parameter

Optional unterstuetzt das Skript:

1. -ProjectRoot
2. -OutputDir

Beispiel:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "tools/build_offline_installer_zip.ps1" -ProjectRoot "C:\manifest_fallschirm" -OutputDir "C:\manifest_fallschirm\build"
```

## Sicherheitsregel: keine externen Pfade

Das Skript prueft intern, dass alle verarbeiteten Include-Pfade innerhalb des Projektordners liegen.
Bei einem Pfad ausserhalb des Projektordners wird mit Fehler abgebrochen.

## Validierung nach dem Build

Empfohlene Kurzpruefung:

```powershell
$zipFile = Get-ChildItem "build/manifest_offline_installer_*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($zipFile.FullName)
$entries = $zip.Entries | Select-Object -ExpandProperty FullName
$zip.Dispose()

"setup_start_manifest.bat vorhanden: " + [bool]($entries | Where-Object { $_ -eq "setup_start_manifest.bat" })
"manifest_launcher.py vorhanden: " + [bool]($entries | Where-Object { $_ -eq "manifest_launcher.py" })
"venv enthalten: " + [bool]($entries | Where-Object { $_ -like "venv/*" })
"tests enthalten: " + [bool]($entries | Where-Object { $_ -like "tests/*" })
```

## Wichtiger Hinweis zum Quellcode-Schutz

Dieses Build-Skript erzeugt ein funktionsfaehiges Offline-Installer-ZIP, aber keinen starken Code-Schutz.
Python-Dateien bleiben in dieser Stufe sichtbar.

Wenn der Quellcode fuer Zielnutzer nicht direkt sichtbar sein soll, brauchst du eine kompilierte Auslieferung (z. B. Nuitka/PyInstaller) als naechste Ausbaustufe.

Empfohlene Reihenfolge:

1. Stufe 1: Dieses ZIP-Build fuer stabile Offline-Installation nutzen.
2. Stufe 2: Separate Protected-Build-Pipeline aufsetzen (kompilierte Binaries, kein offener .py-Quellbaum).

## Fehlerbilder

1. Fehlermeldung "Projektordner nicht gefunden": Pfad fuer -ProjectRoot pruefen.
2. ZIP wird nicht erzeugt: Schreibrechte auf [build](build) pruefen.
3. Paket zu gross: Include/Exclude in [tools/build_offline_installer_zip.ps1](tools/build_offline_installer_zip.ps1) anpassen.