# Manual: Offline-Installationsdatei manifest_ou_1_2.exe

Dieses Handbuch beschreibt den kompletten Ablauf fuer eine echte Offline-Installationsdatei mit:

1. Setup-Datei `manifest_ou_1_2.exe`
2. Zielordner-Auswahl
3. Startmenue- und Desktop-Icon
4. Lizenzschluessel-Eingabe mit Laufzeit
5. Maschinenbindung der Lizenz (Hardware-Fingerprint + Ablaufdatum)
6. Admin-/DB-Admin-Passwort-Setup
7. Uninstall mit optionalem ProgramData-Cleanup

## Relevante Dateien im Projekt

1. [tools/build_inno_offline_setup.ps1](tools/build_inno_offline_setup.ps1)
2. [tools/build_inno_offline_setup.bat](tools/build_inno_offline_setup.bat)
3. [installer/inno/manifest_offline_setup.iss](installer/inno/manifest_offline_setup.iss)
4. [tools/license/install_runtime_secrets.py](tools/license/install_runtime_secrets.py)
5. [tools/license/generate_license_key.py](tools/license/generate_license_key.py)
6. [tools/license/get_machine_fingerprint.ps1](tools/license/get_machine_fingerprint.ps1)
7. [tools/license/get_machine_fingerprint.bat](tools/license/get_machine_fingerprint.bat)
8. [tools/build_manifest_icon.py](tools/build_manifest_icon.py)
9. [app/static/img/HU_Bleistift.png](app/static/img/HU_Bleistift.png)
10. [app/static/img/manifest_ou.ico](app/static/img/manifest_ou.ico)

## Was die Loesung heute leistet

1. Setup-Dateiname: `manifest_ou_1_2.exe`
2. Setup-Icon und Shortcut-Icon auf Basis des Bleistift-Logos mit Schriftzug `MANIFeST OU`
3. Lizenzpruefung bei Installation und bei jedem App-Start
4. Lizenzablauf (`exp`) wird erzwungen
5. Maschinenbindung (`hwfp`) wird erzwungen
6. Admin- und DB-Admin-Passwort werden als Hash gespeichert, nicht als Klartext
7. Uninstall fragt, ob ProgramData-Daten behalten oder geloescht werden sollen

## Voraussetzungen (ohne Internet beim Build)

1. Projektordner vollstaendig: `C:\manifest_fallschirm`
2. Inno Setup lokal installiert
3. Inno-Compiler steht im Projekt unter [tools/inno](tools/inno) (Build-Skript synchronisiert fehlende Dateien automatisch aus `C:\Program Files (x86)\Inno Setup 6` oder `C:\Program Files\Inno Setup 6`)
4. Runtime vorhanden: `C:\manifest_fallschirm\runtime\python\python.exe`

## A) Hardware-Fingerprint vom Zielrechner ermitteln

Maschinenbindung braucht den Fingerprint des Zielrechners.

Auf Zielrechner ausfuehren:

1. [tools/license/get_machine_fingerprint.bat](tools/license/get_machine_fingerprint.bat)
2. Ausgabe kopieren (Hex-String)
3. Fingerprint an den Entwickler senden

Hinweis: Der Fingerprint ist ein SHA256-Hash aus stabilen Maschinenmerkmalen.

## B) Lizenzschluessel mit Laufzeit und Maschinenbindung erzeugen

Auf Entwicklerrechner in `C:\manifest_fallschirm` ausfuehren:

```powershell
runtime\python\python.exe tools\license\generate_license_key.py --customer "Kunde A" --valid-days 365 --fingerprint "<HWFP_VOM_ZIELRECHNER>"
```

Ergebnis:

1. Lizenzschluessel (eine Zeile, fuer Setup-Eingabe)
2. JSON-Payload mit `nbf`, `exp`, `hwfp`

## C) Setup-Datei bauen (manifest_ou_1_2.exe)

Variante 1:

1. [tools/build_inno_offline_setup.bat](tools/build_inno_offline_setup.bat) doppelklicken

Variante 2:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\build_inno_offline_setup.ps1"
```

Ergebnisdatei:

1. [build/installer/manifest_ou_1_2.exe](build/installer/manifest_ou_1_2.exe)

## D) Installation auf Zielrechner

1. `manifest_ou_1_2.exe` per USB/Cloud auf Zielrechner kopieren
2. Doppelklick auf `manifest_ou_1_2.exe`
3. Zielordner waehlen
4. Lizenzschluessel eingeben
5. Admin-Passwort eingeben
6. DB-Admin-Passwort eingeben
7. Installation abschliessen
8. Optional sofort starten

Der Installer schreibt Secrets nach:

1. `C:\ProgramData\ManifestFallschirm\secrets\auth_config.json`

Inhalt:

1. Lizenzschluessel
2. Lizenzablauf
3. Lizenz-HW-Fingerprint
4. Lokal berechneter Maschinen-Fingerprint
5. Passwort-Hashes (Admin, DB-Admin)
6. Zufaelliger Flask Secret Key

## E) Startmenue/Desktop/Icon

1. Startmenue-Eintrag: `MANIFeST OU`
2. Desktop-Icon: `MANIFeST OU`
3. Icon-Datei im Installationsordner: `app\static\img\manifest_ou.ico`

## F) Uninstall-Verhalten und Cleanup-Regeln

Beim Deinstallieren fragt der Uninstaller:

1. ProgramData-Dateien behalten
2. ProgramData-Dateien loeschen

Wenn `Ja` gewaehlt wird, wird geloescht:

1. `C:\ProgramData\ManifestFallschirm`

Wenn `Nein` gewaehlt wird, bleiben erhalten:

1. Lizenz/Secrets
2. ggf. Betriebsdaten fuer spaetere Neuinstallation

## G) Validierung nach Build

Pruefen, ob Setup vorhanden ist:

```powershell
Test-Path "C:\manifest_fallschirm\build\installer\manifest_ou_1_2.exe"
```

Pruefen, ob maschinengebundene Lizenz erzeugt wurde:

1. Payload enthaelt `hwfp`
2. Payload enthaelt `exp`

## H) Fehlersuche

1. Fehler `Could not load ISCmplr.dll`: Inno-Compilerordner unvollstaendig. Build-Skript erneut starten.
2. Fehler `Mismatched or misplaced quotes`: [installer/inno/manifest_offline_setup.iss](installer/inno/manifest_offline_setup.iss) in `[Run]` pruefen.
3. Lizenzfehler bei Start: Fingerprint/exp pruefen, neuen Schluessel fuer die konkrete Maschine erzeugen.
4. Passwortfehler: Setup erneut starten oder Secrets-Datei in ProgramData gezielt erneuern.

## I) Sicherheitshinweis

Die Signatur basiert derzeit auf HMAC mit Secret. Fuer hoechste Schutzstufe sollte langfristig auf Public/Private-Key-Signaturen umgestellt werden (private key nur beim Entwickler, public key im Client).
