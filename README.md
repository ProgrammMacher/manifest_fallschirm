# manifest_fallschirm

Erstellen einer EXE.

## Installer bauen

Im Repository ist ein NSIS-Installer unter `/home/runner/work/manifest_fallschirm/manifest_fallschirm/ProgrammMacher/manifest_fallschirm/installer/manifest_fallschirm.nsi` hinterlegt.

- Lokal: `makensis installer/manifest_fallschirm.nsi`
- GitHub Actions: Workflow `Build installer`

Das erzeugte Installationsprogramm liegt anschließend unter `dist/manifest_fallschirm-setup.exe`.
