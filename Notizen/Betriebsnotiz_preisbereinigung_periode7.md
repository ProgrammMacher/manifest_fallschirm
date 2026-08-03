# Betriebsnotiz – gezielte Bereinigung der Preiszeilen für Periode 7

Datum: 2026-08-03

## Anlass
Die Preisverwaltung zeigte für Periode 7 einen konkreten Fehlerfall bei den Statusgruppen TD-Vereins-Schirm und Video:
- mehrere billing_price-Zeilen existierten für denselben fachlichen Status,
- ältere Varianten wurden beim Reload über neu gespeicherte Werte gelegt,
- die KU-Basis wurde nicht stabil dargestellt,
- und die Warnung über unterschiedliche KU-Regeln erschien.

## Umfang der Maßnahme
Es wurde nur die aktuell betroffene Problembasis in Periode 7 bereinigt:
- TD-Vereins-Schirm
- Video

Nicht betroffen und bewusst unverändert blieben alle übrigen Statusgruppen.

## Entfernte Datensätze
### TD-Vereins-Schirm
Entfernt wurden die historischen Dublettensätze mit den Literals:
- TD_VEREIN_SCHIRM
- Td-Vereins-Schirm
- Td_Vereins_Schirm

Betroffene Datensatz-IDs:
- 277, 278, 279
- 280, 281, 282
- 283, 284, 285

### Video
Entfernt wurden die historischen Dublettensätze mit dem Literal:
- VIDEO

Betroffene Datensatz-IDs:
- 289, 290, 291

## Erhalten gebliebene Datensätze
### TD-Vereins-Schirm
Erhalten blieben die kanonischen Datensätze mit dem Literal:
- TD-Vereins-Schirm

Betroffene Datensatz-IDs:
- 274, 275, 276

### Video
Erhalten blieben die kanonischen Datensätze mit dem Literal:
- Video

Betroffene Datensatz-IDs:
- 295, 296, 297

## Begründung für die Auswahl der erhaltenen Datensätze
Die erhaltenen Datensätze wurden ausgewählt, weil sie:
- bereits den fachlich kanonischen Statuscode als Literal trugen,
- die aktuellen sichtbaren Preiswerte repräsentierten,
- die aktuelle KU-Basis (Netto) korrekt abbildeten,
- und damit die stabile Grundlage für die Preisverwaltung und das UI darstellten.

## Bewusst nicht veränderte Statusgruppen
Folgende Statusgruppen wurden nicht verändert:
- alle übrigen Preisstatusgruppen in Periode 7,
- ebenso alle anderen Perioden.

## Ergebnis
- pro Höhe existiert für die betroffenen Statusgruppen jetzt nur noch ein Datensatz,
- die KU-Regelwarnung ist verschwunden,
- und der Speichervorgang bleibt nach Reload stabil sichtbar.
