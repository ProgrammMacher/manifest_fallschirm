# C:\manifest_fallschirm\app\db_migrations.py

from sqlalchemy import text

from app import db, create_app


def migrate_add_invoice_stage():
    """
    Fügt die Spalte 'stage' zur Tabelle 'invoice' hinzu,
    falls sie noch nicht existiert.

    - SQLite-kompatibel
    - Bestehende Rechnungen werden automatisch 'final'
    """
    print("== Migration: invoice.stage ==")

    result = db.session.execute(
        text("PRAGMA table_info(invoice);")
    ).fetchall()

    column_names = {row[1] for row in result}

    if "stage" in column_names:
        print("✔ Spalte 'stage' existiert bereits – keine Aktion nötig.")
        return

    print("➕ Füge Spalte 'stage' zur Tabelle 'invoice' hinzu …")

    db.session.execute(
        text(
            "ALTER TABLE invoice "
            "ADD COLUMN stage VARCHAR(10) NOT NULL DEFAULT 'final';"
        )
    )

    db.session.commit()
    print("✔ Migration abgeschlossen: 'invoice.stage' angelegt.")


def run_all_migrations():
    migrate_add_invoice_stage()


if __name__ == "__main__":
    # ✅ Flask Application Context korrekt aufbauen
    app = create_app()
    with app.app_context():
        run_all_migrations()