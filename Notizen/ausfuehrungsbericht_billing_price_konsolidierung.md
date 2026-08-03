# Ausf?hrungsbericht ? vollst?ndige Bereinigung von billing_price-Statuscodes

Erstellt am: 2026-08-03

## Ziel

- Alle historischen Schreibweisen desselben fachlichen Statuscodes in billing_price auf den kanonischen Statuscode normalisieren.
- TD und TD-Vereins-Schirm niemals zusammenf?hren.
- Nur unterschiedliche Schreibweisen desselben fachlichen Status vereinheitlichen.

## Zusammenfassung
- Anzahl betroffener Gruppen mit mehreren Status-Varianten: 78
- Insgesamt analysierte Preiszeilen: 285
- Konfiktfallkriterium: unterschiedliche Preise oder unterschiedliche KU-Basiswerte innerhalb derselben Gruppe.

## Vorschlag f?r die Beibehaltung

- Behalten wird der Datensatz, der bereits den kanonischen Statuscode als Literal tr?gt.
- Falls mehrere solche Datens?tze existieren, wird der Datensatz mit der h?chsten ID bevorzugt.
- Bei widerspr?chlichen Preisen oder KU-Basiswerten wird der Fall als Konflikt markiert und nicht automatisch ?berschrieben.

## Betroffene Gruppen

