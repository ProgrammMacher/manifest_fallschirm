# Betriebsnotiz: Chat-Aenderungen 2026-08-05

## Kontext
Diese Notiz dokumentiert die heute im Chat umgesetzten und geprueften Aenderungen im Workspace C:/manifest_fallschirm.
Stand: 2026-08-05.

## 1) Pricing: feldweiser Lock statt Komplettabbruch
- Anpassung in der Preis-Speicherlogik: verwendete Felder werden gezielt gesperrt, nicht mehr der gesamte Speichervorgang.
- Ergebnis: nicht betroffene Felder koennen weiterhin gespeichert werden.
- Regressionstest ergaenzt und gruen.

Betroffene Dateien:
- app/routes/pricing.py
- tests/test_pricing_save_field_level_lock.py

## 2) Personensuche fuer Billing/Manual vereinheitlicht
- Suchpraedikat um E-Mail erweitert.
- API-Payload um Rechnungsadressdaten erweitert (u. a. E-Mail, Strasse, PLZ, Ort), damit Empfaengerdaten uebernommen werden koennen.

Betroffene Dateien:
- app/routes/load.py
- tests/test_manual_invoice_person_search.py

## 3) /billing/person/<id>: Empfaenger aus gespeicherten Personen uebernehmen
- Minimalinvasive UI-Funktion ergaenzt: Lookup + Uebernahme in bestehende Rechnungsadressfelder.
- Backend-Strukturen wurden dafuer nicht erweitert.

Betroffene Dateien:
- app/templates/billing/person_billing.html
- app/routes/load.py
- tests/test_manual_invoice_person_search.py

## 4) /billing/invoices: Anzeige/Filter/Sortierung auf denselben Person-Display-Wert
- Anzeigename in der Liste: billing_address_name hat Vorrang, sonst Fallback auf invoice.person.full_name.
- Filter, Suche und Sortierung wurden auf diese Anzeigequelle abgestimmt.

Betroffene Dateien:
- app/routes/billing.py
- app/templates/billing/invoice_list.html
- tests/test_invoice_split_output.py

## 5) SEPA-Compliance: abweichender Rechnungsempfaenger sperrt SEPA
- Fachregel umgesetzt: Sobald abweichende billing_address_* Felder gesetzt sind, ist SEPA fuer die Rechnung nicht zulaessig.
- Gilt zentral ueber _invoice_allows_sepa:
  - automatisches Setzen auf SEPA wird verhindert
  - manuelles Umstellen auf SEPA wird verhindert

Betroffene Dateien:
- app/services/invoice_state_service.py
- tests/test_invoice_payment_method_clear.py

## 6) /billing/persons: Split-Option nur bei positiv + negativ
- Anzeige der Option Getrennte Belege in der Personenuebersicht nur, wenn mindestens eine positive und eine negative Position vorhanden ist.
- Pruefung verwendet dieselbe Betragslogik wie die eigentliche Split-Erstellung.
- Serverseitiger Guard in der Erstellungsroute:
  - erzwungenes split_output ohne beide Vorzeichen faellt korrekt auf Einzelbeleg zurueck.

Betroffene Dateien:
- app/routes/billing.py
- app/templates/billing/persons_overview.html
- tests/test_invoice_split_output.py

## 7) UI-Wunsch Aktionen-Layout in /billing/persons
- Zwischenzeitlich wurde eine reine Darstellungsanpassung umgesetzt (vertikale Anordnung Details -> Checkbox -> Rechnung erzeugen).
- Diese konkrete UI-Aenderung wurde anschliessend rueckgaengig gemacht.
- Wichtig: Keine Logikaenderung ging dadurch verloren.

Betroffene Datei (rueckgaengig gemachte Layout-Aenderung):
- app/templates/billing/persons_overview.html

## Test- und Validierungsstand aus dem Chat
Erfolgreich ausgefuehrte Tests (laut Chatlauf):
- tests/test_pricing_save_field_level_lock.py
- tests/test_manual_invoice_person_search.py
- tests/test_invoice_split_output.py
- tests/test_invoice_payment_method_clear.py

Zusatzpruefungen:
- Fehlerpruefung fuer geaenderte Dateien: keine neuen Editor-Fehler in den zuletzt bearbeiteten Dateien.

## Hinweise zum Arbeitsbaum
- Es gibt zusaetzliche lokale Daten-/Log-Aenderungen, die nicht Teil der obigen Feature-Implementierungen sind (z. B. data/app_settings.json, data/manifest.db, logs/http_requests.log, temporaere Pruefskripte).
- Diese Notiz beschreibt die fachlichen Chat-Aenderungen an Anwendung und Tests, nicht betriebliche Laufzeitartefakte.
