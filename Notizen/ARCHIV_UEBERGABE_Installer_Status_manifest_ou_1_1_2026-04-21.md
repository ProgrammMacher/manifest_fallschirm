# ARCHIV - Uebergabe: Installer- und E2E-Status (2026-04-21)

## Archivhinweis
- Historisches Uebergabedokument vom 2026-04-21.
- Aktueller Installer-Standard heute: build/installer/manifest_ou_1_2.exe.

## Ziel
- Offline-Installer MANIFeST OU mit Lizenz, Admin/DB-Admin-Setup und sauberem Startverhalten.

## Aktueller Stand
- Inno-Installer wird erfolgreich gebaut.
- Historische Build-Datei (Stand 2026-04-21): build/installer/manifest_ou.exe (neu erzeugt am 21.04.2026, 22:27, ca. 104 MB).
- Aktuelle Primaerdatei fuer neue Builds: build/installer/manifest_ou_1_2.exe.
- Passwortseite wurde angepasst:
	- Passwoerter sichtbar.
	- Mindestlaenge entfernt (nur nicht-leer).
- Setup-/Startskripte wurden auf Benutzer-venv-Fallback umgestellt.

## Letzter reproduzierter Fehler beim Kundenstart
- Windows Script Host Fehler in C:\Program Files\MANIFeST OU\start_manifest_prod.vbs
- Code: 800A0409
- Meldung: Unterminated string constant
- Zeile: 30

## Wahrscheinliche technische Ursache
- Fehlerhafte Quote-Escaping-Zeile in VBS (Shell.Run mit zusammengesetzten Anfuehrungszeichen).

## Bereits erledigte Korrekturen im Build-Prozess
- Inno-Readiness-Check robust gemacht (ISCC /? Exit-Code 0 oder 1).
- Build-Staging angepasst: aktuelle Startskripte werden beim Inno-Build explizit in die Stage kopiert (nicht nur aus altem ZIP uebernommen).
- Logo-Tausch im App-Quellstand erledigt: Logo_Dessau.png -> Logo_DZ.png in allen aktiven Templates/Routen unter app/.

## Hinweis zum Logo-Stand
- Die Umstellung auf Logo_DZ.png ist im produktiven Quellcode (app/) aktiv.
- In vorhandenen build/-Artefakten existieren noch alte Referenzen auf Logo_Dessau.png, bis ein neuer Build erzeugt wurde.
- Fuer Auslieferung und Test nur neu gebaute Installer verwenden.

## Erledigt in dieser Session
1. start_manifest_prod.vbs Quote-Escaping korrigiert (fehlerhafte Shell.Run-Quoting-Zeile repariert).
2. Installer neu gebaut (tools/build_inno_offline_setup.ps1, Exit-Code 0).

## Offene ToDos
1. Vollstaendig deinstallieren und neu installieren (mit neuem build/installer/manifest_ou_1_2.exe).
2. Start ueber Startmenue pruefen (inkl. VBS-Fehlerfreiheit).
3. Sichtpruefung: rechts oben muss Logo_DZ.png erscheinen.
4. E2E-Protokoll in Notizen/ARCHIV_Abnahmeprotokoll_E2E_manifest_ou_1_1_2026-04-21.md finalisieren (PASS/FAIL).

## Wichtige Betriebsregeln
- Fuer Neuinstallationen build/installer/manifest_ou_1_2.exe verwenden.
- Alte Artefakte (manifest_ou_run.exe, manifest_setup.exe) nicht mehr verwenden.
- Lizenz ist hardwaregebunden (hwfp) und i.d.R. pro Rechner unterschiedlich.