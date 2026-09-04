# Mobile Personenerfassung

## Neue Funktion

Einfuehrung einer mobilen Personenerfassung ueber Smartphone oder Tablet.

Ablauf:

- Neue Person ueber Mobilgeraet
- Auswahl Tandemgast oder Springer
- QR-Code-Erzeugung
- Dateneingabe auf Mobilgeraet
- Speicherung als Entwurf
- Anzeige in Mobile Entwuerfe
- Oeffnen im bestehenden Personenformular
- Uebernahme durch Manifest-Benutzer
- Speicherung als regulaere Person
- Statuswechsel auf ACCEPTED

## Technische Umsetzung

### Entwurfswarteschlange

- Neue Tabelle `mobile_person_intake_draft`
- Statusmodell:
  - OPEN
  - SUBMITTED
  - ACCEPTED
  - DISCARDED
  - EXPIRED

### Personenverwaltung

- Neuer Button:
  - Neue Person ueber Mobilgeraet
- Neuer Bereich:
  - Mobile Entwuerfe

### QR-Code

- Wiederverwendung bestehender WLAN- und QR-Infrastruktur
- Tokenbasierte Erfassung

### Mobile Formulare

Tandemgast:

- Personenstammdaten
- Adresse
- Notfallkontakt

Springer:

- Personenstammdaten
- Adresse
- Notfallkontakt
- Lizenznummer
- Versicherungsdaten
- Mitglied
- Partnerverein

Nicht mobil erfassbar:

- Bankdaten
- Rollen
- Kleinunternehmerregelung
- interne Daten

### Spaetere Uebernahme

- Oeffnen ueber bestehendes Personenformular
- Keine zweite Personenanlage
- Bestehende Validierung bleibt erhalten
- Bestehende Speicherlogik bleibt erhalten

## UI-Anpassungen

- Groessere Auswahlkacheln fuer Tandemgast / Springer
- Ueberarbeiteter Erfolgstext nach mobiler Eingabe
- Lizenzart aus mobiler Springer-Erfassung entfernt
- Aktionsleiste im Personenformular oberhalb des Newsletter-Blocks platziert
- Schaltflaechen Abbrechen, Enthaftung drucken / PDF und Aenderungen speichern vergroessert und deutlicher hervorgehoben

## Heute abgeschlossen

Die Aktionsleiste mit Abbrechen, Enthaftung drucken / PDF und Aenderungen speichern steht jetzt oberhalb des Newsletter-Blocks. Die bestehenden Funktionen und Farben bleiben unveraendert; die Schaltflaechen wurden fuer bessere Sichtbarkeit und Touch-Bedienung vergroessert.

## Geplanter naechster Schritt

Git-Commit erstellen.

Commit-Text:

`feat: mobile Personenerfassung mit Entwurfsworkflow und QR-Code integriert`

## Aenderungen 04.09.2026

- Einfuehrung eines Kiosk-Modus fuer die mobile Personenerfassung.
- Betrifft ausschliesslich:
  - `mobile_intake_new.html`
  - `mobile_intake_qr.html`
- Sidebar, Navigation, Dashboard-Menues und Standardkopf werden im separaten Erfassungsfenster ausgeblendet.
- Hauptfenster der Personenverwaltung bleibt unveraendert.
- QR-Code-Darstellung wurde vergroessert und fuer Tresenmonitore optimiert.
- Auswahlkarten Tandemgast und Springer bleiben unveraendert erhalten.
- Backend, Routing, Berechtigungen und Datenmodell wurden nicht geaendert.
- Praxistest erfolgreich:
  - QR-Code-Fenster oeffnet korrekt.
  - Kiosk-Modus funktioniert.
  - Hauptfenster bleibt voll funktionsfaehig.
- Test zu nicht verwendeten QR-Codes:
  - Mehrere QR-Codes erzeugt.
  - Keine Dateneingaben vorgenommen.
  - Fenster geschlossen.
  - Keine negativen Auswirkungen festgestellt.
  - Keine zusaetzliche Verwaltung offener Mobilentwuerfe erforderlich.
- Entscheidung:
  - Ungenutzte QR-Codes werden aktuell nicht gesondert verwaltet.
  - Beim naechsten Erfassungsvorgang wird einfach ein neuer QR-Code erzeugt.
  - Keine weitere UX-Anpassung notwendig.
