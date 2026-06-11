"""
Migration: add fuel_required to load

- Fügt der Tabelle `load` die Spalte `fuel_required` hinzu
- Reine Informationsspalte (0/1)
- Default = 0 (kein Tanken erforderlich)
- SQLite-kompatibel
- Idempotent: prüft vorher, ob Spalte bereits existiert
"""

import sqlite3
from pathlib import Path


# ------------------------------------------------------------
# KONFIGURATION
# ------------------------------------------------------------
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "manifest.db"
TABLE_NAME = "load"
COLUMN_NAME = "fuel_required"


def column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def run_migration():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Datenbank nicht gefunden: {DB_PATH}")

    print(f"[INFO] Öffne Datenbank: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        if column_exists(cur, TABLE_NAME, COLUMN_NAME):
            print(f"[OK] Spalte '{COLUMN_NAME}' existiert bereits – keine Aktion nötig.")
            return

        print(f"[MIGRATION] Füge Spalte '{COLUMN_NAME}' zur Tabelle '{TABLE_NAME}' hinzu …")

        cur.execute(
            f"""
            ALTER TABLE {TABLE_NAME}
            ADD COLUMN {COLUMN_NAME} INTEGER NOT NULL DEFAULT 0
            """
        )

        conn.commit()
        print(f"[SUCCESS] Migration erfolgreich abgeschlossen.")

    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()