# Dokumentation: Kleinunternehmer-Regelung und Preismatrix

Version: 2026-08-03

## 1. Hintergrund

Die Kleinunternehmer-Regelung wurde als konfigurierbare Regelung für bestimmte Sprung- und Leistungsstatus eingeführt. Ziel ist es, pro Status festzulegen, ob ein Eintrag als Kleinunternehmer behandelt wird und ob die Gutschrift bzw. der Rechnungsbetrag auf Basis von Brutto oder Netto berechnet werden soll.

Ziel der Regelung:

- Kleinunternehmer erhält pro Status konfigurierbar:
  - Bruttopreis
  - Nettopreis
- Die Regelung betrifft nicht nur die Rechnungsberechnung, sondern auch die Vorschau und den Rechnungssnapshot.

---

## 2. Unterstützte Status

Aktuell sind folgende Status als KU-fähig unterstützt:

- TD
- TD-Vereins-Schirm
- Video
- Aff-Lehrer

### Statusübersicht

| Status | KU-fähig | Brutto-/Netto-Basis möglich | MwSt.-Verhalten |
|---|---:|---:|---|
| TD | Ja | Ja | Regelbesteuerung oder 0 % bei KU |
| TD-Vereins-Schirm | Ja | Ja | Regelbesteuerung oder 0 % bei KU |
| Video | Ja | Ja | Regelbesteuerung oder 0 % bei KU |
| Aff-Lehrer | Ja | Ja | Regelbesteuerung oder 0 % bei KU |

Wichtiger Punkt:

- Die KU-Regelung ist nicht nur ein UI-Flag, sondern wirkt sich direkt auf die Rechnungspositionen und den Gesamtbetrag aus.
- Für neue KU-fähige Status muss immer die gesamte Berechnungskette geprüft werden.

---

## 3. Datenmodell

Die Kleinunternehmer-Regelung ist über mehrere Datenmodelle verteilt.

### Person

Die Person enthält die Stammdaten für die Default-Einstellung der KU-Regelung:

- is_tandem_kleinunternehmer
- is_video_kleinunternehmer
- is_aff_teacher_kleinunternehmer

Diese Felder bestimmen, ob eine Person beim Erstellen einer Rechnung standardmäßig die KU-Regelung für den jeweiligen Status verwendet.

### Invoice

Die Rechnung speichert den Snapshot der KU-Einstellung zum Zeitpunkt der Rechnungserstellung bzw. späterer Änderungen:

- is_tandem_kleinunternehmer
- is_video_kleinunternehmer
- is_aff_teacher_kleinunternehmer

Diese Felder sind relevant, weil die Rechnung unabhängig von späteren Stammdatenänderungen bestehen bleiben soll.

### billing_price

Die Preismatrix enthält die fachliche Konfiguration pro Status und Periode:

- status_code
- height_m
- price_eur
- ku_credit_payout_basis

Mögliche Werte von ku_credit_payout_basis:

- gross
- net

Diese Basis bestimmt, welcher Betrag als KU-Gutschrift bzw. effektiver Betrag verwendet wird. Der Aufbau der Preismatrix ist deshalb nicht nur ein technischer Detailpunkt, sondern die eigentliche fachliche Steuerung der KU-Berechnung.

---

## 4. Preislogik

Die Regelung arbeitet mit zwei unterschiedlichen Pfaden:

### Regelbesteuerung

Bei Regelbesteuerung gilt die normale Mehrwertsteuer.

Beispiel:

- Brutto: 53,55 €
- MwSt.: 19 %

Ergebnis:

- Netto: 45,00 €
- MwSt.: 8,55 €
- Brutto: 53,55 €

### Kleinunternehmer

Bei Kleinunternehmer gilt 0 % MwSt. auf die effektive Position.

#### Basis = Bruttopreis

Beispiel:

- Brutto: 53,55 €
- MwSt.: 0 %

Ergebnis:

- Betrag: 53,55 €
- MwSt.: 0,00 €

#### Basis = Nettopreis

Beispiel:

- Netto: 45,00 €
- MwSt.: 0 %

Ergebnis:

- Betrag: 45,00 €
- MwSt.: 0,00 €

Wichtige fachliche Regel:

- Die KU-Regelung darf nicht zu einer doppelten oder falschen MwSt.-Berechnung führen.
- Bei KU muss der Rechnungsbetrag zu 0 % MwSt. geführt werden, sofern die Regelung aktiv ist.

---

## 5. Backend-Ablauf

Die Berechnung läuft über mehrere Ebenen.

### Ablauf

1. Preismatrix
   - Preis wird pro Status und Höhe aus der billing_price-Matrix gelesen.
2. Statuscode
   - Status wird normalisiert, bevor Preis und MwSt. ermittelt werden.
