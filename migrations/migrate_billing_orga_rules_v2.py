# C:\manifest_fallschirm\migrate_billing_orga_rules_v2.py
import os
import sqlite3
from decimal import Decimal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Reihenfolge entspricht (laut v1) create_app() / Fallbacks
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
    raise SystemExit("Keine SQLite-DB gefunden. Erwartet z.B. data/manifest.db.")


def table_exists(cur, table):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


def column_exists(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    return col in cols


def add_column(cur, table, col, coltype, default_sql=None):
    if default_sql is None:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
    else:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype} DEFAULT {default_sql}")


def safe_exec(cur, sql, label=None):
    try:
        cur.execute(sql)
        if label:
            print("OK:", label)
    except sqlite3.OperationalError as e:
        # z.B. "index already exists" oder "trigger already exists"
        if "already exists" in str(e).lower():
            if label:
                print("OK:", label, "(exists)")
        else:
            raise


def main():
    db_path = find_db()
    print("DB:", db_path)

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # SQLite-FKs nur aktiv, wenn pragma gesetzt
    cur.execute("PRAGMA foreign_keys=ON")

    # ---------------------------------------------------------------------
    # 0) Vorbedingungen
    # ---------------------------------------------------------------------
    if not table_exists(cur, "billing_price_period"):
        raise SystemExit("Tabelle billing_price_period existiert nicht. Bitte DB initialisieren.")

    if not table_exists(cur, "flugplatz"):
        raise SystemExit("Tabelle flugplatz existiert nicht. Bitte DB initialisieren.")

    # ---------------------------------------------------------------------
    # 1) billing_price_period erweitern (wie v1, aber robust/idempotent)
    # ---------------------------------------------------------------------
    if not column_exists(cur, "billing_price_period", "orga_fee_mode"):
        print("ADD: billing_price_period.orga_fee_mode")
        add_column(cur, "billing_price_period", "orga_fee_mode", "TEXT", "'period'")
    else:
        print("OK: billing_price_period.orga_fee_mode")

    if not column_exists(cur, "billing_price_period", "orga_fee_vat_strategy"):
        print("ADD: billing_price_period.orga_fee_vat_strategy")
        add_column(cur, "billing_price_period", "orga_fee_vat_strategy", "TEXT", "'max_status'")
    else:
        print("OK: billing_price_period.orga_fee_vat_strategy")

    # ---------------------------------------------------------------------
    # 2) billing_orga_rule sicherstellen + Referenz-Trigger & Indizes
    # ---------------------------------------------------------------------
    if not table_exists(cur, "billing_orga_rule"):
        print("CREATE: billing_orga_rule")
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
    else:
        print("OK: billing_orga_rule")

    # Indizes (Performance)
    safe_exec(cur, "CREATE INDEX idx_billing_orga_rule_fp ON billing_orga_rule(flugplatz_id)", "idx_billing_orga_rule_fp")
    safe_exec(cur, "CREATE INDEX idx_billing_orga_rule_period ON billing_orga_rule(period_id)", "idx_billing_orga_rule_period")

    # Referenzprüfung via Trigger (wenn keine FK-Constraints existieren)
    safe_exec(
        cur,
        """
        CREATE TRIGGER trg_billing_orga_rule_ref_ins
        BEFORE INSERT ON billing_orga_rule
        FOR EACH ROW
        BEGIN
          SELECT RAISE(ABORT, 'billing_orga_rule: flugplatz_id does not exist')
          WHERE (SELECT id FROM flugplatz WHERE id = NEW.flugplatz_id) IS NULL;

          SELECT RAISE(ABORT, 'billing_orga_rule: period_id does not exist')
          WHERE (SELECT id FROM billing_price_period WHERE id = NEW.period_id) IS NULL;
        END;
        """,
        "trg_billing_orga_rule_ref_ins",
    )

    safe_exec(
        cur,
        """
        CREATE TRIGGER trg_billing_orga_rule_ref_upd
        BEFORE UPDATE OF flugplatz_id, period_id ON billing_orga_rule
        FOR EACH ROW
        BEGIN
          SELECT RAISE(ABORT, 'billing_orga_rule: flugplatz_id does not exist')
          WHERE (SELECT id FROM flugplatz WHERE id = NEW.flugplatz_id) IS NULL;

          SELECT RAISE(ABORT, 'billing_orga_rule: period_id does not exist')
          WHERE (SELECT id FROM billing_price_period WHERE id = NEW.period_id) IS NULL;
        END;
        """,
        "trg_billing_orga_rule_ref_upd",
    )

    # ---------------------------------------------------------------------
    # 3) NEU: billing_orga_config (Orga-Betrag + Mode/Strategy pro Flugplatz+Periode)
    # ---------------------------------------------------------------------
    if not table_exists(cur, "billing_orga_config"):
        print("CREATE: billing_orga_config")
        cur.execute(
            """
            CREATE TABLE billing_orga_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flugplatz_id INTEGER NOT NULL,
                period_id INTEGER NOT NULL,
                orga_fee_eur NUMERIC NOT NULL DEFAULT 0,
                orga_fee_mode TEXT NOT NULL DEFAULT 'period',
                orga_fee_vat_strategy TEXT NOT NULL DEFAULT 'max_status',
                UNIQUE (flugplatz_id, period_id)
            )
            """
        )
    else:
        print("OK: billing_orga_config")

    safe_exec(cur, "CREATE INDEX idx_billing_orga_cfg_fp ON billing_orga_config(flugplatz_id)", "idx_billing_orga_cfg_fp")
    safe_exec(cur, "CREATE INDEX idx_billing_orga_cfg_period ON billing_orga_config(period_id)", "idx_billing_orga_cfg_period")

    # Referenz-Trigger für billing_orga_config
    safe_exec(
        cur,
        """
        CREATE TRIGGER trg_billing_orga_cfg_ref_ins
        BEFORE INSERT ON billing_orga_config
        FOR EACH ROW
        BEGIN
          SELECT RAISE(ABORT, 'billing_orga_config: flugplatz_id does not exist')
          WHERE (SELECT id FROM flugplatz WHERE id = NEW.flugplatz_id) IS NULL;

          SELECT RAISE(ABORT, 'billing_orga_config: period_id does not exist')
          WHERE (SELECT id FROM billing_price_period WHERE id = NEW.period_id) IS NULL;
        END;
        """,
        "trg_billing_orga_cfg_ref_ins",
    )

    safe_exec(
        cur,
        """
        CREATE TRIGGER trg_billing_orga_cfg_ref_upd
        BEFORE UPDATE OF flugplatz_id, period_id ON billing_orga_config
        FOR EACH ROW
        BEGIN
          SELECT RAISE(ABORT, 'billing_orga_config: flugplatz_id does not exist')
          WHERE (SELECT id FROM flugplatz WHERE id = NEW.flugplatz_id) IS NULL;

          SELECT RAISE(ABORT, 'billing_orga_config: period_id does not exist')
          WHERE (SELECT id FROM billing_price_period WHERE id = NEW.period_id) IS NULL;
        END;
        """,
        "trg_billing_orga_cfg_ref_upd",
    )

    # ---------------------------------------------------------------------
    # 4) Datumsvalidierung + Overlap-Schutz für billing_price_period (Trigger)
    # ---------------------------------------------------------------------
    # valid_to < valid_from verhindern
    safe_exec(
        cur,
        """
        CREATE TRIGGER trg_bpp_date_sanity_ins
        BEFORE INSERT ON billing_price_period
        FOR EACH ROW
        WHEN NEW.valid_to IS NOT NULL AND NEW.valid_to < NEW.valid_from
        BEGIN
          SELECT RAISE(ABORT, 'billing_price_period: valid_to < valid_from');
        END;
        """,
        "trg_bpp_date_sanity_ins",
    )
    safe_exec(
        cur,
        """
        CREATE TRIGGER trg_bpp_date_sanity_upd
        BEFORE UPDATE OF valid_from, valid_to ON billing_price_period
        FOR EACH ROW
        WHEN NEW.valid_to IS NOT NULL AND NEW.valid_to < NEW.valid_from
        BEGIN
          SELECT RAISE(ABORT, 'billing_price_period: valid_to < valid_from');
        END;
        """,
        "trg_bpp_date_sanity_upd",
    )

    # Overlap verhindern (open-ended valid_to zählt als "unendlich")
    # Überlappungskriterium: [from, to] schneidet [from2, to2]
    # => from <= to2 AND from2 <= to
    safe_exec(
        cur,
        """
        CREATE TRIGGER trg_bpp_no_overlap_ins
        BEFORE INSERT ON billing_price_period
        FOR EACH ROW
        BEGIN
          SELECT RAISE(ABORT, 'billing_price_period: overlapping period')
          WHERE EXISTS (
            SELECT 1
            FROM billing_price_period p
            WHERE
              (NEW.valid_from <= COALESCE(p.valid_to, '9999-12-31'))
              AND (p.valid_from <= COALESCE(NEW.valid_to, '9999-12-31'))
          );
        END;
        """,
        "trg_bpp_no_overlap_ins",
    )

    safe_exec(
        cur,
        """
        CREATE TRIGGER trg_bpp_no_overlap_upd
        BEFORE UPDATE OF valid_from, valid_to ON billing_price_period
        FOR EACH ROW
        BEGIN
          SELECT RAISE(ABORT, 'billing_price_period: overlapping period')
          WHERE EXISTS (
            SELECT 1
            FROM billing_price_period p
            WHERE
              p.id <> OLD.id
              AND (NEW.valid_from <= COALESCE(p.valid_to, '9999-12-31'))
              AND (p.valid_from <= COALESCE(NEW.valid_to, '9999-12-31'))
          );
        END;
        """,
        "trg_bpp_no_overlap_upd",
    )

    # ---------------------------------------------------------------------
    # 5) Backfill: billing_orga_config aus vorhandenen Preisen/Perioden befüllen
    # ---------------------------------------------------------------------
    # Nur Kombinationen, die im billing_price vorkommen (=> relevant)
    if table_exists(cur, "billing_price"):
        cur.execute("SELECT DISTINCT flugplatz_id, period_id FROM billing_price")
        pairs = cur.fetchall()
    else:
        pairs = []

    inserted = 0
    skipped = 0

    for row in pairs:
        fp_id = int(row["flugplatz_id"])
        period_id = int(row["period_id"])

        # existiert schon?
        cur.execute(
            "SELECT id FROM billing_orga_config WHERE flugplatz_id=? AND period_id=?",
            (fp_id, period_id),
        )
        if cur.fetchone():
            skipped += 1
            continue

        # Basis aus billing_price_period
        cur.execute(
            "SELECT orga_fee_eur, orga_fee_mode, orga_fee_vat_strategy FROM billing_price_period WHERE id=?",
            (period_id,),
        )
        p = cur.fetchone()
        period_amount = Decimal(str(p["orga_fee_eur"])) if p and p["orga_fee_eur"] is not None else Decimal("0")
        mode = (p["orga_fee_mode"] if p and p["orga_fee_mode"] else "period")
        strat = (p["orga_fee_vat_strategy"] if p and p["orga_fee_vat_strategy"] else "max_status")

        amount = period_amount

        # Legacy fallback: billing_price mit status_code="Orga" und height_m=0 (pro Flugplatz+Periode)
        if amount <= 0:
            cur.execute(
                """
                SELECT price_eur
                FROM billing_price
                WHERE flugplatz_id=? AND period_id=? AND status_code='Orga' AND height_m=0
                ORDER BY id DESC
                LIMIT 1
                """,
                (fp_id, period_id),
            )
            legacy = cur.fetchone()
            if legacy and legacy["price_eur"] is not None:
                amount = Decimal(str(legacy["price_eur"]))

        cur.execute(
            """
            INSERT INTO billing_orga_config (flugplatz_id, period_id, orga_fee_eur, orga_fee_mode, orga_fee_vat_strategy)
            VALUES (?, ?, ?, ?, ?)
            """,
            (fp_id, period_id, str(amount), mode, strat),
        )
        inserted += 1

    # ---------------------------------------------------------------------
    # 6) Diagnoseausgaben (zeigt dir die "Datumsprobleme" direkt)
    # ---------------------------------------------------------------------
    # 6a) Unplausible Perioden
    cur.execute(
        """
        SELECT id, name, valid_from, valid_to
        FROM billing_price_period
        WHERE valid_to IS NOT NULL AND valid_to < valid_from
        """
    )
    bad = cur.fetchall()
    if bad:
        print("WARN: Unplausible billing_price_period (valid_to < valid_from):")
        for b in bad:
            print("  -", dict(b))

    # 6b) Overlaps (nur Report; Trigger verhindert nur zukünftige)
    cur.execute(
        """
        SELECT p1.id AS id1, p1.name AS name1, p1.valid_from AS from1, p1.valid_to AS to1,
               p2.id AS id2, p2.name AS name2, p2.valid_from AS from2, p2.valid_to AS to2
        FROM billing_price_period p1
        JOIN billing_price_period p2 ON p1.id < p2.id
        WHERE (p1.valid_from <= COALESCE(p2.valid_to, '9999-12-31'))
          AND (p2.valid_from <= COALESCE(p1.valid_to, '9999-12-31'))
        """
    )
    overlaps = cur.fetchall()
    if overlaps:
        print("WARN: Überlappende Preisperioden gefunden (bestehende Daten):")
        for o in overlaps[:50]:
            print("  -", dict(o))
        if len(overlaps) > 50:
            print("  ... (weitere Overlaps vorhanden)")

    con.commit()
    con.close()

    print("Migration v2 abgeschlossen.")
    print(f"billing_orga_config: +{inserted} neu, {skipped} vorhanden.")


if __name__ == "__main__":
    main()