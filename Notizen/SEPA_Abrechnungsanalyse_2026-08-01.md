# SEPA-Analyse zur Abrechnungsübersicht und Exports

Datum: 2026-08-01

## Zweck

Diese Notiz fasst die Analyse aus dem aktuellen Chat zusammen, damit das Thema später nicht erneut doppelt behandelt werden muss.

## Umfang

Analysiert wurden:
- die Rechnungsliste unter /billing/invoices
- die zugehörigen Exportfunktionen für
  - PDF
  - Excel
  - CSV

Es wurden keine Änderungen umgesetzt. Es handelte sich ausschließlich um eine Analyse des aktuellen Zustands.

## Zentrale Erkenntnisse

### 1. SEPA-Zustände sind im System vorhanden und werden unterschieden

Die folgenden Zustände werden in der Abrechnungslogik erkannt und dargestellt:
- offen
- sepa_pending
- sepa_exported
- sepa_returned
- paid

### 2. SEPA wird als eigener Zahlungsweg und als eigener Statuspfad behandelt

SEPA-Rechnungen werden nicht nur über die Zahlungsart `payment_method = sepa` adressiert, sondern zusätzlich über eigene Zustände wie:
- SEPA vorgemerkt
- SEPA exportiert
- Rücklastschrift
- bezahlt nach erfolgreichem SEPA-Einzug

### 3. Die Rechnungsliste berücksichtigt SEPA grundsätzlich

Die Übersicht unter /billing/invoices berücksichtigt SEPA-Rechnungen in der Liste, in den Filtern, in der Statusdarstellung und in den Summenblöcken.

### 4. Statusfilter und Zahlungsartenfilter sind vorhanden

Die Rechnungsliste bietet Filter für:
- Status: offen, SEPA vorgemerkt, SEPA exportiert, Nicht SEPA, bezahlt, Rücklastschrift
- Bezahlart: Bar, Karte, Überweisung, WERO, SEPA-Lastschrift, Vorkasse / Gutschein

Zusätzlich gibt es Sortieroptionen wie:
- SEPA vorgemerkt zuerst
- SEPA exportiert zuerst
- SEPA zuletzt

### 5. SEPA-Export-Box ist enger als die allgemeine Übersicht

Die SEPA-Export-Box arbeitet aktuell nur mit Rechnungen im Zustand `sepa_pending`.

Folge:
- Rechnungen im Zustand `sepa_exported` oder `sepa_returned` sind nicht mehr direkt für den SEPA-Export auswählbar.
- Die Exportbox ist damit funktional enger als die allgemeine Übersicht.

### 6. SEPA-Exporthistorie wird angezeigt, aber nicht als eigene Exportdatenquelle in die Exporte übernommen

Die Historie zu SEPA-Exporten wird in der UI dargestellt.

Sie wird aber nicht als zusätzliche Datenquelle in die PDF-/Excel-/CSV-Exporte eingebunden.

### 7. Rücklastschriften sind eindeutig sichtbar

Rechnungen im Zustand `sepa_returned` werden als Rücklastschrift dargestellt und sind klar erkennbar.

### 8. SEPA-Rollbacks wirken sich auf den Zustand aus

Ein SEPA-Rollback setzt die Rechnung wieder auf einen offenen, neutralen Zustand zurück und entfernt die SEPA-Zahlungsart im Modell.

Dadurch werden solche Rechnungen wieder wie normale offene Rechnungen behandelt.

## Ergebnis der Analyse

### Rechnungsliste /billing/invoices

SEPA-Rechnungen werden in der Rechnungsliste grundsätzlich vollständig und korrekt berücksichtigt.

Sie werden unterschieden nach:
- offen / SEPA-Status
- SEPA vorgemerkt
- SEPA exportiert
- Rücklastschrift
- bezahlt

### PDF-Export

SEPA-Rechnungen werden in die PDF-Übersicht einbezogen.

Die wichtigsten Punkte:
- SEPA-Status wird dargestellt
- Rücklastschriften sind sichtbar
- Bezahlart-/Summenlogik ist vorhanden

### Excel-Export

SEPA-Rechnungen werden in den Excel-Export übernommen.

Es gibt keine eigene Spezialspalte für SEPA, aber Status und Bezahlart sind im Export vorhanden.

### CSV-Export

SEPA-Rechnungen werden in den CSV-Export übernommen.

Die relevanten Felder für Zustand und Zahlungsart sind vorhanden.

## Hauptfokuspunkte / offene Punkte

Die aktuell relevantesten engen Stellen sind:
- die SEPA-Exportbox ist nur auf `sepa_pending` begrenzt
- die SEPA-Exporthistorie ist UI-seitig sichtbar, aber nicht eine eigene Exportdatenquelle
- Rücklastschriften und Rollbacks sind zwar sichtbar, aber nicht als eigener separater Summen- oder Statistikblock modelliert

## Betroffene Dateien

Die Analyse betrifft vor allem:
- app/routes/billing.py
- app/templates/billing/invoice_list.html
- app/templates/billing/invoice_list_pdf.html

## Abschluss

Die SEPA-Logik ist im Rechnungs- und Exportpfad grundsätzlich vorhanden und wird weitgehend konsistent behandelt.

Die größte Einschränkung liegt nicht in der Aufnahme von SEPA-Rechnungen, sondern in der engeren SEPA-Exportbox und in der fehlenden Einbindung der SEPA-Exporthistorie als eigene Exportdatenquelle.
