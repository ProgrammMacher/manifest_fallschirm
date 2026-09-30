MANIFEST Fallschirm - Entwickler-Lizenzgenerator (MFS2)
=======================================================

Einmalige Einrichtung auf dem Entwicklerrechner:
1. Doppelklick auf "Signierschlüssel einmalig einrichten.bat".
2. Der private Ed25519-Schluessel wird benutzergebunden mit Windows DPAPI
   unter %LOCALAPPDATA%\ManifestFallschirm\developer-signing gespeichert.
3. Die NTFS-ACL wird auf das aktuelle Windows-Konto und SYSTEM beschraenkt.
4. Nur der oeffentliche Pruefschluessel wird nach app\security geschrieben.
5. Den privaten .dpapi-Schluessel niemals kopieren, committen oder weitergeben.
   Ohne diesen Schluessel koennen neue Lizenzen nicht mehr signiert werden.

Kunden-Fingerprint:
1. Nur die beiden Dateien aus developer_tools\fingerprint weitergeben.
2. Der Kunde startet "Fingerprint ermitteln.bat" und sendet den angezeigten
   64-stelligen Fingerprint zurueck.
3. Das Fingerprint-Werkzeug erzeugt keine Lizenz und enthaelt keinen Signer.

Lizenz erstellen:
1. Doppelklick auf "Lizenzgenerator starten.bat".
2. Kundenname, Fingerprint und Lizenzstufe 3 Monate / 12 Monate / Unbegrenzt
   auswaehlen.
3. "Lizenzschluessel generieren" klicken und den Schluessel kopieren.

Weitergeben darfst du:
- den fertigen MFS2-Lizenzschluessel
- die beiden Fingerprint-Dateien (Fingerprint ermitteln.bat/.ps1)
- den freigegebenen Kunden-Installer

Niemals weitergeben:
- license_ed25519_private.dpapi aus dem lokalen LOCALAPPDATA-Pfad
- Dateien aus diesem Entwicklerordner (ausser den zwei Fingerprint-Dateien)
- initialize_signing_key.py, license_signing.py oder Generator-Dateien
- auth_config.json, app_settings.json oder sonstige Laufzeit-Secrets

Der Kunden-Installer enthaelt nur den oeffentlichen Pruefschluessel und die
Runtime-Pruefung. Er enthaelt keine Signierfunktion und keinen privaten Key.