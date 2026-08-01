# SEPA Dev-Rollback – technische Spezifikation

## Zweck des Dev-Rollbacks

Der Dev-Rollback ist ein reines Entwicklerwerkzeug für den Dev-Modus. Ziel ist es, den letzten SEPA-Testexport vollständig aus dem System zu entfernen, sodass der Eindruck entsteht, dieser SEPA-Vorgang habe niemals existiert.

Der Rollback dient ausschließlich der Bereinigung von Testexporten. Er ist kein Produktiv-Feature und kein allgemeiner Datenreset.

## Fachliche Anforderungen

Der Dev-Rollback entfernt den letzten SEPA-Testexport vollständig:

- Exportdatei löschen
- SepaExport löschen
- SepaExportInvoice löschen
- zugehörige Exporthistorie dieses Exports entfernen
- betroffene Rechnungen aus dem SEPA-Kontext lösen

Die Rechnungen bleiben erhalten. Nur der SEPA-Vorgang und seine Zuordnungen verschwinden.

## Voraussetzungen

Der Rollback darf nur durchgeführt werden, wenn:

- die Anwendung im Dev-Modus läuft
- der aktuelle Benutzer Admin oder DB-Admin ist
- der zu rollende Export der aktuell letzte SEPA-Export ist
- die Prüfung serverseitig erfolgt

## Berechtigungen

Nur folgende Rollen dürfen den Rollback ausführen:

- Admin
- DB-Admin

Andere Rollen dürfen diesen Vorgang nicht starten.

## Dev-Modus-Regeln

Im Dev-Modus gilt:

- Dev-Rollback ist erlaubt
- nur der aktuell letzte SEPA-Export darf zurückgerollt werden
- der Rollback muss serverseitig geprüft werden
- die Aktion darf nur als expliziter Dev-Only-Workflow ausgeführt werden

## Produktivmodus-Regeln

Im Produktivmodus gilt:

- kein Rollback
- keine Löschung von Exporten
- keine Löschung von Historie
- keine Wiederverwendung von Exportnummern
- keine Änderung von Exportdaten im Sinne eines Rollbacks

## Ablauf des Rollbacks

1. Serverseitige Prüfung der Voraussetzungen
2. Feststellen, ob der Ziel-Export der aktuell letzte SEPA-Export ist
3. Exportdatei löschen, falls vorhanden
4. SepaExport löschen
5. SepaExportInvoice-Zeilen löschen
6. betroffene Rechnungen aus dem SEPA-Kontext lösen
7. Historie dieses Exports entfernen
8. Erfolg oder Fehler an die UI zurückgeben

## Auswirkungen auf Rechnungen

Die Rechnungen bleiben erhalten. Sie werden jedoch wieder neutralisiert:

- payment_state = open
- payment_method = None
- is_paid = False
- paid_at = None

Damit sind die Rechnungen wieder offen und nicht mehr an einen aktiven SEPA-Vorgang gebunden.

## Auswirkungen auf SEPA-Historie

Die Historie dieses Exports verschwindet vollständig.

Ältere Exporte bleiben unverändert erhalten.

Nur der zuletzt erzeugte Export wird entfernt, sofern er der aktuell letzte Export ist.

## Auswirkungen auf Exportnummern

Im Dev-Modus darf die freigewordene Exportnummer wiederverwendet werden.

Im Produktivmodus bleibt die Exportnummer dauerhaft reserviert.

## UI-Verhalten

In der bestehenden Exporthistorie erscheint im Dev-Modus ein zusätzlicher Button:

- SEPA-Testexport zurückrollen

Der Button erscheint nur, wenn:

- Dev-Modus aktiv ist
- Admin oder DB-Admin
- der angezeigte Export der aktuell letzte SEPA-Export ist

Vor dem Ausführen wird eine Sicherheitsabfrage angezeigt.

## Sonderfälle

- Ein neuer Export kann zwischen Prüfung und Ausführung erzeugt worden sein.
- Die Exportdatei kann bereits fehlen.
- Ein Rollback darf nicht für ältere Exporte durchgeführt werden, wenn bereits ein späterer Export existiert.
- Im Produktivmodus muss die Aktion immer blockiert werden.

## Begründung für open statt sepa_pending

Ein vollständiger Dev-Rollback entfernt den SEPA-Vorgang inklusive Historie und Zuordnung. Danach ist die Rechnung nicht mehr „SEPA vorgemerkt“, sondern wieder neutral und offen.

Der Zustand `open` passt deshalb fachlich besser als `sepa_pending`, weil `sepa_pending` weiterhin den Eindruck eines aktiven SEPA-Workflows erzeugt.

## Abgrenzung zu Rücklastschriften

Rücklastschriften sind kein Rollback. Sie sind normale Statusübergänge im späteren Banking-Workflow.

Sie bleiben getrennt vom Dev-Rollback behandelt.

## Offene Folgearbeiten

- UI-Text und Fehlermeldungen im Sinne der finalen Fachsprache prüfen
- Rollback-Log und Audit-Informationen ergänzen
- ggf. spätere Absicherung bei parallelen Exports oder fehlenden Dateipfaden prüfen
