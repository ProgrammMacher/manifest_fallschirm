# E2E-Smoketest-Plan: Abrechnung, Rechnungsübersicht, Export, Import (inkl. AFF)

**Version:** 1.0 · **Datum:** 04.05.2026  
**Geltungsbereich:** Vollständiger manueller Smoketest nach Code-Änderungen im Bereich Abrechnung, AFF-Logik, Personen-Export/Import  
**Geschätzte Durchlaufzeit:** 90–120 Minuten  

---

## 1. Voraussetzungen

| # | Bedingung |
|---|-----------|
| P1 | Applikation läuft lokal (`run.py` oder `Flask_start_manifest.bat`) |
| P2 | Datenbank hat mindestens eine aktive Preismatrix mit Preisen für alle genutzten Status |
| P3 | Orga-Pauschale ist in der aktiven Preismatrix konfiguriert |
| P4 | `BillingConfig` enthält Schirmmiete-Preise für Verein, Gast, Partner-Verein, Tandemmaster |
| P5 | Admin-Login ist möglich |

---

## 2. Testdaten anlegen (einmalig)

### 2.1 Personen

| ID | Name (Beispiel) | Flags |
|----|-----------------|-------|
| T-P1 | Müller, Anna | `is_aff_teacher=true` |
| T-P2 | Schmidt, Ben | `is_aff_student=true` |
| T-P3 | Weber, Clara | `is_aff_student=true` |
| T-P4 | Koch, Dieter | `is_member=true` (Verein) |
| T-P5 | Braun, Eva | Gast (keine Flags) |
| T-P6 | Wolf, Felix | `is_partner_verein=true` |
| T-P7 | Klein, Georg | `is_tandemmaster=true` |
| T-P8 | Groß, Hanna | `is_tandem_guest=true` |

### 2.2 Loads (Status `completed`, mit Preismodell)

| Load | Sitze | Erwartetes Ergebnis beim Speichern |
|------|-------|-------------------------------------|
| L1 | 1× Schueler-Aff-1 (T-P2) + 1× Aff-Lehrer (T-P1), H=4000 | ✅ Speichern OK |
| L2 | 1× Schueler-Aff-2 (T-P3) + 2× Aff-Lehrer (T-P1 + T-P4), H=4000 | ✅ Speichern OK |
| L3 | 1× Schueler-Aff-2 (T-P3) + 1× Aff-Lehrer (T-P1), H=4000 | ❌ Save-Block: zu wenige AFF-Lehrer |
| L4 | 1× Aff-Lehrer (T-P1) ohne AFF-Schüler, H=3000 | ❌ Save-Block: AFF-Lehrer ohne AFF-Schüler |
| L5 | T-P4 (Verein) + T-P5 (Gast) + T-P6 (Partner) + T-P7 (TD) + T-P8 (G-TD), H=1500, jeweils Schirmmiete aktiviert | ✅ Speichern OK |
| L6 | T-P2 (AFF-Schüler) mit Schirmmiete-Flag gesetzt, H=4000 | Schirmmiete wird serverseits verworfen |

---

## 3. Testlauf A – Load-Validierung

| TF | Schritt | Erwartetes Ergebnis | Ist-Ergebnis | Status |
|----|---------|---------------------|--------------|--------|
| A-01 | L1 speichern | Gespeichert, keine Fehlermeldung | | ☐ |
| A-02 | L2 speichern | Gespeichert, keine Fehlermeldung | | ☐ |
| A-03 | L3 Speichern versuchen | Fehlermeldung „Schüler-AFF-2-Lehrer erfordert zwei AFF-Lehrer", kein Commit | | ☐ |
| A-04 | L4 Speichern versuchen | Fehlermeldung „AFF-Lehrer erfordert mindestens einen AFF-Schüler", kein Commit | | ☐ |
| A-05 | L5 speichern | Gespeichert, Schirmmiete-Flags für T-P4/T-P7 erhalten | | ☐ |
| A-06 | L6: AFF-Schüler mit Schirmmiete → speichern | Schirmmiete für AFF-Schüler nach Speichern nicht gesetzt (server-seitig geleert) | | ☐ |
| A-07 | L5 im Editor: Schirmmiete für G-TD-Gast aktivieren → speichern | Schirmmiete für Tandemgast wird serverseitig verworfen | | ☐ |

---

## 4. Testlauf B – Abrechnung

### B.1 Personenübersicht

| TF | Schritt | Erwartetes Ergebnis | Ist-Ergebnis | Status |
|----|---------|---------------------|--------------|--------|
| B-01 | `/billing/persons` öffnen | Personen T-P1 bis T-P8 mit offenen Einträgen erscheinen | | ☐ |
| B-02 | Summe für T-P4 (Verein, L5) prüfen | Sprung-Betrag (1500m Verein aus Preismatrix) + Schirmmiete (falls max_count > 0) + ggf. Orga | | ☐ |
| B-03 | Summe für T-P2 (AFF-Schüler, L1) prüfen | Nur Sprungbetrag, keine Schirmmiete | | ☐ |
| B-04 | Summe für T-P7 (TD, L5) prüfen | Sprungbetrag + Schirmmiete Tandemmaster | | ☐ |

