# Betriebsnotiz – Statuscode-Bereinigung in billing_price

Datum: 2026-08-03

## Ausgangslage
Die vorherige Inventur zeigte, dass in billing_price weiterhin historische Statuscode-Varianten für denselben fachlichen Status vorhanden waren. Besonders auffällig waren Konfliktgruppen für Mitflieger und TD-Vereins-Schirm.

## Fachliche Entscheidung
- Mitflieger: Der korrekte Preis ist 60,00 €; Datensätze mit 50,00 € gelten als historischer Altbestand und bleiben nicht erhalten.
- TD-Vereins-Schirm in Periode 2: Der Datensatz mit Preis 0,00 € bleibt nicht erhalten; der kanonische Datensatz mit Preis -50,00 € bleibt erhalten.
- TD und TD-Vereins-Schirm bleiben immer getrennt und werden nicht zusammengeführt.

## Bereinigte Statusgruppen
- Periode 2 / Mitflieger / 1500 m
- Periode 2 / Mitflieger / 3000 m
- Periode 2 / Mitflieger / 4000 m
- Periode 7 / Mitflieger / 1500 m
- Periode 7 / Mitflieger / 3000 m
- Periode 7 / Mitflieger / 4000 m
- Periode 2 / TD-Vereins-Schirm / 1500 m
- Periode 2 / TD-Vereins-Schirm / 3000 m
- Periode 2 / TD-Vereins-Schirm / 4000 m

## Entfernte Datensätze
- Mitflieger: Datensätze mit Literal MITFLIEGER und Preis 50,00 € entfernt
- TD-Vereins-Schirm in Periode 2: historische Varianten mit Preis 0,00 € bzw. anderen nicht-kanonischen Literals entfernt

## Verbleibender Zustand
- Keine verbleibenden Konfliktgruppen
- Keine verbleibenden Dublettengruppen pro (period_id, fachlicher Status, Höhe)
- Alle Preisperioden sind konsolidiert
