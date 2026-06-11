# C:\manifest_fallschirm\migrate_billing_config_mail_fields.py
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Bekannte DB-Kandidaten (wie bei euch üblich)
CANDIDATES = [
    os.path.join(BASE_DIR, "database.sqlite"),
    os.path.join(BASE_DIR, "manifest.db"),
    os.path.join(BASE_DIR, "data", "manifest.db"),
    os.path.join(BASE_DIR, "app", "database.sqlite"),
    os.path.join(BASE_DIR, "app", "manifest.db"),
]


def find_db():
    for p in CANDIDATES:
        if os.path.exists(p):
            return p
    raise SystemExit(
        "Keine SQLite-DB gefunden. Erwartet z.B. data/manifest.db oder database.sqlite."
    )


def column_exists(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    return col in cols


def add_column(cur, table, col, coltype):
    sql = f"ALTER TABLE {table} ADD COLUMN {col} {coltype}"
    cur.execute(sql)


def main():
    db_path = find_db()
    print("DB:", db_path)

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    table = "billing_config"

    # Sicherstellen, dass Tabelle existiert
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    if not cur.fetchone():
        raise SystemExit(
            "Tabelle billing_config existiert nicht. Bitte zuerst DB anlegen."
        )

    columns = [
        ("mail_sender_address", "VARCHAR(255)"),
        ("mail_sender_name", "VARCHAR(255)"),
        ("mail_subject_template", "VARCHAR(255)"),
        ("mail_body_template", "TEXT"),
        ("mail_body_template_manual", "TEXT"),
    ]

    for col, coltype in columns:
        if column_exists(cur, table, col):
            print(f"OK: {col} existiert bereits")
        else:
            print(f"ADD: {col}")
            add_column(cur, table, col, coltype)

    cur.execute(
        "UPDATE billing_config "
        "   SET mail_body_template_manual = COALESCE(NULLIF(TRIM(mail_body_template_manual), ''), ?) "
        " WHERE mail_body_template_manual IS NULL OR TRIM(mail_body_template_manual) = ''",
        (
            "Liebe/r {first_name} {last_name},\n\n"
            "in der Anlage erhältst Du Deine Rechnung für {manual_title}.\n"
            "Sollte die Rechnung noch nicht bezahlt sein, bitten wir um Begleichung bis zwei Tage nach Erhalt der Rechnung.\n\n"
            "Bitte antworte nicht auf diese E-Mail, da sie automatisiert generiert wurde. Ggf. Kontakt siehe unten.\n\n"
            "Viele Grüße aus Dessau",
        ),
    )

    con.commit()
    con.close()

    print("Migration abgeschlossen. Starte Flask neu.")


if __name__ == "__main__":
    main()