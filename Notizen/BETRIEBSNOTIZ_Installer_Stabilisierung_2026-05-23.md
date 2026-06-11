# Betriebsnotiz: Installer-Stabilisierung und Runtime-Pfadfix (2026-05-23)

## Ausgangslage

Wiederholte Startprobleme im installierten Modus (Program Files), trotz mehrfacher Rebuilds von manifest_ou_1_2.exe.

Hauptfehlerbilder:

1. Installer/Start fiel auf Program Files als Runtime-Home zurueck.
2. venv-Erstellung unter Program Files schlug mit WinError 5 fehl.
3. install_runtime_secrets.py scheiterte mit nackter Runtime an App-Importkette.
4. App-Start scheiterte spaeter mit PermissionError auf C:\Program Files\MANIFeST OU\logs.

## Durchgefuehrte technische Schritte

### 1) Installer-Bootstrap von App entkoppelt

Neues app-unabhaengiges Hilfsmodul erstellt:

- tools/license/security_core.py

Darauf umgestellt:

- tools/license/install_runtime_secrets.py
- tools/license/generate_license_key.py
- tools/license/print_machine_fingerprint.py

Ziel:
Der Installer-Secrets-Schritt muss mit runtime/python/python.exe ohne App-Initialisierung laufen.

### 2) Pfad-/Runtime-Logik in Startern gehaertet

Anpassungen in Startskripten (bereits in vorherigen Schritten erfolgt und weiterverwendet):

- start_manifest_prod.bat
- setup_start_manifest.bat
- start_manifest_prod.vbs

Ziel:
Bei vorhandenen installierten Secrets Runtime-Home auf ProgramData umstellen, statt Program Files zu verwenden.

### 3) Schreibpfad-Fix in App-Initialisierung

In app/__init__.py wurde die Verzeichniswahl auf Runtime-Home-first mit Fallback umgestellt:

- LOG_DIR
- DATA_DIR
- UPLOAD_FOLDER
- SESSION_FILE_DIR

Dabei wird Schreibbarkeit aktiv geprueft (write probe), um PermissionError in Program Files zu vermeiden.

### 4) Inno-Berechtigungen fuer ProgramData gesetzt

In installer/inno/manifest_offline_setup.iss wurden Dirs mit users-modify gesetzt:

- {commonappdata}\ManifestFallschirm
- {commonappdata}\ManifestFallschirm\secrets
- {commonappdata}\ManifestFallschirm\logs
- {commonappdata}\ManifestFallschirm\data
- {commonappdata}\ManifestFallschirm\uploads
- {commonappdata}\ManifestFallschirm\session_data
- {commonappdata}\ManifestFallschirm\venv

Ziel:
Schreibvorgaenge im installierten Laufzeitmodus ohne Admin-Nachstart ermoeglichen.

## Verifikation

### Direkter Runtime-Test (ohne venv)

Erfolgreich:

- runtime\python\python.exe tools\license\install_runtime_secrets.py --help
- runtime\python\python.exe tools\license\generate_license_key.py --help
- runtime\python\python.exe tools\license\print_machine_fingerprint.py

### Lizenz-Check auf diesem Rechner

Gepruefter Schluessel war gueltig fuer den aktuellen Fingerprint.

### Build-Status

Installer mehrfach neu gebaut; finaler Stand:

- build/installer/manifest_ou_1_2.exe
- LastWriteTime: 23.05.2026 01:13:44
- Length: 109968486 Bytes

## Cleanup

Nach jedem erfolgreichen Rebuild wurden temporaere Build-Artefakte entfernt:

- build/.inno_build.lock
- build/inno_stage_* (temp)
- build/manifest_offline_compiled_installer_* (temp + zip)

Aktueller Projektgroessenstand nach Cleanup:

- TOTAL_MB: 741.31

## Betriebsrelevante Schlussfolgerung

1. Kopiermodus (Projektordner) und Installermodus (lizenzierter Betrieb) sind technisch getrennte Laufzeitmodi.
2. Installer-Bootstrap ist jetzt app-unabhaengig und damit frueher im Setup robust.
3. Installierter Betrieb soll auf ProgramData als schreibbaren Runtime-Bereich laufen; Program Files bleibt nur Installationsort.
