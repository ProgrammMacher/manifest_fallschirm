# manifest_fallschirm

Erstellen einer EXE.

## Installer bauen

Im Repository ist ein NSIS-Installer unter `installer/manifest_fallschirm.nsi` hinterlegt.

- Lokal: `makensis installer/manifest_fallschirm.nsi`
- GitHub Actions: Workflow `Build installer`

Das erzeugte Installationsprogramm liegt anschließend unter `dist/manifest_fallschirm-setup.exe`.

Aktuell wird bewusst nur die vorhandene Datei `README.md` verpackt. Sobald weitere Anwendungsdateien hinzukommen, können sie in den Abschnitten `Install` und `Uninstall` der NSIS-Datei ergänzt werden.
