# Manual: build_offline_compiled_installer_zip.ps1

Dieses Handbuch beschreibt die kompilierte Auslieferung ohne offenen App-.py-Baum.

Skript: [tools/build_offline_compiled_installer_zip.ps1](tools/build_offline_compiled_installer_zip.ps1)

## Ziel

Das Skript erzeugt ein Offline-Installer-ZIP, bei dem der eigene App- und Migrationscode als `.pyc` ausgeliefert wird.

Rahmenbedingungen:

1. Kein Internetzugriff fuer den Build.
2. Nur Pfade innerhalb des Projektordners.
3. Startskripte nutzen automatisch `.pyc` (Fallback auf `.py`).

## Schnellstart

### Variante A: Doppelklick

Starte [tools/build_offline_compiled_installer_zip.bat](tools/build_offline_compiled_installer_zip.bat).

### Variante B: PowerShell

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "tools/build_offline_compiled_installer_zip.ps1"
```

## Was das Skript macht

1. Kopiert die freigegebenen Include-Ordner und Include-Dateien in ein Staging unter [build](build).
2. Kompiliert App-Code und Migrationen zu `.pyc` (sourceless delivery).
3. Entfernt danach die zugehoerigen `.py`-Dateien im Staging.
4. Schreibt eine Build-Doku in `OFFLINE_COMPILED_INSTALLER_CONTENTS.txt`.
5. Packt alles als ZIP nach [build](build).

## Include

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

Hinweis: `manifest_launcher.py` und `run_migrations.py` werden im Staging zu `.pyc` kompiliert und danach als `.py` entfernt.

## Exclude

1. app/session_data/*
2. app/uploads/*
3. data/archive/*
4. data/backup/*
5. data/temp/*
6. logs/*
7. __pycache__/*
8. *.pyc, *.pyo, *.log (vor Kompilierung beim Kopieren)

## Startverhalten im Zielpaket

Die Startskripte wurden kompatibel gemacht:

1. [setup_start_manifest.bat](setup_start_manifest.bat) startet `manifest_launcher.pyc`, wenn vorhanden.
2. [start_manifest_prod.bat](start_manifest_prod.bat) startet `manifest_launcher.pyc`, wenn vorhanden.
3. [start_manifest_prod.vbs](start_manifest_prod.vbs) startet fensterlos `manifest_launcher.pyc`, wenn vorhanden.

Fallback bleibt jeweils `manifest_launcher.py`.

## Validierung

Beispielpruefung nach Build:

```powershell
$zipFile = Get-ChildItem "build/manifest_offline_compiled_installer_*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($zipFile.FullName)
$entries = $zip.Entries | Select-Object -ExpandProperty FullName
$zip.Dispose()

"manifest_launcher.pyc vorhanden: " + [bool]($entries | Where-Object { $_ -like "*manifest_launcher.pyc" })
"app .py vorhanden: " + [bool]($entries | Where-Object { $_ -like "app/*.py" -or $_ -like "app/*/*.py" })
```

## Grenzen des Schutzes

`.pyc` ist deutlich weniger offen als ein `.py`-Baum, aber kein unknackbarer DRM-Schutz.

Wenn du hoehere Schutzstufe willst (starker Reverse-Engineering-Schutz), ist die naechste Stufe eine native Binary-Auslieferung mit Nuitka.

## Fehlerbilder

1. `runtime/python/python.exe` fehlt: Build bricht ab.
2. Kompilierung fehlgeschlagen: Build bricht mit Zielpfad ab.
3. Schreibrechte auf [build](build) fehlen: ZIP wird nicht erstellt.