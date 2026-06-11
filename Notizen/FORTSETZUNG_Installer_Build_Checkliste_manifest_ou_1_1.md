# Fortsetzung Checkliste - Installer Build

Stand: 2026-04-22

## Ziel

Sauber an gleicher Stelle weiterarbeiten, auch nach VS-Code-Schliessen oder Rechner-Neustart.

## A) Vor jedem neuen Build

1. Nur einen Build gleichzeitig starten.
2. Pruefen, ob noch ein alter Build laeuft (ISCC / powershell mit build_inno_offline_setup.ps1).
3. Lockfile build\.inno_build.lock nur loeschen, wenn sicher kein Build mehr aktiv ist.

## B) Build-Reihenfolge (immer gleich)

1. powershell -ExecutionPolicy Bypass -File tools/build_offline_compiled_installer_zip.ps1
2. powershell -ExecutionPolicy Bypass -File tools/build_inno_offline_setup.ps1

## C) Ergebnis bewerten

Ein Installer gilt als gueltig nur wenn:
- Build-Skripte sauber beendet wurden
- und eine neue manifest_ou_1_2.exe mit aktuellem Zeitstempel vorliegt
- und Inno-Compiler im Output erfolgreich abgeschlossen hat

Aktueller Standard:
- es wird nur noch manifest_ou_1_2.exe erzeugt

Datei:
C:\manifest_fallschirm\build\installer\manifest_ou_1_2.exe

## D) Pflicht-Smoketest nach Installation

1. App startet normal.
2. Datenbankseite:
   - /admin/database Backup
   - /admin/database Import
3. Rechnungsversand per E-Mail:
   - PDF-Anhang erzeugt
   - Keine UI-Modaltexte im PDF-Footer.

## E) Bekannter, bereits behobener Sonderfall

- Nur beim E-Mail-PDF trat frueher ein Rendering-Mix aus UI-Modals auf.
- Ist behoben durch Ausschluss von UI-Modalen waehrend is_pdf_render.

## F) Was in den naechsten Chat schreiben

Kurzvorlage:

"Bitte mit der Installer-Fortsetzung weitermachen. Letzter Stand:
- Exe: C:\manifest_fallschirm\build\installer\manifest_ou_1_2.exe
- Letzter gepruefter Punkt: E-Mail-PDF ohne Modaltexte
- Bitte zuerst Prozess/Lock pruefen, dann Build in Standard-Reihenfolge, danach Smoketest."
