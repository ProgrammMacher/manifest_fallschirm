# C:\manifest_fallschirm\migrate_billing_price_period_overlap_policy.py
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CANDIDATES = [
    os.path.join(BASE_DIR, "data", "manifest.db"),
    os.path.join(BASE_DIR, "data", "database.sqlite"),
    os.path.join(BASE_DIR, "manifest.db"),
    os.path.join(BASE_DIR, "database.sqlite"),
    os.path.join(BASE_DIR, "app", "manifest.db"),
    os.path.join(BASE_DIR, "app", "database.sqlite"),
]

def find_db():
    env_db_path = os.environ.get("MANIFEST_DB_PATH", "").strip()
    if env_db_path and os.path.exists(env_db_path):
        return env_db_path
    for p in CANDIDATES:
        if os.path.exists(p):
            return p
    raise SystemExit("Keine SQLite-DB gefunden (z.B. data/manifest.db).")

def table_exists(cur, table):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None

def drop_trigger(cur, name):
    cur.execute(f"DROP TRIGGER IF EXISTS {name}")

def main():
    db_path = find_db()
    print("DB:", db_path)

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys=ON")

    if not table_exists(cur, "billing_price_period"):
        raise SystemExit("Tabelle billing_price_period existiert nicht.")

    # ---------------------------------------------------------
    # 1) Alte harte Overlap-Trigger entfernen
    # ---------------------------------------------------------
    print("DROP: trg_bpp_no_overlap_ins / trg_bpp_no_overlap_upd")
    drop_trigger(cur, "trg_bpp_no_overlap_ins")
    drop_trigger(cur, "trg_bpp_no_overlap_upd")

    # ---------------------------------------------------------
    # 2) Neue Overlap-Regel nur für Default-Perioden
    #    (is_homebase_default = 1)
    # ---------------------------------------------------------
    print("CREATE: trg_bpp_no_overlap_default_ins / upd")

    cur.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_bpp_no_overlap_default_ins
    BEFORE INSERT ON billing_price_period
    FOR EACH ROW
    WHEN NEW.is_homebase_default = 1
    BEGIN
      SELECT RAISE(ABORT, 'billing_price_period: overlapping default period')
      WHERE EXISTS (
        SELECT 1
        FROM billing_price_period p
        WHERE p.is_homebase_default = 1
          AND (NEW.valid_from <= COALESCE(p.valid_to, '9999-12-31'))
          AND (p.valid_from <= COALESCE(NEW.valid_to, '9999-12-31'))
      );
    END;
    """)

    cur.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_bpp_no_overlap_default_upd
    BEFORE UPDATE OF valid_from, valid_to, is_homebase_default ON billing_price_period
    FOR EACH ROW
    WHEN NEW.is_homebase_default = 1
    BEGIN
      SELECT RAISE(ABORT, 'billing_price_period: overlapping default period')
      WHERE EXISTS (
        SELECT 1
        FROM billing_price_period p
        WHERE p.id <> OLD.id
          AND p.is_homebase_default = 1
          AND (NEW.valid_from <= COALESCE(p.valid_to, '9999-12-31'))
          AND (p.valid_from <= COALESCE(NEW.valid_to, '9999-12-31'))
      );
    END;
    """)

    con.commit()
    con.close()
    print("Migration abgeschlossen. Overlap ist jetzt nur noch für Default-Perioden gesperrt.")

if __name__ == "__main__":
    main()