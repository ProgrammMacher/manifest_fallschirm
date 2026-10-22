REGELN.md
MANIFeST OU
Diese Datei beschreibt verbindliche Projektregeln für KI-Agenten, Entwickler und zukünftige Erweiterungen.

Ziel des Projekts
MANIFeST OU ist eine Verwaltungs- und Abrechnungssoftware für Fallschirmsprungbetriebe.

Die Anwendung verwaltet:

Personen
Luftfahrzeuge
Flugplätze
Loads und Sprünge
Statusdefinitionen
Preisverwaltung
Abrechnung
Rechnungen
Kleinunternehmerregelungen
SEPA-Lastschriften
E-Mail-Versand
Newsletter
mobile Personenerfassung
Statistiken
PWA-Funktionen
Grundsätze
Bestandsfunktionen schützen
Bestehende Funktionen dürfen niemals ohne ausdrückliche Anweisung verändert werden.

Erweiterungen erfolgen bevorzugt:

additiv
rückwärtskompatibel
ohne Änderung bestehender Prozesse
wenn dies technisch vertretbar ist.

Keine Überraschungen
KI-Agenten sollen:

vor größeren Eingriffen analysieren
anschließend einen Umsetzungsplan erstellen
erst nach Freigabe Änderungen durchführen
Bewährte Architektur beibehalten
Bestehende Projektmuster haben Vorrang.

Neue Architekturkonzepte sollen nicht eingeführt werden, wenn die bestehende Struktur erweitert werden kann.

Datenbank
Migrationen
Schemaänderungen erfolgen über Alembic-Migrationen.

Neue Datenbankfelder dürfen nicht ohne Migration eingeführt werden.

Bestehende Kundendatenbanken
Kundendatenbanken müssen migrierbar bleiben.

Neue Versionen müssen mit vorhandenen Installationen funktionieren.

Historische Daten
Historische Daten dürfen niemals unbeabsichtigt verändert werden.

Dies gilt insbesondere für:

Rechnungen
Preisstände
Abrechnungen
SEPA-Exporte
Auditdaten
Preisverwaltung
Die Preisverwaltung ist ein besonders schützenswerter Bereich.

Preisänderungen
Preisänderungen müssen nachvollziehbar sein.

Wenn möglich:

PriceAuditLog verwenden
Änderungsgründe dokumentieren
Zeiträume eindeutig berücksichtigen
Preisperioden
Preisperioden sind historisch relevant.

Änderungen dürfen keine alten Rechnungen verändern.

Flugspezifische Preise
Neue Preislogik muss mit bestehenden Preisperioden kompatibel bleiben.

Rechnungswesen
Rechnungen
Rechnungen sind revisionsrelevant.

Finalisierte Rechnungen dürfen nicht nachträglich verändert werden.

Rechnungspositionen
Bereits erzeugte Rechnungspositionen gelten als eingefroren.

Spätere Preisänderungen dürfen bestehende Rechnungen nicht beeinflussen.

Nummernkreise
Rechnungsnummern dürfen niemals rückwirkend verändert werden.

SEPA
SEPA-Exportdaten sind revisionsrelevant.

Nach Erstellung eines Exportes sollen Snapshot-Daten unveränderlich bleiben.

Personenverwaltung
Personendaten können rechtlich relevant sein.

Änderungen an:

Enthaftungen
SEPA-Mandaten
Lizenzdaten
Versicherungsdaten
sind besonders vorsichtig umzusetzen.

Benutzeroberfläche
Sprache
Die Anwendung ist deutschsprachig.

Neue Oberflächenbestandteile sind grundsätzlich in deutscher Sprache umzusetzen.

Design
Bestehendes Erscheinungsbild beibehalten.

Verwendet werden:

Bootstrap 5
Bootstrap Icons
Neue UI-Komponenten sollen sich optisch einfügen.

Formulare
Neue Formulare sollen vorhandene Layoutmuster übernehmen.

Templates
Geschäftslogik gehört nicht in Templates.

Templates sind primär für Darstellung zuständig.

Komplexe Regeln gehören:

in Services
in Modelmethoden
in Hilfsfunktionen
Services
Neue Geschäftslogik soll bevorzugt in Services implementiert werden.

Bestehende Services haben Vorrang vor neuen Service-Klassen.

Sicherheit
Lizenzierung
Änderungen an:

Lizenzprüfung
Hardware-Fingerprint
Signaturprüfung
nur nach ausdrücklicher Freigabe.

Administratoren
Bestehende Adminkonzepte erhalten.

Neue Adminfunktionen sollen vorhandene Prüfmechanismen verwenden.

Installer
Der Offline-Installer ist produktionskritisch.

Änderungen an:

Installer
Runtime
Lizenzierung
Deployment
nur nach ausdrücklicher Freigabe.

PWA
Vorhandene PWA-Funktionen erhalten.

Heartbeat-Mechanismen und Runtime-Control dürfen nicht unbeabsichtigt verändert werden.

Logging
Vorhandenes Logging erhalten.

Bei kritischen neuen Funktionen zusätzliches Logging bevorzugen.

Tests
Bei Änderungen in folgenden Bereichen sollen vorhandene Tests berücksichtigt werden:

Preisverwaltung
Rechnungen
SEPA
Personenimport
Migrationen
Lizenzierung
Refactoring
Große Refactorings nur auf ausdrückliche Anweisung.

Insbesondere betroffen:

billing.py
load.py
billing_service.py
Diese Dateien sind historisch gewachsen und produktiv im Einsatz.

Arbeitsweise für KI-Agenten
Bei größeren Aufgaben:

Analyse erstellen.
Betroffene Dateien auflisten.
Umsetzungsplan erstellen.
Freigabe abwarten.
Umsetzung durchführen.
Keine großflächigen Änderungen ohne Plan.

Wichtiger Grundsatz
Lieber bestehende Strukturen erweitern als neue Strukturen erfinden.

Stabilität und Rückwärtskompatibilität haben Vorrang vor technischer Perfektion.