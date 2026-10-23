- billing.py > 5.000 Zeilen
- load.py > 4.000 Zeilen
- mehrere is_admin()-Implementierungen
- Default SECRET_KEY vorhanden
- smtp_password im Klartext gespeichert
- zwei parallele Migrationsmechanismen
- Altdateien im Repository

Portable Runtime kann von requirements.txt abweichen
Problem
Die mitgelieferte Runtime unter runtime/python/ kann vom dokumentierten Paketstand in requirements.txt und den Offline-Paketen unter packages/ abweichen.

Dadurch können Produktivstarts über Waitress fehlschlagen, obwohl Flask-Starts noch funktionieren.

Bekannter Reparaturbefehl
runtime\python\python.exe -m pip install --no-index --find-links=packages -r requirements.txt

Ziel
Klare Pflege- und Aktualisierungsstrategie für:

requirements.txt
packages/
runtime/python/
festlegen.