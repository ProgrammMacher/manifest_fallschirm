# Betriebsnotiz Stabilisierung 2026-10

## Datenschutz

Problem:
- Nicht-Admins konnten Kontodaten sehen.
- Excel-Export lieferte sensible Daten.

Lösung:
- Kontodaten maskiert.
- Export nur für Admins.

Commit:
- 4c80548d

---

## Startfenster

Problem:
- Startfenster schloss nach ca. 3,5 Sekunden.
- Anwendung startete teilweise deutlich länger.

Lösung:
- Fenster bleibt sichtbar bis Server bereit ist.
- Browser wird erst danach geöffnet.

Commit:
- 4c80548d

---

## Login-Untersuchung

Ergebnis:
- auth_config.json wird korrekt erzeugt.
- Admin-Hash und DB-Admin-Hash vorhanden.
- Login funktioniert.
- Ursprüngliche Vermutung eines Konfigurationsfehlers wurde nicht bestätigt.

---

## Logout-Race-Condition

Problem:
- Teilweise waren mehrere Klicks auf „Abmelden“ erforderlich.

Verworfene Hypothesen:
- Browser-Cache
- fehlerhafte Logout-Buttons
- unterschiedliche Logout-Routen

Tatsächliche Ursache:
- Flask-Session mit SESSION_TYPE=filesystem
- SESSION_REFRESH_EACH_REQUEST=True
- parallele Runtime-Requests
- alte Session konnte nach Logout zurückgeschrieben werden

Umgesetzte Lösung:
- SESSION_REFRESH_EACH_REQUEST=False
- last_page wird nur noch gespeichert, wenn sich der Wert ändert

Commit:
- 1ccd29a1

Restrisiko:
- Parallele GET-Requests aus anderen Tabs können theoretisch weiterhin alte Sessionstände zurückschreiben.

---

## Installer / Seed-Daten

Erkenntnis:
- manifest_Vorlage_leer_mit_Beispiel.db wird aktuell nicht verwendet.
- Neuinstallationen werden über neutral_install_seed.py initialisiert.

Bewertung:
- Der aktuelle Seed-Datenbestand wurde getestet.
- Für Neuinstallationen ausreichend.

Empfehlung:
- Vorlagendatenbank optional als Demo-/Schulungsdatenbank verwenden.

---

## Dokumentation

Technische Schulden dokumentiert in:

TECHNISCHE_SCHULDEN.md

Commit:
- 1325be70