3. Statusnormalisierung
   - historische und unterschiedliche Schreibweisen werden konsistent auf einen Canonical-Code gebracht.
4. billing_price
   - ku_credit_payout_basis wird aus der Preismatrix gelesen.
5. StatusDefinition
   - MwSt.-Satz wird über die StatusDefinition ermittelt.
6. KU-Prüfung
   - Person/Invoice-Flags bestimmen, ob der Status im aktuellen Kontext KU-relevant ist.
7. Rechnungsposition
   - Die effektive Betragssumme und die MwSt. werden für die Position berechnet.
8. Vorschau
   - Die Vorschau muss denselben effektiven Betrag wie die Rechnung zeigen.
9. Rechnung
   - Die finale Rechnung nutzt dieselbe Logik wie die Vorschau.

### Beteiligte Dateien

- billing_service.py
  - zentrale Preis- und KU-Logik
  - Berechnung von effektiven Beträgen, MwSt. und Gutschriftbasis
  - zentraler Ort für KU-Payout-Basis und effektive Positionen
- billing.py
  - Vorschau, Rechnungseditor, Detailansicht, Erzeugung von Rechnungen
  - UI und Backend-Interaktion für KU-Flags
- status_code.py
  - zentrale Statusnormalisierung und Canonical-Codes

### Besonderheit: Vorschau und Rechnung

Die Vorschau darf nicht einen abweichenden Berechnungspfad verwenden. Sie muss dieselbe Logik wie die Rechnung verwenden, weil sonst die fachliche Wahrheit der Rechnung nicht nachvollziehbar ist.

---

## 6. Durchgeführte Datenbereinigung

Während der Einführung der AFF-Lehrer-KU-Regelung wurden historische Status-Dubletten und Preismatrix-Inkonsistenzen bereinigt.

### 6.1 Bereinigung historischer Statuscode-Dubletten

Mehrere historische Schreibweisen wurden auf einen gemeinsamen Statuscode vereinheitlicht.

#### TD-Vereins-Schirm

Bereinigte Varianten:

- TD_VEREIN_SCHIRM
- Td-Vereins-Schirm
- Td_Vereins_Schirm

Konsekutiver Canonical-Code:

- TD-Vereins-Schirm

#### Video

Bereinigte Varianten:

- VIDEO
- Video

Konsekutiver Canonical-Code:

- Video

#### Mitflieger

Historische Konflikte wurden ebenfalls bereinigt.

### 6.2 Bereinigung der billing_price-Tabelle

Die billing_price-Tabelle enthielt historische Dubletten und inkonsistente Einträge, die bereinigt wurden. Ziel war es, dass ein fachlich identischer Status nicht mehrfach mit abweichender Interpretation existiert.

### Ergebnis der Datenbereinigung

- 0 verbleibende Dublettengruppen
- 0 verbleibende Konfliktgruppen

Wichtig:

- Diese Bereinigung ist fachlich notwendig, damit Preis- und MwSt.-Logik zuverlässig funktioniert.
- Ohne Konsolidierung können gleiche fachliche Status unterschiedlich interpretiert werden.

---

## 7. Gefundene Fehler während der AFF-Lehrer-Erweiterung

Während der Erweiterung um AFF-Lehrer wurden mehrere Fehler gefunden und korrigiert.

### Fehler 1: AFF-Lehrer war nicht in der KU-Logik eingebunden

Ursache:

- AFF-Lehrer wurde nicht in der gemeinsamen KU-Logik berücksichtigt.

Folge:

- Rechnungen bzw. Vorschauen für AFF-Lehrer nutzten nicht die korrekte KU-Regelung.

Lösung:

- AFF-Lehrer wurde als KU-fähiger Status in die gemeinsame Logik integriert.

### Fehler 2: Statusnormalisierung AFF-LEHRER ↔ Aff-Lehrer

Ursache:

- Die Statusnormalisierung war nicht konsistent genug, sodass AFF-LEHRER und Aff-Lehrer nicht sauber auf denselben Canonical-Code gebracht wurden.

Folge:

- Die MwSt.-Definition konnte nicht zuverlässig gefunden werden.
- VAT-Lookup war fehleranfällig und nicht zuverlässig.

Lösung:

- Die Statusnormalisierung wurde auf einen konsistenten Canonical-Code gebracht.
- Die VAT-Ermittlung nutzt jetzt den normalisierten Status zuverlässig.

### Fehler 3: Vorschau nutzte Bruttopreise direkt und ignorierte KU-Payout-Basis

Ursache:

- Die Vorschau summierte direkt die Bruttopreise, ohne die KU-Payout-Basis zu beachten.

Folge:

