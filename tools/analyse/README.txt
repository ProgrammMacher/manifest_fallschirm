MANIFEST Fallschirm - Analyse-Werkzeuge (Entwickler-only)
==========================================================

Diese Skripte sind reine, lesende Entwickler-Hilfsmittel.
Sie sind kein Bestandteil des produktiven Installer-Builds
(tools\Installer bauen.bat).

1) analyze_venv.py
   Zeigt installierte Pakete der aktiven venv, ungefaehre Groesse pro Paket
   und bekannte "Heavy Packages". Nur lesend, keine Aenderungen.

   Im neuen CMD-Fenster:
   cd C:\manifest_fallschirm
   venv\Scripts\activate
   python tools\analyse\analyze_venv.py

2) find_unused_modules.py
   Findet .py-Dateien, die von definierten Entrypoints aus nicht (statisch)
   erreichbar sind.

   Im neuen CMD-Fenster:
   cd C:\manifest_fallschirm
   python tools\analyse\find_unused_modules.py --root C:\manifest_fallschirm --entry run.py --entry app\__init__.py
