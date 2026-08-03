# Betriebsnotiz: AFF-Lehrer-Kleinunternehmer-Erweiterung und Datenbereinigung

Version: 2026-08-03

## 1. Ziel der Erweiterung

Im Rahmen der Kleinunternehmer-Erweiterung wurde die KU-Brutto-/Netto-Regelung auf einen weiteren fachlich relevanten Status erweitert: Aff-Lehrer.

Ziel war es, dass AFF-Lehrer nicht mehr wie ein normaler regulärer Status behandelt wird, sondern genau wie andere KU-fähige Status:

- die KU-Logik verwenden kann,
- über die Preismatrix gesteuert wird,
- in Vorschau und Rechnung dieselbe effektive Berechnung nutzt,
- und zuverlässig mit der Statusnormalisierung und VAT-Ermittlung arbeitet.

---

## 2. Einführung der KU-Brutto-/Netto-Regelung

Die Kleinunternehmer-Regelung wurde als konfigurierbare fachliche Regel eingeführt. Sie ist nicht nur ein UI-Feature, sondern ein zentraler Teil der Rechnungserstellung und Vorschau.

Grundidee:

- Ein Status kann als Kleinunternehmer-fähig markiert sein.
- Für diesen Status kann die Gutschrift bzw. der effektive Betrag entweder auf Basis von:
  - Bruttopreis, oder
  - Nettopreis
  berechnet werden.

Diese Konfiguration wird über die Preismatrix gesteuert.

### Fachliche Bedeutung

Die Regelung wirkt sich direkt auf:

- Rechnungspositionen,
- Vorschau-Beträge,
- MwSt.-Berechnung,
- KU-Payout-Basis,
- den späteren Rechnungssnapshot.

---

## 3. Unterstützte Status

Die KU-Regelung ist für folgende Status umgesetzt:

- TD
- TD-Vereins-Schirm
- Video
- Aff-Lehrer

### Bedeutung dieser Status

Diese Status sind im fachlichen Kontext relevant, weil sie:

- als Sprungpositionen auftreten können,
- unterschiedliche steuerliche Behandlung erfordern,
- und in der Preismatrix eigene Konfigurationen haben können.

---

## 4. Datenmodell und Speicherung

### Personenmodell

Die Person enthält die Default-Flags für die KU-Einstellung:

- is_tandem_kleinunternehmer
- is_video_kleinunternehmer
- is_aff_teacher_kleinunternehmer

Diese Flags wirken als Stammdaten-Voreinstellung bei der Rechnungserstellung.

### Invoice-Snapshot

Die Rechnung speichert die KU-Einstellungen zum Zeitpunkt der Rechnungsentstehung bzw. späterer Änderungen:

- is_tandem_kleinunternehmer
- is_video_kleinunternehmer
- is_aff_teacher_kleinunternehmer

Das ist wichtig, weil spätere Änderungen an der Person nicht automatisch die historische Rechnung verändern dürfen.

### billing_price

Die Preismatrix enthält die fachliche Definition für die KU-Basis:

- ku_credit_payout_basis

Mögliche Werte:

- gross
- net

Diese Basis ist der zentrale fachliche Schalter für die effektive KU-Berechnung.

---

## 5. Preislogik und Berechnung

### Regelbesteuerung

Bei Regelbesteuerung gilt der normale MwSt.-Satz.

Beispiel:

- Brutto: 53,55 €
- MwSt.: 19 %

Ergebnis:

- Netto: 45,00 €
- MwSt.: 8,55 €
- Brutto: 53,55 €

### Kleinunternehmer

Bei KU gilt für die betroffene Position 0 % MwSt.

#### Basis = Bruttopreis

- Betrag = Bruttopreis
- MwSt. = 0 %

#### Basis = Nettopreis

- Betrag = Netto
- MwSt. = 0 %

### Wichtig

Die KU-Berechnung darf niemals zu einer falschen MwSt.-Berechnung oder einer inkonsistenten Summe führen.

---

## 6. Vorschau-Logik

Die Vorschau war ein zentraler Problemfall, weil sie anfänglich nicht dieselbe Logik wie die Rechnung verwendete.

### Ausgangslage

Die Vorschau hat zunächst direkt die Bruttopreise aus der Preismatrix summiert.

### Problem

Damit wurde die KU-Payout-Basis vollständig ignoriert. Das führte dazu, dass die Vorschau nicht die gleichen Werte wie die Rechnung anzeigte.

### Folge

- Die Vorschau war fachlich nicht belastbar.
- Ein Entwickler konnte die Rechnung nicht sicher anhand der Vorschau beurteilen.
- Das Verhalten war besonders problematisch bei Aff-Lehrer, weil dort die KU-Regelung neu eingeführt wurde.

### Reparatur

Die Vorschau wurde so angepasst, dass sie die gleiche effektive Berechnung verwendet wie die Rechnungslogik.

Wichtig:

- Vorschau und Rechnung müssen heute denselben Berechnungspfad verwenden.
- Nur so kann gewährleistet werden, dass die gezeigten Werte wirklich mit dem späteren Rechnungsergebnis übereinstimmen.

