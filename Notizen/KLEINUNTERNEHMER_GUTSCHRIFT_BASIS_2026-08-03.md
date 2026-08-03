# Konfigurierbare Kleinunternehmer-Gutschrift-Basis für Tandemmaster und Video

Datum: 2026-08-03

## Zweck

Diese Notiz beschreibt die Einführung einer konfigurierbaren Vergütungsbasis für Kleinunternehmer-Gutschriften bei Tandemmaster- und Video-Positionen. Ziel war es, den Auszahlungsbetrag für Kleinunternehmer flexibel zu gestalten, ohne die steuerliche Behandlung der Gutschrift zu verändern.

## Ausgangssituation

Bisher wurde bei Kleinunternehmern für die betroffenen Gutschriften immer der in der Preismatrix hinterlegte Preis ausgezahlt.

Beispiel:
- Preis in der Preismatrix: 75,00 €
- Kleinunternehmer erhielt: 75,00 €
- MwSt. auf der Gutschrift: 0 %

Damit war die Vergütung für Kleinunternehmer strikt an den hinterlegten Bruttopreis gekoppelt. Eine Auswahl zwischen Bruttopreis und Nettopreis war nicht vorhanden.

## Ziel

Die neue Funktion soll eine konfigurierbare Berechnungsbasis für Kleinunternehmer-Gutschriften ermöglichen:
- Auswahl zwischen Bruttopreis und Nettopreis
- keine Änderung der steuerlichen Behandlung
- nur Änderung des Auszahlungsbetrags

Die fachliche Intention ist ausdrücklich eine Vergütungsregel und keine Steuerregel.

## Fachliche Entscheidung

Die neu eingeführte Funktion ist als Vergütungsregel zu verstehen.

Wichtige Grundsätze:
- Die Regel betrifft die Auszahlung an den Kleinunternehmer.
- Sie ist keine Steuerregel.
- Die MwSt. auf Kleinunternehmer-Gutschriften bleibt weiterhin 0 %.
- Der Anwender entscheidet bewusst, ob der Kleinunternehmer den Bruttopreis oder den Nettopreis erhält.

Damit bleibt die steuerliche Behandlung der Gutschrift unverändert. Lediglich die Höhe der Auszahlung wird abhängig von der gewählten Basis angepasst.

## Betroffene Status

Die neue Auswahl wurde für die Statusgruppen:
- TD
- Video

implementiert.

Technisch weiterhin unterstützt ist außerdem der Status TD-Vereins-Schirm. Dieser wird in der Praxis jedoch heute kaum noch verwendet. In der aktuellen Nutzung wird statt dessen typischerweise TD zusammen mit einer separaten Schirmmiete verwendet.

## Schirmmiete

Die Schirmmiete wird in der aktuellen Implementierung als eigene Rechnungs-/Gutschriftsposition behandelt.

Wichtige Punkte aus der Analyse:
- Die Schirmmiete wird als eigene Position erzeugt.
- Sie ist technisch von der Kleinunternehmer-Gutschrift für Sprungpositionen getrennt.
- Die neue Bruttopreis-/Nettopreis-Einstellung für Kleinunternehmer beeinflusst die Schirmmiete nicht.
- Die Schirmmiete verwendet weiterhin den in der Billing-Konfiguration hinterlegten MwSt.-Satz.
- Der Verein bleibt bei der Schirmmiete umsatzsteuerpflichtig.

Damit ist die Schirmmiete kein Teil der Kleinunternehmer-Gutschrift-Berechnung, sondern ein eigener Berechnungspfad mit eigener Preis- und MwSt-Logik.

## Technische Umsetzung

### Betroffene Dateien

Die Funktion betrifft vor allem folgende Bereiche:
- app/models/billing_config.py
- app/models/invoice_item.py
- app/services/billing_service.py
- app/helpers/status_code.py
- app/routes/pricing.py
- app/templates/billing/index.html

### Neue Migration

