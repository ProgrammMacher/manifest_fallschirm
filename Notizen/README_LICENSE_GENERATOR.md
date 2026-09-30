# Lizenzverwaltung (MFS2)

Die aktuelle Entwicklerbedienung und sichere Schlüsselspeicherung sind dokumentiert in:

- `developer_tools/lizenzgenerator/README.txt`

Der Kunden-Fingerprint-Starter liegt separat unter:

- `developer_tools/fingerprint/Fingerprint ermitteln.bat`
- `developer_tools/fingerprint/Fingerprint ermitteln.ps1`

MFS2 verwendet Ed25519. Der private Entwicklerschlüssel bleibt DPAPI-geschützt
unter `%LOCALAPPDATA%\ManifestFallschirm\developer-signing\` und darf niemals
weitergegeben oder in Git/Installer aufgenommen werden. Die installierte App
enthält ausschließlich den öffentlichen Prüfschlüssel.
