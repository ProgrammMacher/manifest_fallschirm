# manifest_fallschirm

Erstellen einer EXE.

## Installer bauen

Im Repository ist ein NSIS-Installer unter `installer/manifest_fallschirm.nsi` hinterlegt.

- Lokal: `makensis installer/manifest_fallschirm.nsi`
- GitHub Actions: Workflow `Build installer`

Das erzeugte Installationsprogramm liegt anschließend unter `dist/manifest_fallschirm-setup.exe`.