Es wurde eine neue Migration ergänzt:
- migrations/versions/20260802_add_ku_credit_payout_fields.py

### Neue Snapshot-Felder

Für Rechnungsposten wurden zusätzliche Snapshot-Felder ergänzt:
- ku_credit_payout_basis
- ku_credit_payout_amount

Diese Felder speichern die verwendete Vergütungsbasis und den effektiven Auszahlungsbetrag zum Zeitpunkt der Rechnungserstellung.

### Anpassungen in Pricing

Die Preisverwaltung wurde um eine neue Auswahl ergänzt:
- "Kleinunternehmer erhält"

Verfügbare Werte:
- Bruttopreis
- Nettopreis

Die Auswahl wird pro Status/Periode in der Preismatrix verwaltet.

### Anpassungen im Billing Service

Die Berechnung der Kleinunternehmer-Gutschriften wurde im Billing Service erweitert:
- Ermittlung der verwendeten Basis für relevante Status
- Berechnung des effektiven Auszahlungsbetrags
- Speicherung der Basis und des Betrags auf den Rechnungsposten

Diese Anpassung betrifft die Sprung-Gutschriften, nicht die Schirmmiete.

### Statusnormalisierung

Die Status-Erkennung wurde erweitert, damit die neue UI- und Berechnungslogik für die relevanten Status konsistent behandelt wird.

### UI-Anpassungen

In der Preismatrix wurde eine neue Auswahl ergänzt.

Die Darstellung enthält:
- eine neue Überschrift "Kleinunternehmer erhält"
- die Werte Bruttopreis und Nettopreis
- eine Anzeige nur für relevante Status
- ein Info-Icon mit Tooltip zur Erklärung der Funktion

## Benutzeroberfläche

In der Preismatrix erscheint nun die neue Auswahl:

- Kleinunternehmer erhält
  - Bruttopreis
  - Nettopreis

Die Auswahl wird nur dort angezeigt, wo die Funktion fachlich relevant ist. Für nicht betroffene Status erscheint sie nicht.

Das Info-Icon liefert eine kurze Erklärung zur Funktion und erklärt, dass die Gutschrift weiterhin 0 % MwSt. aufweist, während der Auszahlungsbetrag je nach Auswahl angepasst wird.

## Migration

Die Migration 20260802_add_ku_credit_payout_fields.py ergänzt die notwendigen Datenbankfelder für die neue Vergütungsregel.

Ergänzte Felder:
- In billing_price:
  - ku_credit_payout_basis
- In invoice_item:
  - ku_credit_payout_basis
  - ku_credit_payout_amount

Diese Felder werden verwendet, um die Regel dauerhaft und nachvollziehbar in der Rechnungssnapshot-Struktur abzubilden.

## Tests

Für die Änderung wurden gezielte Regressionstests ergänzt bzw. erweitert:
- tests/test_ku_tandemmaster_regressions.py
- tests/test_status_code_normalization.py

Die relevanten Regressionstests wurden erfolgreich durchlaufen.

## Risiken und Hinweise

- Bestehende Rechnungen werden nicht automatisch nachträglich geändert.
- Die neue Regel wirkt nur auf neu berechnete bzw. neu erzeugte Gutschriften.
- Die Schirmmiete bleibt von dieser Regelung unberührt.
- Die steuerliche Behandlung der Kleinunternehmer-Gutschrift bleibt unverändert bei 0 % MwSt.

## Abschlussbewertung

Die Lösung schafft eine flexible Vergütungsregel für Kleinunternehmer-Gutschriften ohne die steuerliche Logik zu verändern. Die Entscheidung ist bewusst als Vergütungsregel zu verstehen, nicht als Steuerregel. Damit kann der Anwender zwischen Bruttopreis und Nettopreis wählen, während die Gutschrift weiterhin als 0-%-MwSt-Position behandelt wird.

Die Schirmmiete bleibt dabei technisch separiert und wird von dieser neuen Regelung nicht beeinflusst.
