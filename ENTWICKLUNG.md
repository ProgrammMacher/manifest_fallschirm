# ENTWICKLUNG.md

MANIFeST OU: Entwicklungs-, Test- und Migrationsleitfaden

**Stand:** Oktober 2026  
**Git-HEAD:** 3bb67bdb  
**Letzte Änderungen:** TECHNISCHE_SCHULDEN.md, ARCHITEKTUR.md, REGELN.md hinzugefügt

---

## 📋 Legende

- ✅ **Verifiziert:** Im Code/Skripten belegt
- 🔍 **Annahme:** Plausibel, aber nicht direkt belegt  
- ❓ **Offen:** Muss vom Projektverantwortlichen beantwortet werden

---

## 1. Entwicklungsumgebung

### 1.1 Python und Abhängigkeiten

✅ **Python Version:** 3.14.2 (Entwicklung und CI)  
✅ **Hauptabhängigkeiten:** 
- Flask 3.1.2
- SQLAlchemy 2.0.46  
- Flask-Migrate 4.1.0
- Alembic 1.18.4
- WeasyPrint 68.1
- Waitress 3.0.2

✅ **Testframework:** pytest 9.1.1 (nicht in requirements.txt gepinnt)

### 1.2 Betriebssystem

✅ **Zielplattform:** Windows  
- BAT/VBS-Skripte vorhanden
- GTK-Runtime für WeasyPrint erforderlich
- Ein Test explizit Windows-only (`test_license_mfs2.py`)

### 1.3 Konfiguration

✅ **Keine Linter/Formatter-Konfiguration** vorhanden (pytest.ini, pyproject.toml, setup.cfg, tox.ini, conftest.py)

---

## 2. Anwendung starten

### 2.1 Startskripte

✅ **Entwicklung:** `python run.py`
- Flask debug mode auf 0.0.0.0:5000
- Öffnet automatisch Browser unter `http://127.0.0.1:5000/pwa/`

✅ **Produktion:** `manifest_launcher.py` über Batch/VBS-Skripte

### 2.2 Umgebungsvariablen

✅ **Wichtige ENV-Variablen** (alle in `app/__init__.py` ausgewertet):

| Variable | Standardwert | Beschreibung |
|----------|-------------|-------------|
| `MANIFEST_ENV` | `development` | Laufzeitumgebung |
| `MANIFEST_DB_PATH` | - | Datenbankpfad (hat Priorität) |
| `MANIFEST_RUNTIME_HOME` | - | Runtime-Verzeichnis |
| `MANIFEST_SECRET_KEY` | `"bitte-später-ändern"` | Session-Schlüssel |
| `MANIFEST_AUTO_DB_UPGRADE` | `1` | Automatische DB-Upgrades |
| `MANIFEST_AUTO_CREATE_DB` | `1` | Automatische DB-Erstellung |
| `MANIFEST_ENABLE_MIGRATIONS` | `0` | Migrations-Tools aktivieren |

✅ **Datenbankpfad-Logik** (`app/__init__.py:173-184`):
1. `MANIFEST_DB_PATH` gesetzt → verwendet diesen Pfad
2. Sonst: `<DATA_DIR>/manifest.db`  
3. Fallback: Alte `manifest.db` im Projektroot (nur bei Migration)

🔍 **Bei Entwicklung ohne gesetztes `MANIFEST_DB_PATH`** arbeitet man gegen `data/manifest.db`, die laut `.gitignore` nicht versioniert ist.

---

## 3. Datenbank und Migrationen

### 3.1 Migrationsmechanismen

✅ **Drei verschiedene Systeme** vorhanden:

| System | Ort | Verwendung |
|--------|-----|------------|
| **A** Alembic | `migrations/versions/*.py` | Primärsystem, idempotent |
| **B** SQL-Funktionen | `app/helpers/db_migrations.py` | Idempotente Fallback-Migrationen |
| **C** Manuelle Skripte | `migrations/*.py` (nicht versions/) | Manuelle Ausführung |

❓ **Offen:** Warum existieren System C-Skripte? Sollen sie archiviert werden?

