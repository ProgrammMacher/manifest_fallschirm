- billing.py > 5.000 Zeilen
- load.py > 4.000 Zeilen
- mehrere is_admin()-Implementierungen
- Default SECRET_KEY vorhanden
- smtp_password im Klartext gespeichert
- zwei parallele Migrationsmechanismen
- Altdateien im Repository

Portable Runtime kann von requirements.txt abweichen
Problem
Die mitgelieferte Runtime unter runtime/python/ kann vom dokumentierten Paketstand in requirements.txt und den Offline-Paketen unter packages/ abweichen.

Dadurch können Produktivstarts über Waitress fehlschlagen, obwohl Flask-Starts noch funktionieren.

Bekannter Reparaturbefehl
runtime\python\python.exe -m pip install --no-index --find-links=packages -r requirements.txt

Ziel
Klare Pflege- und Aktualisierungsstrategie für:

requirements.txt
packages/
runtime/python/
festlegen.


# Priorisierte Übersicht

Stand: Oktober 2026

# Hoch

## Portable Runtime kann von requirements.txt abweichen

Problem:

Die mitgelieferte Runtime unter

runtime/python/

kann vom dokumentierten Paketstand in

requirements.txt

und den Offline-Paketen unter

packages/

abweichen.

Dadurch können Produktivstarts über Waitress fehlschlagen, obwohl Flask-Starts noch funktionieren.

Bekannter Reparaturbefehl:

runtime\python\python.exe -m pip install --no-index --find-links=packages -r requirements.txt

Ziel:

Klare Pflege- und Aktualisierungsstrategie für:

- requirements.txt
- packages/
- runtime/python/

festlegen.

# Mittel

## billing.py zu groß

Datei:

app/routes/billing.py

Größe:

> 5.000 Zeilen

Risiken:

- schwer testbar
- hohe Komplexität
- schwierige Wartung

Langfristiges Ziel:

fachliche Aufteilung in kleinere Module.

---

## load.py zu groß

Datei:

app/routes/load.py

Größe:

> 4.000 Zeilen

Risiken:

- hoher Analyseaufwand
- schwer wartbar
- hohe Kopplung

Langfristiges Ziel:

Modularisierung.

---

## Mehrere is_admin()-Implementierungen

Problem:

Adminrechte werden nicht zentral geprüft.

Risiken:

- Inkonsistenzen
- doppelte Logik
- Sicherheitsrisiko

Ziel:

Eine zentrale Admin-/DB-Admin-Prüfung.

# Niedrig

## Default SECRET_KEY vorhanden

Problem:

Ein Default SECRET_KEY ist weiterhin vorhanden.

Risiko:

Produktivinstallationen sollten immer einen individuellen SECRET_KEY erhalten.

Ziel:

Installationsspezifischen SECRET_KEY erzwingen.

---

## SMTP-Passwort im Klartext gespeichert

Problem:

SMTP-Passwort wird derzeit im Klartext gespeichert.

Risiko:

Administratoren mit Datenbankzugriff können das Passwort auslesen.

Ziel:

Verschlüsselung oder Secret-Store evaluieren.

---

## Zwei parallele Migrationsmechanismen

Problem:

Für Initialisierung und Migration existieren mehrere Mechanismen.

Beispiele:

- Alembic-Migrationen
- neutral_install_seed.py

Risiken:

- unterschiedliche Datenbankstände
- schwer nachvollziehbare Initialisierung

Ziel:

Klare Trennung zwischen

- Schema-Migration
- Seed-Daten
- Demo-/Beispieldaten

---

## Altdateien im Repository

Problem:

Historische und temporäre Dateien befinden sich im Repository.

Beispiele:

- app/session_data/*
- Runtime-Artefakte
- temporäre Arbeitsdateien

Ziel:

.gitignore prüfen und Repository bereinigen.

---

## Logout-Race-Condition

Status:

Teilweise behoben in Commit:

1ccd29a1

Ursache:

Filesystem-Session + parallele Requests + SESSION_REFRESH_EACH_REQUEST=True.

Umgesetzte Maßnahmen:

- SESSION_REFRESH_EACH_REQUEST=False
- unnötige Session-Schreibvorgänge reduziert
- Regressionstests ergänzt

Bekanntes Restrisiko:

Parallele GET-Requests aus anderen Tabs können theoretisch weiterhin alte Session-Zustände zurückschreiben.

Eine vollständige Lösung würde eine Session-Regeneration beim Logout erfordern.