---

## 7. Rechnungslogik

Die Rechnungslogik verwendet die gleiche fachliche Basis wie die Vorschau.

### Ablauf bei Rechnungserzeugung

1. Status wird normalisiert.
2. KU-Flag wird geprüft.
3. Preismatrix wird ausgewertet.
4. ku_credit_payout_basis wird berücksichtigt.
5. Effektive Position wird berechnet.
6. MwSt. wird entsprechend gesetzt.
7. Rechnungssnapshot wird gespeichert.

### Bedeutung des Snapshots

Die Rechnung enthält die fachliche Entscheidung der Zeit der Erstellung. Auch wenn sich spätere Stammdaten ändern, muss die Rechnung stabil bleiben.

---

## 8. Statuscode-Normalisierung

Die Statuscode-Normalisierung ist essenziell, weil die fachliche Bedeutung von Statuscodes nicht nur von der Schreibweise, sondern auch von der Konsistenz abhängt.

### Problemstellung

Historisch wurden Statuscodes in unterschiedlichen Schreibweisen verwendet, etwa:

- TD
- TD-Vereins-Schirm
- Video
- AFF-LEHRER
- Aff-Lehrer
- Td-Vereins-Schirm
- Td_Vereins_Schirm
- VIDEO

### Konsequenz

Ohne Normalisierung wird:

- die Preismatrix nicht zuverlässig gefunden,
- VAT nicht korrekt ermittelt,
- und die KU-Logik falsch oder gar nicht angesteuert.

### Reparatur

Die Normalisierung wurde auf einen konsistenten Canonical-Code gebracht.

Dadurch konnte sichergestellt werden, dass:

- derselbe fachliche Status in allen Teilen des Systems gleich behandelt wird,
- die VAT-Ermittlung zuverlässig funktioniert,
- und die KU-Berechnung nicht an Schreibweise scheitert.

---

## 9. Durchgeführte Datenbereinigung

Im Rahmen der Erweiterung wurde eine gezielte Datenbereinigung durchgeführt, um historische Inkonsistenzen zu beseitigen.

### Ziel

Die Datenbank sollte fachlich sauber und konsistent werden, damit unterschiedliche Varianten desselben Status nicht mehr als getrennte Zustände behandelt werden.

### Bereinigte historischer billing_price-Dubletten

Die Preismatrix enthielt historische Dubletten und inkonsistente Varianten, die bereinigt wurden.

Beispiele:

#### TD-Vereins-Schirm

Bereinigte Varianten:

- TD_VEREIN_SCHIRM
- Td-Vereins-Schirm
- Td_Vereins_Schirm

Zielzustand:

- TD-Vereins-Schirm

#### Video

Bereinigte Varianten:

- VIDEO
- Video

Zielzustand:

- Video

### Ergebnis der Bereinigung

- 0 verbleibende Dublettengruppen
- 0 verbleibende Konfliktgruppen

### Wichtigkeit der Bereinigung

Ohne diese Datenbereinigung wäre die KU-Logik nicht zuverlässig gewesen, weil dieselben fachlichen Status mehrfach mit leicht abweichenden Codes im System aufgetreten wären.

---

## 10. AFF-Lehrer-Erweiterung

Die AFF-Lehrer-Erweiterung war der eigentliche Auslöser für die komplette Prüfung der KU-Regelung.

### Ausgangslage

AFF-Lehrer war in der bestehenden KU-Logik nicht vollständig berücksichtigt.

### Folgen

- AFF-Lehrer wurde nicht wie die anderen KU-fähigen Status behandelt.
- Die VAT-Ermittlung konnte bei bestimmten Statusvarianten nicht zuverlässig funktionieren.
- Die Vorschau war nicht konsistent.

### Implementierte Anpassungen

Die Erweiterung um AFF-Lehrer umfasste:

- Aufnahme in die KU-fähigen Status,
- Anpassung der Statusnormalisierung,
- Umsetzung der gemeinsamen Berechnung in Vorschau und Rechnung,
- Anpassung der Regressionstests,
- Prüfung der VAT-Ermittlung und des KU-Payout-Pfades.

---

## 11. Gefundene Fehler und Ursachen

Im Verlauf der Erweiterung wurden mehrere Fehler gefunden.

### Fehler 1: AFF-Lehrer war nicht in der KU-Logik eingebunden

Ursache:

- AFF-Lehrer war nicht in der gemeinsamen KU-Logik abgedeckt.

Folge:

- Der Status wurde nicht wie TD/Video behandelt.

Reparatur:

- AFF-Lehrer wurde in die gemeinsame KU-Logik aufgenommen.

### Fehler 2: Fehlerhafte Statusnormalisierung

Ursache:

- AFF-LEHRER und Aff-Lehrer wurden nicht sauber auf denselben Canonical-Code gemappt.

Folge:

- VAT-Lookup konnte den relevanten Status nicht zuverlässig finden.

Reparatur:

- Die Normalisierung wurde konsistent auf den fachlich richtigen Canonical-Code gebracht.

