SQLite‑Datenbank (Format 3), dateibasiert, persistent, lokal
SQLite format 3

Datenbanktyp

✅ SQLite 3
✅ Dateibasiert
✅ Persistent
✅ Transaktionssicher
✅ Single‑User‑optimiert

C:\manifest_fallschirm\data\manifest.db

Warum „kein Speichern“ nötig ist (wichtige Erkenntnis)
SQLite arbeitet so:

Jede Änderung (INSERT, UPDATE, DELETE)
wird sofort in die Datei geschrieben
innerhalb einer Transaktion
automatisch von Flask / ORM ausgelöst

👉 Deshalb:

kein „Speichern“-Button
kein expliziter Commit für den Benutzer
nach Neustart alles wieder da

✅ Strukturierte relationale Datenbank
Man sieht u. a.:

CREATE TABLE person
CREATE TABLE pricing
CREATE TABLE status_definitions
CREATE TABLE flugplatz
price_audit_log

✅ Indizes
Z. B.: CREATE INDEX ix_person_email ON person (email)

✅ Audit‑Log vorhanden
price_audit_log

👉 Sehr wichtig für:

Nachvollziehbarkeit
Abrechnung
spätere Revisionen


Was ihr nicht habt (klar abgrenzen)
❌ Kein Datenbankserver
❌ Keine Cloud‑Datenbank
❌ Kein Shared‑Access
❌ Kein Live‑Mehrbenutzerbetrieb
👉 Und das ist genau richtig für eure Anforderungen.


Warum SQLite für euch ideal ist (objektiv)
Für euer Szenario:

1 Benutzer
klare Arbeitsphasen
Export / Import
Jahresarchive
Transport über Cloud

ist SQLite nicht nur ausreichend, sondern optimal.
Ihr bekommt:
✅ einfache Backups (Datei kopieren)
✅ einfache Archivierung (Datei umbenennen)
✅ einfache Übergabe (Datei weitergeben)
✅ keine Infrastrukturkosten
✅ minimale Fehlerquellen


Damit SQLite dauerhaft stabil bleibt, gelten nur diese Regeln:

DB-Datei nur kopieren, wenn die App nicht läuft
Nie zwei laufende Apps auf dieselbe DB-Datei
Cloud nur als Transport, nicht als Live‑Speicher
Backups = einfache Dateikopien

Wenn ihr das einhaltet → jahrelang problemlos.