### 3.2 Startup-Ablauf (`app/__init__.py:362-434`)

✅ **Bestehende DB** (`database_was_missing == False`):
1. Wenn `MANIFEST_AUTO_DB_UPGRADE=1` (Standard): `flask_migrate.upgrade(directory="migrations", revision="heads")`
   - Fehler werden mit `except BaseException` abgefangen (nur Warnung)
   - Grund: `flask_migrate` ruft `sys.exit(1)` auf (`SystemExit` ist keine `Exception`)
2. Danach immer: `run_startup_migrations()` (Mechanismus B)
3. Dann: `db.create_all()` für fehlende Tabellen (nur Tabellen, keine Spalten)

✅ **Neue DB** (`database_was_missing == True`):
1. `db.create_all()` erzeugt Schema aus Modellen
2. `stamp(directory="migrations", revision="heads")` markiert alle Migrationen als erledigt
3. `seed_neutral_installation()` legt Startdaten an
4. Mechanismus A und B laufen in diesem Fall **nicht**

⚠️ **Folgerung:** Eine neue Spalte muss im Modell stehen (für Neuinstallationen) **und** in einer Migration (für Bestandsdatenbanken).

### 3.3 Alembic-Besonderheiten

✅ **`sourceless = true`** in `migrations/alembic.ini` 
- Installer liefert Migrationen nur als `.pyc` aus
- Test `test_alembic_ini_declares_sourceless` sichert dies ab

✅ **Mehrere Heads vorhanden** (aus `revision`/`down_revision`-Analyse):
- `20260504_add_fuel_required_to_load` 
- `20260903_add_mobile_person_intake_draft`

✅ **Revisions-IDs:** Gemischt (Hex vs. Datumsformat)
- Alt: zufällige Hex-IDs (`dd1561c497a7`)
- Neu: Datum und Beschreibung (`20260903_add_mobile_person_intake_draft`)

✅ **Struktur neuerer Migrationen:** Existenzprüfung über `sa.inspect(op.get_bind())`, `upgrade()` ohne Aktion wenn schon vorhanden

✅ **`env.py`:** DB-URL kommt aus Flask-App, `sqlalchemy.url` in `alembic.ini` wird überschrieben

### 3.4 Migrationen ausführen

✅ **Manuell:** `python run_migrations.py`
- Führt `upgrade(revision='heads')` aus
- Gibt `MIGRATION_OK` oder `MIGRATION_ERROR: ...` aus
- Ändert keinen Exit-Code bei Fehlern

### 3.5 Details zu `app/helpers/db_migrations.py`

✅ **966 Zeilen** mit Hilfsfunktionen:
- `_table_exists()` (SQLite `sqlite_master`)
- `_column_exists()` (SQLite `PRAGMA table_info`)

✅ **`run_startup_migrations()`** ruft 23 `ensure_*`-Funktionen in fester Reihenfolge auf

⚠️ **Enthält Datenänderungen:** `ensure_partner_verein_status_and_prices()` legt Statuswerte an und kopiert per `INSERT ... SELECT` Preise und `billing_orga_rule`-Einträge

❓ **Offen:** Muss zusätzlich ein `ensure_*` in `db_migrations.py` erstellt werden?

### 3.6 Neue Datenbankänderungen

✅ **Checkliste:**
1. Modell in `app/models/` anpassen
2. Alembic-Migration erstellen (idempotent)
3. Modell in `create_app()` importieren (Liste ab `app/__init__.py:400`)

---


## 4. Tests

### 4.1 Testausführung

🔍 **Vermuteter Befehl:** `python -m pytest tests`

✅ **Testabdeckung** (22 Dateien + 1 MD):

| Bereich | Dateien |
|---------|---------|
| Abrechnung/Rechnung | 9 Dateien (inkl. `test_ku_tandemmaster_regressions.py` - 43KB) |
| SEPA | 3 Dateien |
| Preise | 3 Dateien |
| Migrationen | 1 Datei |
| Lizenz/Installer | 6 Dateien |

