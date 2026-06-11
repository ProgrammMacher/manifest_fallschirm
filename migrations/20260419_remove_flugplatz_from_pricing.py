"""
Migration: Entfernt flugplatz_id aus Preismatrix-Tabellen

Hintergrund:
  Die Preismatrix gilt global für alle Flugplätze und alle Flugzeuge.
  flugplatz_id in billing_price / billing_orga_rule / billing_orga_config
  ist strukturell überflüssig und wird vollständig entfernt.

Tabellen:
  billing_price         (flugplatz_id, period_id, status_code, height_m, price_eur)
                     -> (period_id, status_code, height_m, price_eur)
  billing_orga_rule     (flugplatz_id, period_id, status_code, apply_orga)
                     -> (period_id, status_code, apply_orga)
  billing_orga_config   (flugplatz_id, period_id, orga_fee_eur, ...)
                     -> (period_id, orga_fee_eur, ...)

Duplikate: Da Preise / Regeln bereits für alle Flugplätze synchron gehalten
           wurden, werden beim Migrieren nur eindeutige Zeilen behalten.

Idempotent: Prüft vorher, ob flugplatz_id noch existiert.
SQLite-kompatibel: Tabellen werden neu erzeugt (kein ALTER TABLE DROP COLUMN).
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "manifest.db"


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table});")
    return any(row[1] == column for row in cursor.fetchall())


def table_exists(cursor, table: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cursor.fetchone() is not None


# ------------------------------------------------------------------
# billing_price
# ------------------------------------------------------------------
def migrate_billing_price(conn, cursor):
    if not column_exists(cursor, "billing_price", "flugplatz_id"):
        print("[OK] billing_price: flugplatz_id bereits entfernt – keine Aktion.")
        return

    print("[MIGRATION] billing_price: Entferne flugplatz_id …")
    cursor.execute("""
        CREATE TABLE billing_price_new (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            period_id   INTEGER NOT NULL REFERENCES billing_price_period(id),
            status_code VARCHAR(50) NOT NULL,
            height_m    INTEGER NOT NULL,
            price_eur   NUMERIC(10,2) NOT NULL,
            UNIQUE(period_id, status_code, height_m)
        )
    """)
    # Deduplizierung: MAX(price_eur) je Schlüssel (alle Flugplätze hatten denselben Wert)
    cursor.execute("""
        INSERT OR IGNORE INTO billing_price_new (period_id, status_code, height_m, price_eur)
        SELECT period_id, status_code, height_m, MAX(price_eur)
        FROM billing_price
        GROUP BY period_id, status_code, height_m
    """)
    rows = cursor.rowcount
    cursor.execute("DROP TABLE billing_price")
    cursor.execute("ALTER TABLE billing_price_new RENAME TO billing_price")
    conn.commit()
    print(f"[SUCCESS] billing_price: {rows} Zeile(n) übernommen.")


# ------------------------------------------------------------------
# billing_orga_rule
# ------------------------------------------------------------------
def migrate_billing_orga_rule(conn, cursor):
    if not table_exists(cursor, "billing_orga_rule"):
        print("[OK] billing_orga_rule: Tabelle existiert nicht – keine Aktion.")
        return
    if not column_exists(cursor, "billing_orga_rule", "flugplatz_id"):
        print("[OK] billing_orga_rule: flugplatz_id bereits entfernt – keine Aktion.")
        return

    print("[MIGRATION] billing_orga_rule: Entferne flugplatz_id …")
    cursor.execute("""
        CREATE TABLE billing_orga_rule_new (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            period_id   INTEGER NOT NULL REFERENCES billing_price_period(id),
            status_code VARCHAR(50) NOT NULL,
            apply_orga  BOOLEAN NOT NULL DEFAULT 1,
            UNIQUE(period_id, status_code)
        )
    """)
    # MAX(apply_orga): falls eine Regel True enthielt, bleibt True
    cursor.execute("""
        INSERT OR IGNORE INTO billing_orga_rule_new (period_id, status_code, apply_orga)
        SELECT period_id, status_code, MAX(apply_orga)
        FROM billing_orga_rule
        GROUP BY period_id, status_code
    """)
    rows = cursor.rowcount
    cursor.execute("DROP TABLE billing_orga_rule")
    cursor.execute("ALTER TABLE billing_orga_rule_new RENAME TO billing_orga_rule")
    conn.commit()
    print(f"[SUCCESS] billing_orga_rule: {rows} Zeile(n) übernommen.")


# ------------------------------------------------------------------
# billing_orga_config
# ------------------------------------------------------------------
def migrate_billing_orga_config(conn, cursor):
    if not table_exists(cursor, "billing_orga_config"):
        print("[OK] billing_orga_config: Tabelle existiert nicht – keine Aktion.")
        return
    if not column_exists(cursor, "billing_orga_config", "flugplatz_id"):
        print("[OK] billing_orga_config: flugplatz_id bereits entfernt – keine Aktion.")
        return

    print("[MIGRATION] billing_orga_config: Entferne flugplatz_id …")
    cursor.execute("""
        CREATE TABLE billing_orga_config_new (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            period_id             INTEGER NOT NULL REFERENCES billing_price_period(id),
            orga_fee_eur          NUMERIC(10,2) NOT NULL DEFAULT 0,
            orga_fee_mode         VARCHAR(20) NOT NULL DEFAULT 'period',
            orga_fee_vat_strategy VARCHAR(20) NOT NULL DEFAULT 'max_status',
            UNIQUE(period_id)
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO billing_orga_config_new
            (period_id, orga_fee_eur, orga_fee_mode, orga_fee_vat_strategy)
        SELECT period_id, MAX(orga_fee_eur), orga_fee_mode, orga_fee_vat_strategy
        FROM billing_orga_config
        GROUP BY period_id
    """)
    rows = cursor.rowcount
    cursor.execute("DROP TABLE billing_orga_config")
    cursor.execute("ALTER TABLE billing_orga_config_new RENAME TO billing_orga_config")
    conn.commit()
    print(f"[SUCCESS] billing_orga_config: {rows} Zeile(n) übernommen.")


# ------------------------------------------------------------------
# Hauptprogramm
# ------------------------------------------------------------------
def run_migration():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Datenbank nicht gefunden: {DB_PATH}")

    print(f"[INFO] Öffne Datenbank: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    # Foreign Keys kurz deaktivieren, damit DROP TABLE sicher funktioniert
    conn.execute("PRAGMA foreign_keys = OFF;")
    try:
        cur = conn.cursor()
        migrate_billing_price(conn, cur)
        migrate_billing_orga_rule(conn, cur)
        migrate_billing_orga_config(conn, cur)
        conn.execute("PRAGMA foreign_keys = ON;")
        print("[DONE] Alle Migrationsschritte abgeschlossen.")
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
