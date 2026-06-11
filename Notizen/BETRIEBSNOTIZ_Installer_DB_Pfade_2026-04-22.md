# MANIFeST OU - Betriebsnotiz (Installer + Datenbank)

Stand: 2026-04-22
Status: Verifiziert in installierter EXE-Version

## 1) Laufzeitpfade (wichtig)

Die installierte App nutzt fuer schreibende Laufzeitdaten ProgramData:

- Aktive DB: C:\ProgramData\ManifestFallschirm\data\manifest.db
- Backups: C:\ProgramData\ManifestFallschirm\data\backup\
- Archiv: C:\ProgramData\ManifestFallschirm\data\archive\
- Temp: C:\ProgramData\ManifestFallschirm\data\temp\
- Logs: C:\ProgramData\ManifestFallschirm\logs\
- Uploads: C:\ProgramData\ManifestFallschirm\uploads\
- Sessiondaten: C:\ProgramData\ManifestFallschirm\session_data\
- Secrets/Auth: C:\ProgramData\ManifestFallschirm\secrets\auth_config.json

Hinweis:
C:\Program Files\MANIFeST OU\data\manifest.db ist fuer den laufenden Betrieb nicht mehr die massgebliche Live-DB, wenn ProgramData-Fallback aktiv ist.

## 2) Standardablauf fuer DB-Uebernahme

1. App starten.
2. Seite aufrufen: http://localhost:5000/admin/database
3. Zuerst Backup ausloesen.
4. Danach "Datenbank laden" mit vorhandener .db-Datei ausfuehren.
5. Startseite/Fachseiten pruefen: Daten muessen sofort sichtbar sein.

## 3) Wenn Daten nach manuellem Kopieren nicht sichtbar sind

Ursache fast immer: falscher Zielpfad.

Verwende fuer manuelles Ersetzen immer:
C:\ProgramData\ManifestFallschirm\data\manifest.db

Nicht nur in Program Files ersetzen.

## 4) Verifizierte Fixes (Code)

- Admin-Backup/Export/Import nutzen den aktiven SQLALCHEMY_DATABASE_URI-Pfad.
- DB-Operationen (backup/archive/temp) laufen relativ zur aktiven Laufzeit-DB.
- Import-Upload und Sessiondaten nutzen konfigurierte, beschreibbare Laufzeitordner.
- app_settings.json wird in einen beschreibbaren data-Ordner gelegt (Projekt oder ProgramData).

## 5) Betriebs-Check nach Neuinstallation

1. Installer ausfuehren: C:\manifest_fallschirm\build\installer\manifest_ou_1_2.exe
2. App starten.
3. /admin/database: Backup testen.
4. /admin/database: Datenbank laden testen.
5. Sichtpruefung in der App.
6. Optional: Logs pruefen unter C:\ProgramData\ManifestFallschirm\logs\

## 6) Build-Hinweis

Ein vorhandenes setup EXE ist nur vertrauenswuerdig, wenn der letzte Build erfolgreich beendet wurde (Exit-Code 0 / Successful compile).
Parallel gestartete Inno-Builds koennen Lock-Konflikte erzeugen (build\.inno_build.lock).

## 7) Spezieller Bugfix Rechnungsversand-PDF

Problem (behoben):
Beim PDF fuer den E-Mail-Versand wurden Modal-Texte aus der UI am Seitenende mitgerendert
(z.B. "E-Mail wird versendet..." und Datensicherungs-Dialogtexte).

Loesung (behoben):
- UI-Modals und zugehoerige Script-Teile werden beim PDF-Render ausgeschlossen.
- Bedingung: is_pdf_render.

Symptomabgrenzung:
- Fehler trat nur im serverseitigen PDF-Pfad fuer E-Mail-Anhang auf.
- Normaler Browser-PDF-Export war nicht betroffen.

## 8) Fortsetzen nach VS-Code/PC-Neustart

1. Workspace C:\manifest_fallschirm oeffnen.
2. Aktuelle Installer-Datei pruefen: C:\manifest_fallschirm\build\installer\manifest_ou_1_2.exe (primaer, Zeitstempel notieren).
3. Falls Build unklar/alt: nur einen Build-Lauf starten (keine Parallelstarts).
4. Vor Build pruefen, ob noch ISCC/Build-Prozess laeuft; nur dann ggf. lock entfernen.
5. Build-Reihenfolge:
	- tools/build_offline_compiled_installer_zip.ps1
	- tools/build_inno_offline_setup.ps1
6. Erfolg nur bei sauberem Abschluss akzeptieren (Exit-Code 0 und Compiler-Erfolgsmeldung im Output).
7. Installer installieren und Kern-Smoketest:
	- /admin/database Backup
	- /admin/database Import
	- Rechnungsversand per E-Mail inkl. PDF-Anhang
8. Ergebnis in Notizen dokumentieren (Datum, Installer-Zeitstempel, Test ok/nicht ok).