❓ **Offen:** Vollständiger grüner Teststand? Fehleranfällige Tests?

### 4.2 Testmuster

✅ **Fixtures verwenden** `tmp_path` + Umgebungsvariablen:
```python
monkeypatch.setenv("MANIFEST_RUNTIME_HOME", str(runtime_home))
monkeypatch.setenv("MANIFEST_DB_PATH", str(db_file)) 
monkeypatch.setenv("MANIFEST_ENV", "dev")
monkeypatch.setenv("MANIFEST_AUTO_DB_UPGRADE", "0")
monkeypatch.setenv("MANIFEST_AUTO_CREATE_DB", "1")
```

⚠️ **Achtung:** Einige Tests setzen `os.environ` direkt (`test_invoice_payment_method_clear.py`, `test_migrations_sourceless.py`) - Potenzial für Seiteneffekte

### 4.3 Manueller Test

✅ **Smoketest:** `e2e_smoketest_abrechnung_import.md`
- Manueller Testplan (90-120 Min.)
- Abrechnung, Rechnungen, Export/Import
- Stand: 04.05.2026

### 4.4 Fehlende Prüfung

❓ **Keine Testprüfung** gegen echte `data/manifest.db` oder Test-Datenbankvorlage mit Altdaten

---

## 5. CI und Build

### 5.1 GitHub Actions

✅ **Einziger Workflow:** `.github/workflows/build-installer.yml`
- Nur manuell auslösbar (`workflow_dispatch`)
- Windows-only
- `contents: read` Berechtigung
- **Keine Tests in CI integriert**

### 5.2 Installer-Build

✅ **Schritte:**
1. Python 3.14.2 einrichten (exakt)
2. Portable Runtime `runtime/python` bereitstellen
3. Inno Setup per Chocolatey installieren
4. `tools\build_inno_offline_setup.ps1 -ProjectRoot ...` ausführen
5. Prüfen, dass `build\installer\manifest_ou_1_2.exe` entsteht
6. ZIP-Inhalt validieren und Artefakt hochladen (30 Tage)

✅ **ZIP muss enthalten:** 
- `.pyc`-Dateien (`app/__init__.pyc`, `migrations/env.pyc`, `run_migrations.pyc`, etc.)
- Python- und GTK-Runtime
- Offline-Wheels in `packages/`
- `cryptography` und `flask` in Runtime-`site-packages`

✅ **ZIP darf nicht enthalten:** 
- `data/`, `logs/`, `session_data/`, `uploads/`, `noch_zu_loeschen/`
- `app_settings.json`, `auth_config.json`
- `*.db|sqlite|sqlite3`, `*.log`
- `runtime/gtk/var/cache/`

⚠️ **Folge für Entwickler:** Alle Dateien werden als `.pyc` ausgeliefert - müssen kompilierbar sein

### 5.3 Runtime-Konsistenzprüfung (`tools/check_runtime_consistency.py`)

✅ **Quelle der Wahrheit:** `requirements.txt`. `packages/` (Offline-Wheels) und `runtime/python/` (portable Runtime) müssen exakt dazu passen.

✅ **Zweck:** Erkennt Drift zwischen `requirements.txt`, `packages/` und `runtime/python/`, bevor Produktiv- oder Waitress-Starts (`start_manifest_prod.bat`, `start_manifest_waitress_dev.bat`) daran scheitern.

✅ **Aufruf (lokal, aus dem Projektordner):**
```
python tools\check_runtime_consistency.py
```
Optional: `--project-root <Pfad>`. Es genügt jeder Python-Interpreter, die Runtime selbst wird nicht gestartet.

✅ **Das Skript arbeitet ausschließlich lesend:**
- kein `pip install`, kein `pip download`, keine Netzwerkzugriffe
- keine Dateien werden geschrieben, geändert oder gelöscht
- `runtime/python/` und `packages/` bleiben unverändert
- keine automatische Reparatur

Gelesen werden nur Namen: `requirements.txt` (Format `name==version`), die Dateinamen in `packages/*.whl` und die Ordner `runtime/python/Lib/site-packages/*.dist-info`. Paketnamen werden nach PEP 503 normalisiert (`Flask-SQLAlchemy` = `flask_sqlalchemy`).