### Periode 2 ? Auffüller Gast / H?he 1500 m
- Literale Varianten: AUFFUELLER_GAST, Auffüller Gast
- Preise: 25.00
- KU-Basis: gross
- Behalten wird ID 7 (Auffüller Gast, Preis 25.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 1 => AUFFUELLER_GAST / Preis 25.00 / KU gross; ID 7 => Auffüller Gast / Preis 25.00 / KU gross

### Periode 2 ? Auffüller Gast / H?he 3000 m
- Literale Varianten: AUFFUELLER_GAST, Auffüller Gast
- Preise: 25.00
- KU-Basis: gross
- Behalten wird ID 8 (Auffüller Gast, Preis 25.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 2 => AUFFUELLER_GAST / Preis 25.00 / KU gross; ID 8 => Auffüller Gast / Preis 25.00 / KU gross

### Periode 2 ? Auffüller Gast / H?he 4000 m
- Literale Varianten: AUFFUELLER_GAST, Auffüller Gast
- Preise: 28.00
- KU-Basis: gross
- Behalten wird ID 9 (Auffüller Gast, Preis 28.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 3 => AUFFUELLER_GAST / Preis 28.00 / KU gross; ID 9 => Auffüller Gast / Preis 28.00 / KU gross

### Periode 2 ? Auffüller Verein / H?he 1500 m
- Literale Varianten: AUFFUELLER_VEREIN, Auffüller Verein
- Preise: 22.00
- KU-Basis: gross
- Behalten wird ID 13 (Auffüller Verein, Preis 22.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 4 => AUFFUELLER_VEREIN / Preis 22.00 / KU gross; ID 13 => Auffüller Verein / Preis 22.00 / KU gross

### Periode 2 ? Auffüller Verein / H?he 3000 m
- Literale Varianten: AUFFUELLER_VEREIN, Auffüller Verein
- Preise: 22.00
- KU-Basis: gross
- Behalten wird ID 14 (Auffüller Verein, Preis 22.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 5 => AUFFUELLER_VEREIN / Preis 22.00 / KU gross; ID 14 => Auffüller Verein / Preis 22.00 / KU gross

### Periode 2 ? Auffüller Verein / H?he 4000 m
- Literale Varianten: AUFFUELLER_VEREIN, Auffüller Verein
- Preise: 25.00
- KU-Basis: gross
- Behalten wird ID 15 (Auffüller Verein, Preis 25.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 6 => AUFFUELLER_VEREIN / Preis 25.00 / KU gross; ID 15 => Auffüller Verein / Preis 25.00 / KU gross

### Periode 2 ? G-TD / H?he 1500 m
- Literale Varianten: G-TD, G_TD
- Preise: 220.00
- KU-Basis: gross
- Behalten wird ID 16 (G-TD, Preis 220.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 16 => G-TD / Preis 220.00 / KU gross; ID 25 => G_TD / Preis 220.00 / KU gross

### Periode 2 ? G-TD / H?he 3000 m
- Literale Varianten: G-TD, G_TD
- Preise: 220.00
- KU-Basis: gross
- Behalten wird ID 17 (G-TD, Preis 220.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 17 => G-TD / Preis 220.00 / KU gross; ID 26 => G_TD / Preis 220.00 / KU gross

### Periode 2 ? G-TD / H?he 4000 m
- Literale Varianten: G-TD, G_TD
- Preise: 220.00
- KU-Basis: gross
- Behalten wird ID 18 (G-TD, Preis 220.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 18 => G-TD / Preis 220.00 / KU gross; ID 27 => G_TD / Preis 220.00 / KU gross

### Periode 2 ? G-TD-Video / H?he 1500 m
- Literale Varianten: G-TD-Video, G_TD_VIDEO
- Preise: 310.00
- KU-Basis: gross
- Behalten wird ID 19 (G-TD-Video, Preis 310.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 19 => G-TD-Video / Preis 310.00 / KU gross; ID 28 => G_TD_VIDEO / Preis 310.00 / KU gross

### Periode 2 ? G-TD-Video / H?he 3000 m
- Literale Varianten: G-TD-Video, G_TD_VIDEO
- Preise: 310.00
- KU-Basis: gross
- Behalten wird ID 20 (G-TD-Video, Preis 310.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 20 => G-TD-Video / Preis 310.00 / KU gross; ID 29 => G_TD_VIDEO / Preis 310.00 / KU gross

### Periode 2 ? G-TD-Video / H?he 4000 m
- Literale Varianten: G-TD-Video, G_TD_VIDEO
- Preise: 310.00
- KU-Basis: gross
- Behalten wird ID 21 (G-TD-Video, Preis 310.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 21 => G-TD-Video / Preis 310.00 / KU gross; ID 30 => G_TD_VIDEO / Preis 310.00 / KU gross

### Periode 2 ? Gast / H?he 1500 m
- Literale Varianten: GAST, Gast
- Preise: 25.00
- KU-Basis: gross
- Behalten wird ID 31 (Gast, Preis 25.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 22 => GAST / Preis 25.00 / KU gross; ID 31 => Gast / Preis 25.00 / KU gross

### Periode 2 ? Gast / H?he 3000 m
- Literale Varianten: GAST, Gast
- Preise: 35.00
- KU-Basis: gross
- Behalten wird ID 32 (Gast, Preis 35.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 23 => GAST / Preis 35.00 / KU gross; ID 32 => Gast / Preis 35.00 / KU gross

### Periode 2 ? Gast / H?he 4000 m
- Literale Varianten: GAST, Gast
- Preise: 38.00
- KU-Basis: gross
- Behalten wird ID 33 (Gast, Preis 38.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 24 => GAST / Preis 38.00 / KU gross; ID 33 => Gast / Preis 38.00 / KU gross

### Periode 2 ? Lehrer / H?he 1500 m
- Literale Varianten: LEHRER, Lehrer
- Preise: 
- KU-Basis: gross
- Behalten wird ID 37 (Lehrer, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 34 => LEHRER / Preis 0.00 / KU gross; ID 37 => Lehrer / Preis 0.00 / KU gross

### Periode 2 ? Lehrer / H?he 3000 m
- Literale Varianten: LEHRER, Lehrer
- Preise: 
- KU-Basis: gross
- Behalten wird ID 38 (Lehrer, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 35 => LEHRER / Preis 0.00 / KU gross; ID 38 => Lehrer / Preis 0.00 / KU gross

### Periode 2 ? Lehrer / H?he 4000 m
- Literale Varianten: LEHRER, Lehrer
- Preise: 
- KU-Basis: gross
- Behalten wird ID 39 (Lehrer, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 36 => LEHRER / Preis 0.00 / KU gross; ID 39 => Lehrer / Preis 0.00 / KU gross

### Periode 2 ? Mitflieger / H?he 1500 m
- Literale Varianten: MITFLIEGER, Mitflieger
- Preise: 50.00, 60.00
- KU-Basis: gross
- Behalten wird ID 43 (Mitflieger, Preis 60.00, KU-Basis gross)
- Konflikt: ja
- Einzelzeilen: ID 40 => MITFLIEGER / Preis 50.00 / KU gross; ID 43 => Mitflieger / Preis 60.00 / KU gross

### Periode 2 ? Mitflieger / H?he 3000 m
- Literale Varianten: MITFLIEGER, Mitflieger
- Preise: 50.00, 60.00
- KU-Basis: gross
- Behalten wird ID 44 (Mitflieger, Preis 60.00, KU-Basis gross)
- Konflikt: ja
- Einzelzeilen: ID 41 => MITFLIEGER / Preis 50.00 / KU gross; ID 44 => Mitflieger / Preis 60.00 / KU gross

### Periode 2 ? Mitflieger / H?he 4000 m
- Literale Varianten: MITFLIEGER, Mitflieger
- Preise: 50.00, 60.00
- KU-Basis: gross
- Behalten wird ID 45 (Mitflieger, Preis 60.00, KU-Basis gross)
- Konflikt: ja
- Einzelzeilen: ID 42 => MITFLIEGER / Preis 50.00 / KU gross; ID 45 => Mitflieger / Preis 60.00 / KU gross

### Periode 2 ? Schueler_Ek1 / H?he 1500 m
- Literale Varianten: SCHUELER_EK1, Schueler_Ek1
- Preise: 
- KU-Basis: gross
- Behalten wird ID 62 (Schueler_Ek1, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 53 => SCHUELER_EK1 / Preis 0.00 / KU gross; ID 62 => Schueler_Ek1 / Preis 0.00 / KU gross

### Periode 2 ? Schueler_Ek1 / H?he 3000 m
- Literale Varianten: SCHUELER_EK1, Schueler_Ek1
- Preise: 
- KU-Basis: gross
- Behalten wird ID 63 (Schueler_Ek1, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 54 => SCHUELER_EK1 / Preis 0.00 / KU gross; ID 63 => Schueler_Ek1 / Preis 0.00 / KU gross

### Periode 2 ? Schueler_Ek1 / H?he 4000 m
- Literale Varianten: SCHUELER_EK1, Schueler_Ek1
- Preise: 
- KU-Basis: gross
- Behalten wird ID 64 (Schueler_Ek1, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 55 => SCHUELER_EK1 / Preis 0.00 / KU gross; ID 64 => Schueler_Ek1 / Preis 0.00 / KU gross

### Periode 2 ? Schueler_Ek2 / H?he 1500 m
- Literale Varianten: SCHUELER_EK2, Schueler_Ek2
- Preise: 
- KU-Basis: gross
- Behalten wird ID 65 (Schueler_Ek2, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 56 => SCHUELER_EK2 / Preis 0.00 / KU gross; ID 65 => Schueler_Ek2 / Preis 0.00 / KU gross

### Periode 2 ? Schueler_Ek2 / H?he 3000 m
- Literale Varianten: SCHUELER_EK2, Schueler_Ek2
- Preise: 
- KU-Basis: gross
- Behalten wird ID 66 (Schueler_Ek2, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 57 => SCHUELER_EK2 / Preis 0.00 / KU gross; ID 66 => Schueler_Ek2 / Preis 0.00 / KU gross

### Periode 2 ? Schueler_Ek2 / H?he 4000 m
- Literale Varianten: SCHUELER_EK2, Schueler_Ek2
- Preise: 
- KU-Basis: gross
- Behalten wird ID 67 (Schueler_Ek2, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 58 => SCHUELER_EK2 / Preis 0.00 / KU gross; ID 67 => Schueler_Ek2 / Preis 0.00 / KU gross

### Periode 2 ? Schueler_Gk6 / H?he 1500 m
- Literale Varianten: SCHUELER_GK6, Schueler_Gk6
- Preise: 
- KU-Basis: gross
- Behalten wird ID 68 (Schueler_Gk6, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 59 => SCHUELER_GK6 / Preis 0.00 / KU gross; ID 68 => Schueler_Gk6 / Preis 0.00 / KU gross

### Periode 2 ? Schueler_Gk6 / H?he 3000 m
- Literale Varianten: SCHUELER_GK6, Schueler_Gk6
- Preise: 
- KU-Basis: gross
- Behalten wird ID 69 (Schueler_Gk6, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 60 => SCHUELER_GK6 / Preis 0.00 / KU gross; ID 69 => Schueler_Gk6 / Preis 0.00 / KU gross

### Periode 2 ? Schueler_Gk6 / H?he 4000 m
- Literale Varianten: SCHUELER_GK6, Schueler_Gk6
- Preise: 
- KU-Basis: gross
- Behalten wird ID 70 (Schueler_Gk6, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 61 => SCHUELER_GK6 / Preis 0.00 / KU gross; ID 70 => Schueler_Gk6 / Preis 0.00 / KU gross

### Periode 2 ? Schüler / H?he 1500 m
- Literale Varianten: SCHUELER, Schüler
- Preise: 59.00
- KU-Basis: gross
- Behalten wird ID 71 (Schüler, Preis 59.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 50 => SCHUELER / Preis 59.00 / KU gross; ID 71 => Schüler / Preis 59.00 / KU gross

### Periode 2 ? Schüler / H?he 3000 m
- Literale Varianten: SCHUELER, Schüler
- Preise: 79.00
- KU-Basis: gross
- Behalten wird ID 72 (Schüler, Preis 79.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 51 => SCHUELER / Preis 79.00 / KU gross; ID 72 => Schüler / Preis 79.00 / KU gross

### Periode 2 ? Schüler / H?he 4000 m
- Literale Varianten: SCHUELER, Schüler
- Preise: 85.00
- KU-Basis: gross
- Behalten wird ID 73 (Schüler, Preis 85.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 52 => SCHUELER / Preis 85.00 / KU gross; ID 73 => Schüler / Preis 85.00 / KU gross

### Periode 2 ? TD-Vereins-Schirm / H?he 1500 m
- Literale Varianten: TD-Vereins-Schirm, TD_VEREIN_SCHIRM, Td-Vereins-Schirm, Td_Vereins_Schirm
- Preise: , -50.00
- KU-Basis: gross
- Behalten wird ID 177 (TD-Vereins-Schirm, Preis -50.00, KU-Basis gross)
- Konflikt: ja
- Einzelzeilen: ID 86 => TD_VEREIN_SCHIRM / Preis -50.00 / KU gross; ID 89 => Td-Vereins-Schirm / Preis 0.00 / KU gross; ID 92 => Td_Vereins_Schirm / Preis -50.00 / KU gross; ID 177 => TD-Vereins-Schirm / Preis -50.00 / KU gross

### Periode 2 ? TD-Vereins-Schirm / H?he 3000 m
- Literale Varianten: TD-Vereins-Schirm, TD_VEREIN_SCHIRM, Td-Vereins-Schirm, Td_Vereins_Schirm
- Preise: , -50.00
- KU-Basis: gross
- Behalten wird ID 178 (TD-Vereins-Schirm, Preis -50.00, KU-Basis gross)
- Konflikt: ja
- Einzelzeilen: ID 87 => TD_VEREIN_SCHIRM / Preis -50.00 / KU gross; ID 90 => Td-Vereins-Schirm / Preis 0.00 / KU gross; ID 93 => Td_Vereins_Schirm / Preis -50.00 / KU gross; ID 178 => TD-Vereins-Schirm / Preis -50.00 / KU gross

### Periode 2 ? TD-Vereins-Schirm / H?he 4000 m
- Literale Varianten: TD-Vereins-Schirm, TD_VEREIN_SCHIRM, Td-Vereins-Schirm, Td_Vereins_Schirm
- Preise: , -50.00
- KU-Basis: gross
- Behalten wird ID 179 (TD-Vereins-Schirm, Preis -50.00, KU-Basis gross)
- Konflikt: ja
- Einzelzeilen: ID 88 => TD_VEREIN_SCHIRM / Preis -50.00 / KU gross; ID 91 => Td-Vereins-Schirm / Preis 0.00 / KU gross; ID 94 => Td_Vereins_Schirm / Preis -50.00 / KU gross; ID 179 => TD-Vereins-Schirm / Preis -50.00 / KU gross

### Periode 2 ? Verein / H?he 1500 m
- Literale Varianten: VEREIN, Verein
- Preise: 22.00
- KU-Basis: gross
- Behalten wird ID 101 (Verein, Preis 22.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 95 => VEREIN / Preis 22.00 / KU gross; ID 101 => Verein / Preis 22.00 / KU gross

### Periode 2 ? Verein / H?he 3000 m
- Literale Varianten: VEREIN, Verein
- Preise: 32.00
- KU-Basis: gross
- Behalten wird ID 102 (Verein, Preis 32.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 96 => VEREIN / Preis 32.00 / KU gross; ID 102 => Verein / Preis 32.00 / KU gross

### Periode 2 ? Verein / H?he 4000 m
- Literale Varianten: VEREIN, Verein
- Preise: 35.00
- KU-Basis: gross
- Behalten wird ID 103 (Verein, Preis 35.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 97 => VEREIN / Preis 35.00 / KU gross; ID 103 => Verein / Preis 35.00 / KU gross

### Periode 2 ? Video / H?he 1500 m
- Literale Varianten: VIDEO, Video
- Preise: -35.00
- KU-Basis: gross
- Behalten wird ID 104 (Video, Preis -35.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 98 => VIDEO / Preis -35.00 / KU gross; ID 104 => Video / Preis -35.00 / KU gross

### Periode 2 ? Video / H?he 3000 m
- Literale Varianten: VIDEO, Video
- Preise: -35.00
- KU-Basis: gross
- Behalten wird ID 105 (Video, Preis -35.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 99 => VIDEO / Preis -35.00 / KU gross; ID 105 => Video / Preis -35.00 / KU gross

### Periode 2 ? Video / H?he 4000 m
- Literale Varianten: VIDEO, Video
- Preise: -35.00
- KU-Basis: gross
- Behalten wird ID 106 (Video, Preis -35.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 100 => VIDEO / Preis -35.00 / KU gross; ID 106 => Video / Preis -35.00 / KU gross

### Periode 7 ? Auffüller Gast / H?he 1500 m
- Literale Varianten: AUFFUELLER_GAST, Auffüller Gast
- Preise: 25.00
- KU-Basis: gross
- Behalten wird ID 189 (Auffüller Gast, Preis 25.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 180 => AUFFUELLER_GAST / Preis 25.00 / KU gross; ID 189 => Auffüller Gast / Preis 25.00 / KU gross

### Periode 7 ? Auffüller Gast / H?he 3000 m
- Literale Varianten: AUFFUELLER_GAST, Auffüller Gast
- Preise: 25.00
- KU-Basis: gross
- Behalten wird ID 190 (Auffüller Gast, Preis 25.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 181 => AUFFUELLER_GAST / Preis 25.00 / KU gross; ID 190 => Auffüller Gast / Preis 25.00 / KU gross

### Periode 7 ? Auffüller Gast / H?he 4000 m
- Literale Varianten: AUFFUELLER_GAST, Auffüller Gast
- Preise: 28.00
- KU-Basis: gross
- Behalten wird ID 191 (Auffüller Gast, Preis 28.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 182 => AUFFUELLER_GAST / Preis 28.00 / KU gross; ID 191 => Auffüller Gast / Preis 28.00 / KU gross

### Periode 7 ? Auffüller Verein / H?he 1500 m
- Literale Varianten: AUFFUELLER_VEREIN, Auffüller Verein
- Preise: 22.00
- KU-Basis: gross
- Behalten wird ID 195 (Auffüller Verein, Preis 22.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 183 => AUFFUELLER_VEREIN / Preis 22.00 / KU gross; ID 195 => Auffüller Verein / Preis 22.00 / KU gross

### Periode 7 ? Auffüller Verein / H?he 3000 m
- Literale Varianten: AUFFUELLER_VEREIN, Auffüller Verein
- Preise: 22.00
- KU-Basis: gross
- Behalten wird ID 196 (Auffüller Verein, Preis 22.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 184 => AUFFUELLER_VEREIN / Preis 22.00 / KU gross; ID 196 => Auffüller Verein / Preis 22.00 / KU gross

### Periode 7 ? Auffüller Verein / H?he 4000 m
- Literale Varianten: AUFFUELLER_VEREIN, Auffüller Verein
- Preise: 25.00
- KU-Basis: gross
- Behalten wird ID 197 (Auffüller Verein, Preis 25.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 185 => AUFFUELLER_VEREIN / Preis 25.00 / KU gross; ID 197 => Auffüller Verein / Preis 25.00 / KU gross

### Periode 7 ? G-TD / H?he 1500 m
- Literale Varianten: G-TD, G_TD
- Preise: 220.00
- KU-Basis: gross
- Behalten wird ID 198 (G-TD, Preis 220.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 198 => G-TD / Preis 220.00 / KU gross; ID 207 => G_TD / Preis 220.00 / KU gross

### Periode 7 ? G-TD / H?he 3000 m
- Literale Varianten: G-TD, G_TD
- Preise: 220.00
- KU-Basis: gross
- Behalten wird ID 199 (G-TD, Preis 220.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 199 => G-TD / Preis 220.00 / KU gross; ID 208 => G_TD / Preis 220.00 / KU gross

### Periode 7 ? G-TD / H?he 4000 m
- Literale Varianten: G-TD, G_TD
- Preise: 220.00
- KU-Basis: gross
- Behalten wird ID 200 (G-TD, Preis 220.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 200 => G-TD / Preis 220.00 / KU gross; ID 209 => G_TD / Preis 220.00 / KU gross

### Periode 7 ? G-TD-Video / H?he 1500 m
- Literale Varianten: G-TD-Video, G_TD_VIDEO
- Preise: 310.00
- KU-Basis: gross
- Behalten wird ID 201 (G-TD-Video, Preis 310.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 201 => G-TD-Video / Preis 310.00 / KU gross; ID 210 => G_TD_VIDEO / Preis 310.00 / KU gross

### Periode 7 ? G-TD-Video / H?he 3000 m
- Literale Varianten: G-TD-Video, G_TD_VIDEO
- Preise: 310.00
- KU-Basis: gross
- Behalten wird ID 202 (G-TD-Video, Preis 310.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 202 => G-TD-Video / Preis 310.00 / KU gross; ID 211 => G_TD_VIDEO / Preis 310.00 / KU gross

### Periode 7 ? G-TD-Video / H?he 4000 m
- Literale Varianten: G-TD-Video, G_TD_VIDEO
- Preise: 310.00
- KU-Basis: gross
- Behalten wird ID 203 (G-TD-Video, Preis 310.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 203 => G-TD-Video / Preis 310.00 / KU gross; ID 212 => G_TD_VIDEO / Preis 310.00 / KU gross

### Periode 7 ? Gast / H?he 1500 m
- Literale Varianten: GAST, Gast
- Preise: 25.00
- KU-Basis: gross
- Behalten wird ID 213 (Gast, Preis 25.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 204 => GAST / Preis 25.00 / KU gross; ID 213 => Gast / Preis 25.00 / KU gross

### Periode 7 ? Gast / H?he 3000 m
- Literale Varianten: GAST, Gast
- Preise: 35.00
- KU-Basis: gross
- Behalten wird ID 214 (Gast, Preis 35.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 205 => GAST / Preis 35.00 / KU gross; ID 214 => Gast / Preis 35.00 / KU gross

### Periode 7 ? Gast / H?he 4000 m
- Literale Varianten: GAST, Gast
- Preise: 38.00
- KU-Basis: gross
- Behalten wird ID 215 (Gast, Preis 38.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 206 => GAST / Preis 38.00 / KU gross; ID 215 => Gast / Preis 38.00 / KU gross

### Periode 7 ? Lehrer / H?he 1500 m
- Literale Varianten: LEHRER, Lehrer
- Preise: 
- KU-Basis: gross
- Behalten wird ID 219 (Lehrer, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 216 => LEHRER / Preis 0.00 / KU gross; ID 219 => Lehrer / Preis 0.00 / KU gross

### Periode 7 ? Lehrer / H?he 3000 m
- Literale Varianten: LEHRER, Lehrer
- Preise: 
- KU-Basis: gross
- Behalten wird ID 220 (Lehrer, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 217 => LEHRER / Preis 0.00 / KU gross; ID 220 => Lehrer / Preis 0.00 / KU gross

### Periode 7 ? Lehrer / H?he 4000 m
- Literale Varianten: LEHRER, Lehrer
- Preise: 
- KU-Basis: gross
- Behalten wird ID 221 (Lehrer, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 218 => LEHRER / Preis 0.00 / KU gross; ID 221 => Lehrer / Preis 0.00 / KU gross

### Periode 7 ? Mitflieger / H?he 1500 m
- Literale Varianten: MITFLIEGER, Mitflieger
- Preise: 50.00, 60.00
- KU-Basis: gross
- Behalten wird ID 225 (Mitflieger, Preis 60.00, KU-Basis gross)
- Konflikt: ja
- Einzelzeilen: ID 222 => MITFLIEGER / Preis 50.00 / KU gross; ID 225 => Mitflieger / Preis 60.00 / KU gross

### Periode 7 ? Mitflieger / H?he 3000 m
- Literale Varianten: MITFLIEGER, Mitflieger
- Preise: 50.00, 60.00
- KU-Basis: gross
- Behalten wird ID 226 (Mitflieger, Preis 60.00, KU-Basis gross)
- Konflikt: ja
- Einzelzeilen: ID 223 => MITFLIEGER / Preis 50.00 / KU gross; ID 226 => Mitflieger / Preis 60.00 / KU gross

### Periode 7 ? Mitflieger / H?he 4000 m
- Literale Varianten: MITFLIEGER, Mitflieger
- Preise: 50.00, 60.00
- KU-Basis: gross
- Behalten wird ID 227 (Mitflieger, Preis 60.00, KU-Basis gross)
- Konflikt: ja
- Einzelzeilen: ID 224 => MITFLIEGER / Preis 50.00 / KU gross; ID 227 => Mitflieger / Preis 60.00 / KU gross

### Periode 7 ? Schueler_Ek1 / H?he 1500 m
- Literale Varianten: SCHUELER_EK1, Schueler_Ek1
- Preise: 
- KU-Basis: gross
- Behalten wird ID 250 (Schueler_Ek1, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 235 => SCHUELER_EK1 / Preis 0.00 / KU gross; ID 250 => Schueler_Ek1 / Preis 0.00 / KU gross

### Periode 7 ? Schueler_Ek1 / H?he 3000 m
- Literale Varianten: SCHUELER_EK1, Schueler_Ek1
- Preise: 
- KU-Basis: gross
- Behalten wird ID 251 (Schueler_Ek1, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 236 => SCHUELER_EK1 / Preis 0.00 / KU gross; ID 251 => Schueler_Ek1 / Preis 0.00 / KU gross

### Periode 7 ? Schueler_Ek1 / H?he 4000 m
- Literale Varianten: SCHUELER_EK1, Schueler_Ek1
- Preise: 
- KU-Basis: gross
- Behalten wird ID 252 (Schueler_Ek1, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 237 => SCHUELER_EK1 / Preis 0.00 / KU gross; ID 252 => Schueler_Ek1 / Preis 0.00 / KU gross

### Periode 7 ? Schueler_Ek2 / H?he 1500 m
- Literale Varianten: SCHUELER_EK2, Schueler_Ek2
- Preise: 
- KU-Basis: gross
- Behalten wird ID 253 (Schueler_Ek2, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 238 => SCHUELER_EK2 / Preis 0.00 / KU gross; ID 253 => Schueler_Ek2 / Preis 0.00 / KU gross

### Periode 7 ? Schueler_Ek2 / H?he 3000 m
- Literale Varianten: SCHUELER_EK2, Schueler_Ek2
- Preise: 
- KU-Basis: gross
- Behalten wird ID 254 (Schueler_Ek2, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 239 => SCHUELER_EK2 / Preis 0.00 / KU gross; ID 254 => Schueler_Ek2 / Preis 0.00 / KU gross

### Periode 7 ? Schueler_Ek2 / H?he 4000 m
- Literale Varianten: SCHUELER_EK2, Schueler_Ek2
- Preise: 
- KU-Basis: gross
- Behalten wird ID 255 (Schueler_Ek2, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 240 => SCHUELER_EK2 / Preis 0.00 / KU gross; ID 255 => Schueler_Ek2 / Preis 0.00 / KU gross

### Periode 7 ? Schueler_Gk6 / H?he 1500 m
- Literale Varianten: SCHUELER_GK6, Schueler_Gk6
- Preise: 
- KU-Basis: gross
- Behalten wird ID 256 (Schueler_Gk6, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 241 => SCHUELER_GK6 / Preis 0.00 / KU gross; ID 256 => Schueler_Gk6 / Preis 0.00 / KU gross

### Periode 7 ? Schueler_Gk6 / H?he 3000 m
- Literale Varianten: SCHUELER_GK6, Schueler_Gk6
- Preise: 
- KU-Basis: gross
- Behalten wird ID 257 (Schueler_Gk6, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 242 => SCHUELER_GK6 / Preis 0.00 / KU gross; ID 257 => Schueler_Gk6 / Preis 0.00 / KU gross

### Periode 7 ? Schueler_Gk6 / H?he 4000 m
- Literale Varianten: SCHUELER_GK6, Schueler_Gk6
- Preise: 
- KU-Basis: gross
- Behalten wird ID 258 (Schueler_Gk6, Preis 0.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 243 => SCHUELER_GK6 / Preis 0.00 / KU gross; ID 258 => Schueler_Gk6 / Preis 0.00 / KU gross

### Periode 7 ? Schüler / H?he 1500 m
- Literale Varianten: SCHUELER, Schüler
- Preise: 59.00
- KU-Basis: gross
- Behalten wird ID 259 (Schüler, Preis 59.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 232 => SCHUELER / Preis 59.00 / KU gross; ID 259 => Schüler / Preis 59.00 / KU gross

### Periode 7 ? Schüler / H?he 3000 m
- Literale Varianten: SCHUELER, Schüler
- Preise: 79.00
- KU-Basis: gross
- Behalten wird ID 260 (Schüler, Preis 79.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 233 => SCHUELER / Preis 79.00 / KU gross; ID 260 => Schüler / Preis 79.00 / KU gross

### Periode 7 ? Schüler / H?he 4000 m
- Literale Varianten: SCHUELER, Schüler
- Preise: 85.00
- KU-Basis: gross
- Behalten wird ID 261 (Schüler, Preis 85.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 234 => SCHUELER / Preis 85.00 / KU gross; ID 261 => Schüler / Preis 85.00 / KU gross

### Periode 7 ? Verein / H?he 1500 m
- Literale Varianten: VEREIN, Verein
- Preise: 22.00
- KU-Basis: gross
- Behalten wird ID 292 (Verein, Preis 22.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 286 => VEREIN / Preis 22.00 / KU gross; ID 292 => Verein / Preis 22.00 / KU gross

### Periode 7 ? Verein / H?he 3000 m
- Literale Varianten: VEREIN, Verein
- Preise: 32.00
- KU-Basis: gross
- Behalten wird ID 293 (Verein, Preis 32.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 287 => VEREIN / Preis 32.00 / KU gross; ID 293 => Verein / Preis 32.00 / KU gross

### Periode 7 ? Verein / H?he 4000 m
- Literale Varianten: VEREIN, Verein
- Preise: 35.00
- KU-Basis: gross
- Behalten wird ID 294 (Verein, Preis 35.00, KU-Basis gross)
- Konflikt: nein
- Einzelzeilen: ID 288 => VEREIN / Preis 35.00 / KU gross; ID 294 => Verein / Preis 35.00 / KU gross

## Statusgruppen, die besonders relevant sind

- TD-Vereins-Schirm: Varianten wie TD_VEREIN_SCHIRM, Td-Vereins-Schirm, Td_Vereins_Schirm werden auf TD-Vereins-Schirm normalisiert.
- Video: Varianten wie VIDEO werden auf Video normalisiert.
- Verein, Lehrer, Gast, G-TD, G-TD-Video, Auff?ller Gast/Verein, Mitflieger, Sch?ler-Varianten usw. werden ebenfalls auf die kanonischen Codes normalisiert.

## Sicherheitscheck f?r den Save-Pfad

- Die aktuelle Save-Route verwendet bereits normalize_status_code und speichert die Werte unter dem kanonischen Statuscode.
- Die Seeding-Logik verwendet ebenfalls normalize_status_code und erzeugt damit keine historischen Varianten mehr.
- Die eigentliche Bereinigung wird deshalb prim?r ?ber die Datenmigration und nicht ?ber den Save-Pfad erfolgen.

## N?chster Schritt

- Nach Freigabe dieses Berichts wird die eigentliche Datenmigration ausgef?hrt.
- Die Migration wird nur f?r die betroffenen Duplikatgruppen ausf?hren, keine anderen Statusgruppen ver?ndern und Konflikte explizit protokollieren.