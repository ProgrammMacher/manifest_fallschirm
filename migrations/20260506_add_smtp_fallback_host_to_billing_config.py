"""
Migration: Fügt smtp_fallback_host zur billing_config hinzu

Hintergrund:
  Der optionale Fallback-SMTP-Host erlaubt es, bei DNS-Ausfällen
  (z.B. DENIC-Störung Mai 2026) auf einen alternativen Hostnamen
  auszuweichen. IONOS-Empfehlung: smtp.1und1.com (nicht .de).
  Für GMX, Web.de, T-Online bleibt das Feld leer.

Idempotent: Prüft vorher, ob smtp_fallback_host bereits existiert.
SQLite-kompatibel: ALTER TABLE ADD COLUMN.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "manifest.db"


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table});")
    return any(row[1] == column for row in cursor.fetchall())


def run():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        if not column_exists(cur, "billing_config", "smtp_fallback_host"):
            cur.execute(
                "ALTER TABLE billing_config ADD COLUMN smtp_fallback_host VARCHAR(255) NULL;"
            )
            print("Spalte smtp_fallback_host hinzugefügt.")
        else:
            print("Spalte smtp_fallback_host bereits vorhanden – übersprungen.")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    run()