| Befund | Wirkung |
|--------|---------|
| Paket aus `requirements.txt` fehlt in `runtime/python` | **Fehler** (Exit-Code 1) |
| Paket in `runtime/python` hat andere Version | **Fehler** (Exit-Code 1) |
| Wheel `name==version` fehlt in `packages/` | **Fehler** (Exit-Code 1) |
| `requirements.txt`, `packages/` oder `site-packages` fehlt, oder Zeile ist kein `name==version`-Pin | **Fehler** (Exit-Code 1) |
| Zusätzliches Paket in `runtime/python` (nicht in `requirements.txt`) | Warnung, Exit-Code 0 |
| Zusätzliches Wheel in `packages/` (nicht in `requirements.txt`) | Warnung, Exit-Code 0 |

`pip`, `setuptools` und `wheel` in der Runtime lösen keine Warnung aus. Transitive Abhängigkeiten müssen wie bisher selbst in `requirements.txt` gepinnt stehen (aktuelle Praxis, z. B. `six`, `idna`, `cffi`).

✅ **GitHub Actions:** Der Schritt „Check runtime consistency (read-only)“ in `.github/workflows/build-installer.yml` läuft direkt nach `setup-python`, vor der Runtime-Bereitstellung. Bei Exit-Code 1 schlägt der Build fehl. Warnungen blockieren nicht.

✅ **Manuelle Reparatur** (wird vom Skript nur ausgegeben, nie ausgeführt):
```
runtime\python\python.exe -m pip install --no-index --find-links=packages -r requirements.txt
```
Fehlt ein Wheel in `packages/`, muss es zuerst ergänzt werden. Die Reparatur ändert `runtime/python/Lib/site-packages`. Da `runtime/*` in `.gitignore` steht, müssen neu hinzugekommene Dateien mit `git add -f` aufgenommen und entfernte Dateien mitcommittet werden, sonst weicht die eingecheckte Runtime weiter ab.

✅ **Pflegeregel:** Änderungen an Paketen immer in dieser Reihenfolge: (1) `requirements.txt` anpassen, (2) Wheels in `packages/` ergänzen/entfernen, (3) Reparaturbefehl ausführen, (4) Prüfskript ausführen, (5) alles gemeinsam committen.

✅ **Tests:** `tests/test_check_runtime_consistency.py` (u. a. Nachweis, dass das Skript nichts verändert).


---

## 6. Git

✅ **Branch:** `main` aktiv  
✅ **Commit-Konvention:** Deutsch, Indikativ/Partizip  
✅ **Gitignore:** Schließt Runtime-Daten aus (`runtime/*`)

❓ **Offen:** Wie wird `runtime/python/Lib` mit `.gitignore` gehandhabt? CI erwartet "Checked-in portable Python library tree"

---

## 7. Offene Fragen

1. **Migrations-Strategie:** Sollen neue Spalten zusätzlich in `db_migrations.py`?
2. **System C-Skripte:** Dürfen nicht-versions Skripte archiviert werden?
3. **Testabdeckung:** Welche Tests sind kritisch/fehleranfällig?
4. **Schema-Stände:** Welche DB-Versionen laufen bei Kunden?
5. **Runtime in Git:** Wie wird der Konflikt mit `.gitignore` gelöst?
6. **Smoketest:** Wann ist der manuelle Test Pflicht?
7. **Linting:** Soll ein Linter/Formatter eingeführt werden?
8. **Test-Daten:** Gibt es eine Test-Datenbankvorlage mit Altdaten?

---

## 📞 Support

Bei Fragen zu Migrationen, Tests oder Build-Prozessen:
1. ARCHITEKTUR.md konsultieren
2. REGELN.md für Projektregeln beachten  
3. TECHNISCHE_SCHULDEN.md für bekannte Issues

**Hinweis:** Diese Datei basiert auf Code-Analyse vom Oktober 2026. Bei Änderungen an der Architektur bitte aktualisieren.

