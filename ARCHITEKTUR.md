ARCHITEKTUR.md

MANIFeST OU

Architekturübersicht für Entwickler und KI-Agenten.

Stand: Oktober 2026

Ziel der Anwendung

MANIFeST OU ist eine Verwaltungs- und Abrechnungssoftware für Fallschirmsprungbetriebe.

Die Anwendung unterstützt Flugplanung, Load-Verwaltung, Personenerfassung, Preisverwaltung, Abrechnung, Rechnungswesen, SEPA-Lastschriften, Newsletter, mobile Personenerfassung, Statistiken, Offline-Betrieb und Lizenzierung.

Architekturprinzip

Die Anwendung basiert auf Flask Application Factory, SQLAlchemy ORM, Jinja2 Templates, Flask Blueprints, einer Service-Schicht und SQLite.

Grundprinzip:

Modelle speichern Daten.
Routes koordinieren Abläufe.
Services enthalten Geschäftslogik.
Templates enthalten Darstellung.
Projektstruktur

Der Einstiegspunkt für die Entwicklung ist run.py.

Der Einstiegspunkt für den Produktivbetrieb ist manifest_launcher.py.

Das Verzeichnis app enthält den eigentlichen Anwendungscode:

models
routes
services
helpers
security
forms
templates
static

Weitere wichtige Verzeichnisse:

migrations
data
tests
installer
tools
packages
runtime
build
Startmechanismen
Entwicklung

run.py startet die Anwendung im Flask-Debug-Modus.

Produktion

manifest_launcher.py übernimmt:

Lizenzprüfung
Laden der Runtime
Start von Waitress
Browserstart
Watchdog-Steuerung
Kernmodule
Personenverwaltung

Verantwortlich für:

Stammdaten
Lizenzdaten
Versicherungsdaten
SEPA-Daten
Newsletter
Mobile Erfassung

Wichtige Dateien:

app/routes/person.py
app/models/person.py
app/services/person_import_service.py
app/services/person_export_service.py
app/services/mobile_person_intake_service.py
Flugzeugverwaltung

Wichtige Dateien:

app/routes/aircraft.py
app/models/aircraft.py
Flugplatzverwaltung

Wichtige Dateien:

app/routes/flugplatz.py
app/models/flugplatz.py
Load-Verwaltung

Verantwortlich für:

Flugplanung
Sprünge
Aufstiege
Sitzplätze
Nutzlast
Displays
Statistiken

Wichtige Dateien:

app/routes/load.py
app/models/load.py
app/models/load_entry.py
app/services/load_service.py
app/services/display_service.py
app/services/tandem_block_service.py
Preisverwaltung

Wichtige Dateien:

app/routes/pricing.py
app/services/pricing_service.py
app/services/price_seed_service.py

Wichtige Tabellen:

BillingPricePeriod
BillingPrice
BillingOrgaRule
BillingOrgaConfig
StatusDefinition

Preisstände sind historisch relevant und müssen nachvollziehbar bleiben.

Abrechnung

Wichtigstes Modul:

app/routes/billing.py

Wichtige Services:

billing_service.py
invoice_state_service.py
payment_data_service.py
sepa_export_service.py
mailer_service.py

Wichtige Modelle:

Invoice
InvoiceItem
BillingConfig
SepaConfig
SepaExport

Aufgaben:

Rechnungsstellung
PDF-Erzeugung
Zahlungsstatus
Kommunikation
E-Mail-Versand
SEPA-Abwicklung
Preis- und Rechnungsarchitektur

Grundprinzip:

Preise können geändert werden.

Bereits erzeugte Rechnungen dürfen dadurch niemals verändert werden.

Aktuelle Preise stammen aus:

BillingPricePeriod
BillingPrice
BillingOrgaRule

Rechnungen enthalten Snapshots der Preisdaten.

Neue Preisänderungen dürfen historische Rechnungen nicht beeinflussen.

SEPA

Wichtige Modelle:

SepaConfig
SepaExport
SepaExportInvoice

Wichtiger Service:

sepa_export_service.py

Exportdaten sind historisch unveränderlich.

Newsletter

Wichtige Dateien:

app/routes/email_newsletter.py
app/models/email_config.py
app/models/email_send_log.py
app/services/mailer_service.py
Mobile Personenerfassung

Wichtige Dateien:

app/routes/pwa.py
app/services/mobile_person_intake_service.py
app/models/mobile_person_intake_draft.py
Datenbank

Datenbanktyp:

SQLite

Produktivdatenbank:

data/manifest.db

Zusätzliche Datenbanken:

Backup-Datenbanken unter data/backup
Temporäre Datenbanken für Prüfungen und Migrationen
Migrationen

Offizielle Migrationen:

migrations/

Alembic wird als primäres Migrationssystem verwendet.

Zusätzliche Startmigrationen befinden sich in:

app/helpers/db_migrations.py

Diese führen idempotente Datenbankanpassungen aus.

Sicherheit

Verzeichnis:

app/security

Wichtige Komponenten:

admin.py
credentials.py
hardware_fingerprint.py
license.py
Lizenzierung

Die Lizenzierung basiert auf:

Hardware-Fingerprint
signierter Lizenzdatei
Validierung beim Anwendungsstart

Wichtige Dateien:

license.py
hardware_fingerprint.py
manifest_launcher.py
PDF-Erzeugung

PDF-Dateien werden mit WeasyPrint erzeugt.

Wichtige Datei:

app/services/pdf_service.py

Templates für PDFs befinden sich unter:

*_pdf.html
waiver_pdf.html
report_pdf.html
Installer

Technologie:

Inno Setup

Verzeichnisse:

installer
tools/inno
build

Der Installer ist produktionskritisch und eng mit Runtime und Lizenzierung gekoppelt.

Kritische Dateien

Folgende Dateien sind historisch gewachsen und besonders vorsichtig zu behandeln:

app/routes/billing.py
app/routes/load.py
app/services/billing_service.py
app/services/person_import_service.py
app/helpers/db_migrations.py

Keine großen Refactorings ohne ausdrückliche Freigabe.

Datenmodell

Zentrale Beziehungen:

Person

besitzt LoadEntries
besitzt Rechnungen
besitzt MobilePersonIntakeDrafts

Load

gehört zu Aircraft
gehört zu Flugplatz
besitzt LoadEntries

LoadEntry

verweist auf Person
verweist optional auf StatusDefinition

Invoice

gehört zu Person
besitzt InvoiceItems

InvoiceItem

verweist optional auf LoadEntry

SepaExport

besitzt SepaExportInvoice-Snapshots
Navigation

Die Hauptnavigation enthält derzeit:

Loads
Flugzeuge
Flugplätze
Personen
Abrechnung
Statistik
Display Hochformat
Display Querformat
Logout
Technische Schulden

Bekannte technische Schulden:

billing.py größer als 5.000 Zeilen
load.py größer als 4.000 Zeilen
billing_service.py größer als 1.800 Zeilen
Mehrere is_admin()-Implementierungen
Zwei parallele Migrationsmechanismen
Historische Debug- und Altdateien im Repository

Diese Bereiche nur nach ausdrücklicher Planung verändern.

Standard-Vorgehen bei Änderungen

Bei neuen Funktionen:

Betroffene Modelle identifizieren.
Betroffene Services identifizieren.
Betroffene Routes identifizieren.
Betroffene Templates identifizieren.
Umsetzungsplan erstellen.
Freigabe einholen.
Umsetzung durchführen.
Tests und Regressionen prüfen.

Ziel ist maximale Rückwärtskompatibilität bei gleichzeitig kontrollierter Weiterentwicklung des Systems.