### B.2 Rechnungen erstellen

| TF | Schritt | Erwartetes Ergebnis | Ist-Ergebnis | Status |
|----|---------|---------------------|--------------|--------|
| B-05 | Rechnung für T-P2 erstellen (AFF-Schüler, aus L1) | Sprungposition Schueler-Aff-1 vorhanden; keine Schirmmietposition | | ☐ |
| B-06 | Rechnung für T-P4 erstellen (Verein, aus L5) | Sprungposition Verein, Schirmmiete-Position (wenn aktiviert) vorhanden | | ☐ |
| B-07 | Rechnung für T-P7 erstellen (TD, aus L5) | Sprungposition TD, Schirmmiete TM vorhanden | | ☐ |
| B-08 | MwSt-Probe für alle Rechnungen | Netto + MwSt = Brutto (keine Rundungsdifferenz > 0,01 €) | | ☐ |
| B-09 | Orga-Position prüfen | Orga genau einmal pro Periode pro Person, nicht doppelt | | ☐ |

---

## 5. Testlauf C – Rechnungsübersicht

| TF | Schritt | Erwartetes Ergebnis | Ist-Ergebnis | Status |
|----|---------|---------------------|--------------|--------|
| C-01 | `/billing/invoices` öffnen | Alle erstellten Rechnungen sichtbar | | ☐ |
| C-02 | Filter „Status: Offen" | Nur unbezahlte Rechnungen | | ☐ |
| C-03 | Filter „Status: Bezahlt" | Nur bezahlte Rechnungen (zunächst leer) | | ☐ |
| C-04 | Rechnung B-05 als „Bar" bezahlt markieren | Status wechselt zu Bezahlt, Zahlungsart „Bar" erscheint | | ☐ |
| C-05 | Filter „Bezahlart: Bar" | Nur gerade bezahlte Rechnung | | ☐ |
| C-06 | Personensuche (z. B. „Schmidt") | Nur T-P2-Rechnung sichtbar | | ☐ |
| C-07 | Sortierung „Betrag absteigend" | Rechnungen korrekt nach Gesamtbetrag sortiert | | ☐ |
| C-08 | Sortierung „Datum aufsteigend" | Älteste Rechnung zuerst | | ☐ |

---

## 6. Testlauf D – Exporte

### D.1 Archiv-Export CSV

| TF | Schritt | Erwartetes Ergebnis | Ist-Ergebnis | Status |
|----|---------|---------------------|--------------|--------|
| D-01 | `/loads/archive/export.csv` herunterladen | CSV enthält alle abgeschlossenen Loads (L1, L2, L5) | | ☐ |
| D-02 | CSV in Excel öffnen | Semikolon-Trennung, UTF-8-BOM, keine Kodierungsfehler | | ☐ |
| D-03 | Spalte „Status" prüfen | Enthält `Schueler-Aff-1`, `Schueler-Aff-2`, `Aff-Lehrer`, `Verein`, `TD` usw. | | ☐ |
| D-04 | Spalten `gear_rental`, `billed`, `paid` | Werte „Ja" / „Nein" korrekt | | ☐ |

### D.2 Archiv-Export XLSX

| TF | Schritt | Erwartetes Ergebnis | Ist-Ergebnis | Status |
|----|---------|---------------------|--------------|--------|
| D-05 | `/loads/archive/export.xlsx` herunterladen | XLSX öffnet fehlerfrei | | ☐ |
| D-06 | Fachliche Inhalte | Identisch zum CSV-Export | | ☐ |
| D-07 | Formatierung | Kopfzeile fett, Spaltenbreiten sinnvoll | | ☐ |

### D.3 Preislisten-PDF

| TF | Schritt | Erwartetes Ergebnis | Ist-Ergebnis | Status |
|----|---------|---------------------|--------------|--------|
| D-08 | `/pricing/price-list.pdf` herunterladen | PDF wird erzeugt (kein 500-Fehler) | | ☐ |
| D-09 | Reihenfolge AFF in PDF-Matrix | Aff-Lehrer unter Lehrer; Schueler-Aff-2 unter Schüler GK 6; Schueler-Aff-1 unter Schueler-Aff-2 | | ☐ |

### D.4 Rechnungs-PDF

| TF | Schritt | Erwartetes Ergebnis | Ist-Ergebnis | Status |
|----|---------|---------------------|--------------|--------|
| D-10 | PDF für Rechnung B-05 (AFF-Schüler) | PDF öffnet, kein Modal-/Overlay-Text im Dokument | | ☐ |
| D-11 | PDF für Rechnung B-06 (Verein) | Positionen und Gesamtbetrag stimmen mit UI überein | | ☐ |
| D-12 | PDF für Rechnung B-07 (TM) | Schirmmiete-Position im PDF vorhanden | | ☐ |

### D.5 Personen-Export XLSX

| TF | Schritt | Erwartetes Ergebnis | Ist-Ergebnis | Status |
|----|---------|---------------------|--------------|--------|
| D-13 | `/export/persons/excel` herunterladen | XLSX enthält Spalten „AFF-Lehrer" und „Schüler-AFF" | | ☐ |
| D-14 | T-P1 (AFF-Lehrer) in XLSX | Spalte „AFF-Lehrer" = „ja" | | ☐ |
| D-15 | T-P2/T-P3 (AFF-Schüler) in XLSX | Spalte „Schüler-AFF" = „ja" | | ☐ |
| D-16 | T-P4 (Verein) in XLSX | Beide AFF-Spalten = „nein" | | ☐ |

---

## 7. Testlauf E – Import

### E.1 Vertikaler Import (Standardvorlage, ohne AFF-Spalten)

| TF | Schritt | Erwartetes Ergebnis | Ist-Ergebnis | Status |
|----|---------|---------------------|--------------|--------|
| E-01 | Vorlage herunterladen (`/import/vorlage`) | XLSX ohne AFF-Spalten | | ☐ |
| E-02 | 2 neue Personen eintragen (ohne AFF) | Vorschau zeigt beide Personen ohne Fehler | | ☐ |
| E-03 | Import ausführen | Beide Personen angelegt, kein Fehler | | ☐ |
| E-04 | Selbe Datei erneut hochladen | Duplikate erkannt, Vorschau zeigt Merge-Kandidaten | | ☐ |

### E.2 Horizontaler Import (Export-XLSX mit AFF-Spalten)

| TF | Schritt | Erwartetes Ergebnis | Ist-Ergebnis | Status |
|----|---------|---------------------|--------------|--------|
| E-05 | Personen-XLSX aus D-13 hochladen (Modus: horizontal) | Vorschau zeigt alle Personen | | ☐ |
| E-06 | T-P1 (AFF-Lehrer=ja) in Vorschau | Spalte AFF-Lehrer erkannt, Wert „ja" | | ☐ |
| E-07 | T-P2 (Schüler-AFF=ja) in Vorschau | Spalte Schüler-AFF erkannt, Wert „ja" | | ☐ |
| E-08 | Import ausführen | Bestehende Personen gemergt (kein Duplikat neu angelegt) | | ☐ |
| E-09 | T-P1 nach Import in Personendetail öffnen | `is_aff_teacher = True` erhalten | | ☐ |
| E-10 | T-P2 nach Import in Personendetail öffnen | `is_aff_student = True` erhalten | | ☐ |

### E.3 AFF-Flag-Änderung im Merge

| TF | Schritt | Erwartetes Ergebnis | Ist-Ergebnis | Status |
|----|---------|---------------------|--------------|--------|
| E-11 | XLSX: T-P1 AFF-Lehrer auf „nein" ändern → hochladen (horizontal) | Vorschau zeigt Konflikt-Feld „AFF-Lehrer: Alt=Ja / Neu=Nein" | | ☐ |
| E-12 | In Vorschau „Bisheriger Wert behalten" wählen → Import | T-P1 bleibt AFF-Lehrer | | ☐ |
| E-13 | In Vorschau „Importwert übernehmen" wählen → Import | T-P1 ist kein AFF-Lehrer mehr | | ☐ |
| E-14 | Re-Check: T-P1 in neuem Load als Aff-Lehrer einsetzen | Load-Editor bietet Aff-Lehrer-Status nur wenn `is_aff_teacher=true` | | ☐ |

---

## 8. Abnahmekriterien (Go/No-Go)

| Kriterium | Bedingung |
|-----------|-----------|
| ✅ AFF-Blockspeicher | Kein Save von L3/L4 (ungültige AFF-Konstellationen) |
| ✅ Schirmmiete | AFF-Schüler, Tandemgast, Mitflieger, Schüler erhalten keine Schirmmiete |
| ✅ Rechnungsbeträge | Brutto = Netto + MwSt in UI, PDF und Export |
| ✅ AFF-Export | Personen-XLSX enthält AFF-Spalten mit korrekten Werten |
| ✅ AFF-Import horizontal | AFF-Flags werden erkannt, gemergt und gespeichert |
| ✅ Vertikaler Import | Bleibt ohne AFF-Spalten stabil und fehlerfrei |
| ✅ PDF-Qualität | Keine UI-Artefakte, keine Modal-Texte in Rechnungs-PDFs |
| ✅ Preislisten-PDF | AFF-Zeilen korrekt einsortiert |

---

## 9. Protokoll

**Tester:** ___________________________  
**Datum:** ___________________________  
**App-Version / Commit:** ___________________________  
**DB-Stand:** ___________________________  

| Gesamt bestanden | Gesamt fehlgeschlagen | Offen/Übersprungen |
|-----------------|----------------------|-------------------|
|  |  |  |

**Besondere Beobachtungen:**

```
(frei)
```

**Freigabe:** ☐ Go  ☐ No-Go  
**Unterschrift:** ___________________________