### Fehler 3: Vorschau verwendete die falsche Berechnung

Ursache:

- Die Vorschau summierte direkte Bruttopreise und ignorierte die KU-Payout-Basis.

Folge:

- Die Vorschau zeigte nicht denselben effektiven Betrag wie die Rechnung.

Reparatur:

- Die Vorschau verwendet jetzt dieselbe effektive Berechnung wie die Rechnung.

### Fehler 4: KU-Payout-Pfad war nicht robust genug

Ursache:

- Der KU-Payout-Pfad wurde bei negativen Preiswerten fehlerhaft behandelt.

Folge:

- TD und Video konnten im KU-Pfad falsch berechnet werden.

Reparatur:

- Der Fallback- und Payout-Pfad wurde korrigiert, sodass negative Preiswerte nicht zur fehlerhaften Überschreibung der effektiven Berechnung führen.

### Fehler 5: Regression bei bestehender Rechnungskonsistenz

Ursache:

- Änderungen an der KU-Logik wurden zunächst an einer Stelle umgesetzt, aber nicht überall durchgängig auf Vorschau und Rechnung übertragen.

Folge:

- Die fachliche Konsistenz war nicht gewährleistet.

Reparatur:

- Die Berechnung wurde zentralisiert und in Vorschau und Rechnung auf denselben Pfad gelegt.

---

## 12. Durchgeführte Reparaturen

Die folgenden Reparaturen wurden umgesetzt:

- AFF-Lehrer in die KU-Logik integriert
- Statusnormalisierung konsolidiert
- VAT-Lookup auf normalisierten Status umgestellt
- Vorschau auf dieselbe effektive Rechenlogik wie Rechnung gebracht
- KU-Payout-Pfad für negative Werte stabilisiert
- Datenbereinigung der historischen Status-Dubletten abgeschlossen
- Regressionstests für Vorschau, Rechnung und AFF-Lehrer ergänzt

Diese Reparaturen sind als fachlich notwendig zu verstehen und nicht bloß als technische Optimierung.

---

## 13. Regressionstests

Für die KU-Erweiterung wurden gezielte Regressionstests ergänzt.

### Abgedeckte Bereiche

- Regelbesteuerung
- Kleinunternehmer
- Bruttopreis
- Nettopreis
- Vorschau
- Rechnung
- Rechnungseditor
- AFF-Lehrer-Spezifika
- Statusnormalisierung
- KU-Payout-Basis

### Wichtige Testprinzipien

Die Tests dürfen nicht nur die UI prüfen. Sie müssen die eigentliche Berechnung abbilden, insbesondere:

- effektive Positionen,
- MwSt.-Sätze,
- KU-Payout-Basis,
- Vorschau und Rechnung.

---

## 14. Wichtige Regeln für zukünftige Erweiterungen

Für jede zukünftige Erweiterung der KU- oder Preismatrix-Logik gelten folgende Regeln:

### 1. Neue Status niemals nur in der UI ergänzen

Ein neuer KU-fähiger Status muss immer in der vollständigen Berechnungskette berücksichtigt werden.

### 2. Vorschau und Rechnung müssen identisch sein

Die Vorschau muss dieselbe logische Berechnung verwenden wie die erzeugte Rechnung. Nur so kann die fachliche Wahrheit zuverlässig dargestellt werden.

### 3. Statusnormalisierung ist zwingend

Jeder neue Status muss sauber normalisiert und in der Statusdefinition abgebildet werden.

### 4. Preismatrix und VAT-Lookup müssen zusammen geprüft werden

Wenn ein Status in der Preismatrix auftaucht, muss auch die VAT-Ermittlung und die KU-Basis geprüft werden.

### 5. Datenbereinigung gehört zur fachlichen Umsetzung

Historische Dubletten und Inkonsistenzen dürfen nicht einfach ignoriert werden. Sie müssen bereinigt werden, damit die fachliche Logik zuverlässig funktioniert.

### 6. Regressionstests sind Pflicht

Bei jeder Änderung an KU-fähigen Status oder Preislogik müssen die Regressionstests überprüft und bei Bedarf ergänzt werden.

---

## 15. Abschluss

Die AFF-Lehrer-KU-Erweiterung war nicht nur eine Erweiterung um einen zusätzlichen Status, sondern ein Testfall für die gesamte Konsistenz der KU-Logik.

Die wesentlichen Erkenntnisse sind:

- KU-Regelung ist ein fachlicher, datenmodellgebundener Prozess und kein rein visueller Schalter.
- Vorschau und Rechnung müssen dieselbe effektive Berechnung nutzen.
- Statusnormalisierung und VAT-Lookup sind kritisch für die korrekte Verarbeitung.
- Historische Datenbereinigung ist notwendig, um die Fachlogik stabil zu machen.
- Die Erweiterung wurde erfolgreich abgeschlossen, dokumentiert und durch Regressionstests abgesichert.

Diese Betriebsnotiz soll langfristig sicherstellen, dass zukünftige Entwickler die komplette Historie, die fachlichen Regeln und die getroffenen Reparaturen nachvollziehen können.
