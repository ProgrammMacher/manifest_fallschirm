MANIFEST Fallschirm - Rechner-Kennung fuer Endanwender (EXE)
============================================================

Dieses Werkzeug erzeugt die Rechner-Kennung, die MANIFeST OU bei der
Lizenzpruefung erwartet. Es wird ausschliesslich an Kunden weitergegeben,
nicht in den Kunden-Installer aufgenommen (der Installer-Build schliesst
tools\fingerprint ohnehin aus).

Inhalt dieses Ordners
--------------------
- fingerprint_app.py            Endanwender-App (Tkinter, nur Anzeige/Kopie/Speichern)
- build_fingerprint_exe.ps1     Entwickler-only: baut die EXE mit PyInstaller
- Fingerprint EXE bauen.bat     Entwickler-only: Doppelklick-Start fuer den Build
- Fingerprint ermitteln.ps1/.bat  interne Rueckfallebene fuer Entwickler (Bestand)
- README.txt                    diese Datei

Die Fingerprint-Berechnung erfolgt ausschliesslich ueber
app\security\hardware_fingerprint.py (get_machine_fingerprint).
Die EXE enthaelt weder Signierfunktion noch privaten Schluessel.

1) EXE bauen (nur auf dem Entwicklerrechner)
--------------------------------------------
1. Doppelklick auf "Fingerprint EXE bauen.bat".
2. Das Skript erzeugt eine eigene Build-Umgebung unter
   build\fingerprint\venv (getrennt von venv\, requirements.txt,
   packages\ und runtime\python - diese bleiben unveraendert).
3. Voraussetzung: 64-Bit-Python als "python" im PATH und Internet
   (pip installiert PyInstaller nur in die Build-Umgebung).
   Das Skript bricht ab, wenn nicht mit 64-Bit gebaut wuerde, weil ein
   32-Bit-Build eine andere MachineGuid liest und damit eine falsche
   Kennung liefern wuerde.
4. Ergebnis: build\fingerprint\dist\MANIFeST_Rechnerkennung.exe
   (eine einzelne Datei, ca. 10-12 MB, keine Installation, kein
   Konsolenfenster, keine Admin-Rechte noetig).
5. Das Skript gibt SHA256-Prüfsummen der EXE und der verwendeten
   Quelle hardware_fingerprint.py aus - im Ticket/Change-Vermerk notieren.

Wichtig: Nach jeder Aenderung an app\security\hardware_fingerprint.py
muss die EXE neu gebaut werden (die Logik wird beim Build eingefroren).

Manuelle Pruefung vor jeder Weitergabe:
1. EXE auf einem Testrechner per Doppelklick starten.
2. Angezeigte Kennung vergleichen mit:
   python -c "from app.security.hardware_fingerprint import get_machine_fingerprint; print(get_machine_fingerprint())"
   auf demselben Rechner. Beide Werte muessen identisch sein.
3. Zwischenablage nach dem Schliessen pruefen (Strg+V in einem Editor).

2) Weitergabe an den Kunden
---------------------------
Nie als Mail-Anhang senden: Outlook, Microsoft 365 und Gmail sperren
.exe-Dateien (auch in ZIPs). Stattdessen:

1. EXE auf einen HTTPS-Download legen (eigene Website, OneDrive- oder
   Nextcloud-Freigabe) und dem Kunden eine E-Mail mit dem Link senden.
2. Der Kunde oeffnet den Link, laedt die Datei herunter, speichert sie
   z. B. auf dem Desktop und startet sie per Doppelklick.
3. Ablauf fuer den Kunden:
   - Doppelklick auf MANIFeST_Rechnerkennung.exe
   - die Kennung wird automatisch erzeugt und in die Zwischenablage kopiert
   - das Fenster zeigt die Kennung und den Hinweis:
     "Bitte antworten Sie auf die E-Mail des Entwicklers und fuegen Sie
      die Kennung mit Strg+V ein."
   - optional kann der Kunde ueber "Textdatei speichern" eine TXT-Datei
     (Desktop\MANIFeST_Rechnerkennung.txt mit Kennung, Computername,
     Datum/Uhrzeit) speichern
   - der Kunde antwortet auf die Entwickler-E-Mail und fuegt die Kennung
     mit Strg+V ein. Fertig.

E-Mail-Vorlage fuer den Kunden (anpassen):
------------------------------------------------
Betreff: MANIFeST OU - Ihre Rechner-Kennung

Hallo,

anbei der Link zu einem kleinen Programm, das die Rechner-Kennung
Ihres PCs ermittelt:

  <DOWNLOAD-LINK>

So geht es:
1. Link oeffnen und Datei herunterladen.
2. Datei z. B. auf dem Desktop speichern.
3. Doppelklick auf "MANIFeST_Rechnerkennung.exe".
   Falls Windows eine blaue Meldung zeigt ("Der Computer wurde durch
   Windows geschuetzt"): auf "Weitere Informationen" und dann
   "Trotzdem ausfuehren" klicken.
4. Die Kennung wurde bereits automatisch kopiert.
5. Antworten Sie einfach auf diese E-Mail und fuegen Sie die Kennung
   mit Strg+V ein.

Viele Gruesse
<NAME>

3) SmartScreen / Virenscanner
-----------------------------
- Ohne Code-Signing meldet Windows SmartScreen "Unbekannter Herausgeber".
  Der Kunde klickt "Weitere Informationen" -> "Trotzdem ausfuehren".
- Die EXE enthaelt kein Mailprogramm, oeffnet keine Webseite und sendet
  nichts. Sie liest nur Maschinenmerkmale (siehe hardware_fingerprint.py)
  und zeigt deren Hash an.
- Langfristig empfiehlt sich Code-Signing (Zertifikat oder Microsoft
  Trusted Signing), damit die Warnung verschwindet und Fehlalarme von
  Virenscannern seltener werden.

4) Was niemals weitergegeben werden darf
----------------------------------------
- den privaten Signierschluessel (DPAPI) und alle Dateien aus
  tools\lizenzgenerator\ (ausser diesem Fingerprint-Ordner)
- auth_config.json, app_settings.json oder sonstige Laufzeit-Secrets
- die EXE als Mail-Anhang (wird blockiert); nur per Download-Link
