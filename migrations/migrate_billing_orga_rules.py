# C:\manifest_fallschirm\migrate_billing_orga_rules.py
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------
# Datenbank-Kandidaten
# Reihenfolge entspricht exakt create_app()
# ---------------------------------------------------------
CANDIDATES = [
    # produktive DB (Standard)
    os.path.join(BASE_DIR, "data", "manifest.db"),
    os.path.join(BASE_DIR, "data", "database.sqlite"),

    # ältere / alternative Pfade
    os.path.join(BASE_DIR, "manifest.db"),
    os.path.join(BASE_DIR, "database.sqlite"),

    # app-Unterordner (bei dir vorhanden, aber leer)
    os.path.join(BASE_DIR, "app", "manifest.db"),
    os.path.join(BASE_DIR, "app", "database.sqlite"),
]

def find_db():
    # ENV überschreibt alles (wie in create_app)
    env_db_path = os.environ.get("MANIFEST_DB_PATH", "").strip()
    if env_db_path and os.path.exists(env_db_path):
        return env_db_path

    for p in CANDIDATES:
        if os.path.exists(p):
            return p

    raise SystemExit(
        "Keine SQLite-DB gefunden. Erwartet z.B. data/manifest.db oder manifest.db im Projektordner."
    )

def table_exists(cur, table):
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cur.fetchone() is not None

def column_exists(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    return col in cols

def add_column(cur, table, col, coltype, default_sql=None):
    if default_sql is None:
        sql = f"ALTER TABLE {table} ADD COLUMN {col} {coltype}"
    else:
        sql = f"ALTER TABLE {table} ADD COLUMN {col} {coltype} DEFAULT {default_sql}"
    cur.execute(sql)

def main():
    db_path = find_db()
    print("DB:", db_path)

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # -----------------------------------------------------
    # 1) billing_price_period erweitern
    # -----------------------------------------------------
    period_table = "billing_price_period"

    if not table_exists(cur, period_table):
        raise SystemExit(
            "Tabelle billing_price_period existiert nicht. "
            "Bitte zuerst DB mit der App initialisieren."
        )

    # Orga-Modus: 'period' oder 'day'
    if column_exists(cur, period_table, "orga_fee_mode"):
        print("OK: billing_price_period.orga_fee_mode existiert bereits")
    else:
        print("ADD: billing_price_period.orga_fee_mode")
        add_column(
            cur,
            period_table,
            "orga_fee_mode",
            "TEXT",
            "'period'",
        )

    # Strategie für MwSt-Ermittlung der Orga
    # (z. B. max_status = maximaler MwSt-Satz aller orga-relevanten Status)
    if column_exists(cur, period_table, "orga_fee_vat_strategy"):
        print("OK: billing_price_period.orga_fee_vat_strategy existiert bereits")
    else:
        print("ADD: billing_price_period.orga_fee_vat_strategy")
        add_column(
            cur,
            period_table,
            "orga_fee_vat_strategy",
            "TEXT",
            "'max_status'",
        )

    # -----------------------------------------------------
    # 2) Neue Tabelle: billing_orga_rule
    # Orga pro Status pro Flugplatz + Periode
    # -----------------------------------------------------
    orga_table = "billing_orga_rule"

    if table_exists(cur, orga_table):
        print("OK: Tabelle billing_orga_rule existiert bereits")
    else:
        print("CREATE: Tabelle billing_orga_rule")
        cur.execute(
            """
            CREATE TABLE billing_orga_rule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flugplatz_id INTEGER NOT NULL,
                period_id INTEGER NOT NULL,
                status_code TEXT NOT NULL,
                apply_orga INTEGER NOT NULL DEFAULT 1,
                UNIQUE (flugplatz_id, period_id, status_code)
            )
            """
        )

    con.commit()
    con.close()

    print("Migration abgeschlossen. Starte Flask neu.")

if __name__ == "__main__":
    main()