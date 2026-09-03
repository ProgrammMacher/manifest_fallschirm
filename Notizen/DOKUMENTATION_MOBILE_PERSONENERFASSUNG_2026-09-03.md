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