- Die Vorschau stimmte nicht mit der effektiven Rechnungslogik überein.

Lösung:

- Die Vorschau verwendet jetzt dieselbe effektive Berechnung wie die Rechnungslogik.

### Fehler 4: Regression bei TD/Video durch fehlerhaften KU-Payout-Fallback

Ursache:

- Ein Fallback-Pfad für negative Preiswerte wurde zu aggressiv verwendet und überschreib die korrekte KU-Payout-Logik.

Folge:

- TD und Video wurden im KU-Payout-Pfad falsch berechnet.

Lösung:

- Der Fallback wurde so angepasst, dass negative Preiswerte nicht irreversibel korrumpiert werden.
- TD/Video sind wieder korrekt berechnet.

### Fehler 5: Ursprünglicher Fehler im Gesamtverständnis der KU-Logik

Ursache:

- Die KU-Regelung war zunächst nicht als zentrale Rechnungslogik verstanden worden, sondern eher als UI- oder Einzel-Status-Problem.

Folge:

- Die richtige Stelle für die Lösung war nicht sofort klar und verschiedene Teilbereiche mussten korrigiert werden.

Lösung:

- Die KU-Logik wurde als zentrale fachliche Berechnung verstanden und in Vorschau, Rechnung und Snapshot konsistent behandelt.

---

## 8. Wichtige Regeln für zukünftige Änderungen

Bei jeder Erweiterung der KU-Regelung sind folgende Punkte zwingend zu prüfen:

### Datenmodell

Bei neuen KU-fähigen Status immer prüfen:

- Personenmodell
- Invoice-Snapshot
- Migration

### Backend

Immer prüfen:

- billing_service.py
- status_code.py
- billing.py

### Vorschau und Rechnung

Neue Status dürfen niemals nur in der UI ergänzt werden. Es muss immer auch geprüft werden:

- Vorschau
- Rechnungsberechnung
- Snapshot
- Tests

### Rechnungseditor und Detailansicht

Wenn ein neuer Status KU-fähig wird, müssen zusätzlich geprüft werden:

- Rechnungseditor
- Detailansicht
- Vorschau

### Regressionstests

Für jeden neuen oder geänderten KU-fähigen Status müssen Tests ergänzt oder angepasst werden.

### Fachliche Grundregel

Wenn ein neuer Status KU-fähig wird, ist nicht nur die UI-Anzeige relevant, sondern die gesamte fachliche Kette aus Preismatrix, Statusnormalisierung, VAT-Ermittlung, Vorschau und Rechnung.

---

## 9. Testfälle

Für jeden KU-fähigen Status sind folgende Pflicht-Tests erforderlich:

- Regelbesteuerung
- Kleinunternehmer
- Bruttopreis
- Nettopreis
- Vorschau
- Rechnung
- Rechnungseditor

### Beispielwerte und erwartete Ergebnisse

#### TD

- Regelbesteuerung: 19 % MwSt.
- KU-Bruttopreis: 0 % MwSt., Betrag = Bruttopreis
- KU-Nettopreis: 0 % MwSt., Betrag = Nettopreis
- Vorschau: muss dieselben Werte wie die Rechnung zeigen

#### Video

- Regelbesteuerung: 19 % MwSt.
- KU-Bruttopreis: 0 % MwSt., Betrag = Bruttopreis
- KU-Nettopreis: 0 % MwSt., Betrag = Nettopreis
- Vorschau: muss dieselben Werte wie die Rechnung zeigen

#### Aff-Lehrer

- Regelbesteuerung: 19 % MwSt.
- KU-Bruttopreis: 0 % MwSt., Betrag = Bruttopreis
- KU-Nettopreis: 0 % MwSt., Betrag = Nettopreis
- Vorschau: muss dieselben Werte wie die Rechnung zeigen

Wichtig:

- Die Testfälle dürfen nicht nur die UI prüfen, sondern müssen die tatsächliche Berechnung abdecken.

---

## 10. Abschluss

Die Kleinunternehmer-Regelung ist jetzt für TD, TD-Vereins-Schirm, Video und Aff-Lehrer implementiert und abgesichert.

Die wichtigsten Ergebnisse der Umsetzung waren:

- AFF-Lehrer-KU eingeführt
- Vorschau korrigiert
- Rechnungsberechnung korrigiert
- Statuscode-Dubletten bereinigt
- Datenbestand konsolidiert
- Regressionstests ergänzt

Ziel dieser Dokumentation ist es, zukünftigen Entwicklern zu zeigen, dass die KU-Regelung nicht nur eine UI-Funktion ist, sondern eine fachlich relevante, datenmodellgebundene und testpflichtige Regelung mit weitreichenden Auswirkungen auf Vorschau, Rechnung und Datenintegrität.
