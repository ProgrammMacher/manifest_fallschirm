# MANIFeST OU - 3-Minuten-Checkliste (Endanwender)

Stand: 2026-04-22

## Wann nutzen?

Wenn nach Installation Daten fehlen oder eine vorhandene Datenbank uebernommen werden soll.

## Schnellablauf

1. App starten.
2. Im Browser oeffnen: http://localhost:5000/admin/database
3. Auf "Jetzt sichern" klicken (Sicherheits-Backup).
4. Bereich "Datenbank laden (ersetzen)" oeffnen.
5. Gewuenschte .db-Datei auswaehlen.
6. Auf "Datenbank laden" klicken und bestaetigen.
7. Zur Startseite wechseln und Daten pruefen.

## Erwartetes Ergebnis

- Daten sind direkt sichtbar.
- Kein "Internal Server Error" bei Backup/Import.

## Wenn etwas nicht passt

1. App komplett schliessen.
2. App neu starten.
3. Schritte oben erneut ausfuehren.
4. Wenn weiter Fehler auftreten: Screenshot + Uhrzeit notieren und an Support geben.

## Wichtiger Hinweis (fuer manuelle Dateiablage)

Falls eine Datenbankdatei manuell ersetzt werden muss, ist der korrekte Zielordner:

C:\ProgramData\ManifestFallschirm\data\manifest.db

Nicht nur in Program Files ersetzen.
