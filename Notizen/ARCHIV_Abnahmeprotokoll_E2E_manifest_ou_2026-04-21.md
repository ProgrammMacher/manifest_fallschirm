# ARCHIV - Abnahmeprotokoll E2E - manifest_ou_1_1.exe

Datum: 2026-04-21
Projektordner: C:\manifest_fallschirm
Installer (primaer): C:\manifest_fallschirm\build\installer\manifest_ou_1_1.exe
Hinweis heute: Aktueller Verteilstandard ist C:\manifest_fallschirm\build\installer\manifest_ou_1_2.exe; manifest_ou.exe wird nicht mehr erzeugt.

## Ziel der Abnahme

Pruefung des fertigen Offline-Installers End-to-End mit:

1. Maschinengebundener Testlizenz
2. Lizenzlaufzeit
3. Admin-/DB-Admin-Passwort-Setup
4. Installation in frischen Zielordner
5. Uninstall-Verhalten inkl. optionalem ProgramData-Cleanup

## Testvorbereitung

1. Build des Installers: PASS
   - Ergebnisdatei vorhanden: C:\manifest_fallschirm\build\installer\manifest_ou_1_1.exe
   - Groesse: ca. 104.3 MB

2. Maschinen-Fingerprint erzeugt: PASS
   - Fingerprint: 853fcf3de5dac271a32155e0b8fd68cd72b4f3d812144f5db52a758c5ec547dd

3. Maschinengebundene Testlizenz erzeugt: PASS
   - Payload enthaelt: nbf, exp, hwfp
   - Laufzeit: 2 Tage

4. Frischer Zielordner vorbereitet: PASS
   - C:\manifest_fallschirm\build\e2e_install_target

## Automatisierter Installer-Lauf (silent)

Ausgefuehrte Parameter:

- /VERYSILENT
- /SUPPRESSMSGBOXES
- /NORESTART
- /SP-
- /DIR="C:\manifest_fallschirm\build\e2e_install_target"
- /LICENSEKEY="<test-key>"
- /ADMINPASSWORD="AdminPass123"
- /DBADMINPASSWORD="DbAdmin123"

Ergebnis: FAIL

- Installer-Exitcode in vorherigen Laeufen: 2
- Keine Installation in Zielordner sichtbar
- Keine Secrets-Datei in ProgramData erzeugt

## Root Cause / Blocker

Der Installer ist mit `PrivilegesRequired=admin` konfiguriert und fordert UAC-Elevation.
Im automatisierten Terminallauf kann die UAC-Bestaetigung nicht interaktiv angenommen werden.
Dadurch wird die Installation abgebrochen, bevor die eigentliche Dateikopie/Setup-Schritte starten.

Hinweis: Das ist kein funktionaler Fehler der Lizenz-/Passwortlogik, sondern ein Ausfuehrungsblocker des non-interaktiven Umfelds.

## Erwartetes Verhalten bei manueller E2E-Abnahme (mit UAC-Bestaetigung)

1. Doppelklick auf manifest_ou_1_1.exe
2. UAC mit "Ja" bestaetigen
3. Zielordner waehlen
4. Lizenzschluessel eingeben
5. Admin-/DB-Admin-Passwort setzen
6. Installation abschliessen
7. Pruefen:
   - Zielordner enthaelt app + Startdateien
   - C:\ProgramData\ManifestFallschirm\secrets\auth_config.json existiert
8. Uninstall-Test A: Daten behalten (Nein bei Cleanup-Frage)
9. Reinstall
10. Uninstall-Test B: Daten loeschen (Ja bei Cleanup-Frage)

## Aktueller Abnahmestatus

- Build- und Artefaktstatus: ABGENOMMEN
- E2E-Silent-Installation im Agent-Terminal: NICHT ABNEHMBAR (UAC-Blocker)
- E2E-Installationslogik (manuell-interaktiv): AUSSTEHEND

## Empfehlung naechster Schritt

Manuelle E2E-Abnahme lokal als Administrator mit obiger Checkliste durchfuehren und dieses Protokoll um die realen PASS/FAIL-Ergebnisse der Punkte 7-10 ergaenzen.