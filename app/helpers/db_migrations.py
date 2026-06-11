# C:\manifest_fallschirm\app\helpers\db_migrations.py
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from app import db


def _table_exists(table_name: str) -> bool:
    """
    SQLite: Prüft, ob eine Tabelle existiert.
    """
    result = db.session.execute(
        text(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name=:table_name
            """
        ),
        {"table_name": table_name},
    ).fetchone()

    return result is not None


def _column_exists(table_name: str, column_name: str) -> bool:
    """
    SQLite: Prüft über PRAGMA table_info, ob eine Spalte existiert.
    """
    rows = db.session.execute(
        text(f"PRAGMA table_info({table_name})")
    ).fetchall()

    for r in rows:
        # PRAGMA table_info liefert: cid, name, type, notnull, dflt_value, pk
        if len(r) >= 2 and str(r[1]).lower() == column_name.lower():
            return True
    return False


def ensure_load_pricing_model_id_column() -> None:
    """
    Idempotente Migration:
    - Fügt load.pricing_model_id hinzu, falls nicht vorhanden.
    - Legt einen Index an.
    - Ist sicher bei:
        * leerer DB
        * mehrfachen App-Starts
        * bereits existierendem Schema
    """

    # Tabelle existiert noch nicht → Migration überspringen
    if not _table_exists("load"):
        return

    if not _column_exists("load", "pricing_model_id"):
        db.session.execute(
            text("ALTER TABLE load ADD COLUMN pricing_model_id INTEGER")
        )

    # Index immer sicherstellen
    db.session.execute(
        text(
            "CREATE INDEX IF NOT EXISTS "
            "ix_load_pricing_model_id ON load (pricing_model_id)"
        )
    )

    db.session.commit()


def ensure_person_partner_verein_column() -> None:
    """
    Fügt person.is_partner_verein hinzu (idempotent), falls nicht vorhanden.
    """
    if not _table_exists("person"):
        return

    if not _column_exists("person", "is_partner_verein"):
        db.session.execute(
            text("ALTER TABLE person ADD COLUMN is_partner_verein INTEGER NOT NULL DEFAULT 0")
        )
        db.session.commit()


def ensure_person_original_name_column() -> None:
    """
    Fügt person.original_name hinzu (idempotent), falls nicht vorhanden.
    """
    if not _table_exists("person"):
        return

    if not _column_exists("person", "original_name"):
        db.session.execute(
            text("ALTER TABLE person ADD COLUMN original_name VARCHAR(120)")
        )
        db.session.commit()


def ensure_person_tandemmaster_column() -> None:
    """
    Fuegt person.is_tandemmaster hinzu (idempotent), falls nicht vorhanden.
    """
    if not _table_exists("person"):
        return

    if not _column_exists("person", "is_tandemmaster"):
        db.session.execute(
            text("ALTER TABLE person ADD COLUMN is_tandemmaster INTEGER NOT NULL DEFAULT 0")
        )
        db.session.commit()


def ensure_person_student_column() -> None:
    """
    Fuegt person.is_student hinzu (idempotent), falls nicht vorhanden.
    """
    if not _table_exists("person"):
        return

    if not _column_exists("person", "is_student"):
        db.session.execute(
            text("ALTER TABLE person ADD COLUMN is_student INTEGER NOT NULL DEFAULT 0")
        )
        db.session.commit()


def ensure_partner_verein_status_and_prices() -> None:
    """
    Ergänzt Partner-Verein-Status und kopiert initial Preise/Orga-Regeln
    aus den Verein-Varianten (idempotent).
    """
    if not _table_exists("status_definitions"):
        return

    # Aktive Statusdefinitionen ergänzen/angleichen
    db.session.execute(
        text(
            """
            INSERT INTO status_definitions (code, label, beschreibung, sort_order, vat_rate, valid_from, is_active)
            SELECT 'Partner-Verein',
                   'Partner-Verein',
                   'Partnerverein mit eigenem Status (Preis wie Verein, separat editierbar)',
                   15,
                   COALESCE(
                     (SELECT vat_rate FROM status_definitions WHERE code='Verein' AND is_active=1 ORDER BY valid_from DESC LIMIT 1),
                     0
                   ),
                   CURRENT_TIMESTAMP,
                   1
            WHERE NOT EXISTS (
                SELECT 1 FROM status_definitions WHERE code='Partner-Verein' AND is_active=1
            )
            """
        )
    )
    db.session.execute(
        text(
            """
            UPDATE status_definitions
               SET label = 'Partner-Verein',
                   sort_order = 15
             WHERE code = 'Partner-Verein'
               AND is_active = 1
            """
        )
    )

    db.session.execute(
        text(
            """
            INSERT INTO status_definitions (code, label, beschreibung, sort_order, vat_rate, valid_from, is_active)
            SELECT 'Auffüller Partner-Verein',
                   'Auffüller eines Tandemloads - Partner Verein',
                   'Auffüllerstatus für Partnerverein (separat auswertbar)',
                   31,
                   COALESCE(
                     (SELECT vat_rate FROM status_definitions WHERE code='Auffüller Verein' AND is_active=1 ORDER BY valid_from DESC LIMIT 1),
                     (SELECT vat_rate FROM status_definitions WHERE code='Verein' AND is_active=1 ORDER BY valid_from DESC LIMIT 1),
                     0
                   ),
                   CURRENT_TIMESTAMP,
                   1
            WHERE NOT EXISTS (
                SELECT 1 FROM status_definitions WHERE code='Auffüller Partner-Verein' AND is_active=1
            )
            """
        )
    )
    db.session.execute(
        text(
            """
            UPDATE status_definitions
               SET label = 'Auffüller eines Tandemloads - Partner Verein',
                   sort_order = 31
             WHERE code = 'Auffüller Partner-Verein'
               AND is_active = 1
            """
        )
    )

    if _table_exists("billing_price"):
        if _column_exists("billing_price", "flugplatz_id"):
            db.session.execute(
                text(
                    """
                    INSERT INTO billing_price (flugplatz_id, period_id, status_code, height_m, price_eur)
                    SELECT b.flugplatz_id, b.period_id, 'Partner-Verein', b.height_m, b.price_eur
                      FROM billing_price b
                     WHERE b.status_code = 'Verein'
                       AND NOT EXISTS (
                           SELECT 1
                             FROM billing_price x
                            WHERE x.flugplatz_id = b.flugplatz_id
                              AND x.period_id = b.period_id
                              AND x.height_m = b.height_m
                              AND x.status_code = 'Partner-Verein'
                       )
                    """
                )
            )
            db.session.execute(
                text(
                    """
                    INSERT INTO billing_price (flugplatz_id, period_id, status_code, height_m, price_eur)
                    SELECT b.flugplatz_id, b.period_id, 'Auffüller Partner-Verein', b.height_m, b.price_eur
                      FROM billing_price b
                     WHERE b.status_code = 'Auffüller Verein'
                       AND NOT EXISTS (
                           SELECT 1
                             FROM billing_price x
                            WHERE x.flugplatz_id = b.flugplatz_id
                              AND x.period_id = b.period_id
                              AND x.height_m = b.height_m
                              AND x.status_code = 'Auffüller Partner-Verein'
                       )
                    """
                )
            )
        else:
            db.session.execute(
                text(
                    """
                    INSERT INTO billing_price (period_id, status_code, height_m, price_eur)
                    SELECT b.period_id, 'Partner-Verein', b.height_m, b.price_eur
                      FROM billing_price b
                     WHERE b.status_code = 'Verein'
                       AND NOT EXISTS (
                           SELECT 1
                             FROM billing_price x
                            WHERE x.period_id = b.period_id
                              AND x.height_m = b.height_m
                              AND x.status_code = 'Partner-Verein'
                       )
                    """
                )
            )
            db.session.execute(
                text(
                    """
                    INSERT INTO billing_price (period_id, status_code, height_m, price_eur)
                    SELECT b.period_id, 'Auffüller Partner-Verein', b.height_m, b.price_eur
                      FROM billing_price b
                     WHERE b.status_code = 'Auffüller Verein'
                       AND NOT EXISTS (
                           SELECT 1
                             FROM billing_price x
                            WHERE x.period_id = b.period_id
                              AND x.height_m = b.height_m
                              AND x.status_code = 'Auffüller Partner-Verein'
                       )
                    """
                )
            )

    if _table_exists("billing_orga_rule"):
        if _column_exists("billing_orga_rule", "flugplatz_id"):
            db.session.execute(
                text(
                    """
                    INSERT INTO billing_orga_rule (flugplatz_id, period_id, status_code, apply_orga)
                    SELECT r.flugplatz_id, r.period_id, 'Partner-Verein', r.apply_orga
                      FROM billing_orga_rule r
                     WHERE r.status_code = 'Verein'
                       AND NOT EXISTS (
                           SELECT 1
                             FROM billing_orga_rule x
                            WHERE x.flugplatz_id = r.flugplatz_id
                              AND x.period_id = r.period_id
                              AND x.status_code = 'Partner-Verein'
                       )
                    """
                )
            )
            db.session.execute(
                text(
                    """
                    INSERT INTO billing_orga_rule (flugplatz_id, period_id, status_code, apply_orga)
                    SELECT r.flugplatz_id, r.period_id, 'Auffüller Partner-Verein', r.apply_orga
                      FROM billing_orga_rule r
                     WHERE r.status_code = 'Auffüller Verein'
                       AND NOT EXISTS (
                           SELECT 1
                             FROM billing_orga_rule x
                            WHERE x.flugplatz_id = r.flugplatz_id
                              AND x.period_id = r.period_id
                              AND x.status_code = 'Auffüller Partner-Verein'
                       )
                    """
                )
            )
        else:
            db.session.execute(
                text(
                    """
                    INSERT INTO billing_orga_rule (period_id, status_code, apply_orga)
                    SELECT r.period_id, 'Partner-Verein', r.apply_orga
                      FROM billing_orga_rule r
                     WHERE r.status_code = 'Verein'
                       AND NOT EXISTS (
                           SELECT 1
                             FROM billing_orga_rule x
                            WHERE x.period_id = r.period_id
                              AND x.status_code = 'Partner-Verein'
                       )
                    """
                )
            )
            db.session.execute(
                text(
                    """
                    INSERT INTO billing_orga_rule (period_id, status_code, apply_orga)
                    SELECT r.period_id, 'Auffüller Partner-Verein', r.apply_orga
                      FROM billing_orga_rule r
                     WHERE r.status_code = 'Auffüller Verein'
                       AND NOT EXISTS (
                           SELECT 1
                             FROM billing_orga_rule x
                            WHERE x.period_id = r.period_id
                              AND x.status_code = 'Auffüller Partner-Verein'
                       )
                    """
                )
            )

    db.session.commit()


def ensure_billing_config_partner_canopy_rent_columns() -> None:
    """
    Fügt eigene Partner-Verein-Schirmmiete-Felder in billing_config hinzu
    und initialisiert sie aus den Vereinswerten (idempotent).
    """
    if not _table_exists("billing_config"):
        return

    changed = False

    if not _column_exists("billing_config", "canopy_rent_partner_member_eur"):
        db.session.execute(
            text(
                "ALTER TABLE billing_config "
                "ADD COLUMN canopy_rent_partner_member_eur NUMERIC(10,2) NOT NULL DEFAULT 15"
            )
        )
        changed = True

    if not _column_exists("billing_config", "canopy_rent_partner_member_max_count"):
        db.session.execute(
            text(
                "ALTER TABLE billing_config "
                "ADD COLUMN canopy_rent_partner_member_max_count INTEGER NOT NULL DEFAULT 3"
            )
        )
        changed = True

    if not _column_exists("billing_config", "canopy_rent_partner_member_vat_rate"):
        db.session.execute(
            text(
                "ALTER TABLE billing_config "
                "ADD COLUMN canopy_rent_partner_member_vat_rate NUMERIC(5,2) NOT NULL DEFAULT 7"
            )
        )
        changed = True

    if changed:
        db.session.execute(
            text(
                """
                UPDATE billing_config
                   SET canopy_rent_partner_member_eur = COALESCE(canopy_rent_member_eur, canopy_rent_partner_member_eur),
                       canopy_rent_partner_member_max_count = COALESCE(canopy_rent_member_max_count, canopy_rent_partner_member_max_count),
                       canopy_rent_partner_member_vat_rate = COALESCE(canopy_rent_member_vat_rate, canopy_rent_partner_member_vat_rate)
                """
            )
        )
        db.session.commit()


def ensure_billing_config_waiver_text_columns() -> None:
    """
    Fuegt fehlende Waiver-Text-Spalten in billing_config hinzu (idempotent).
    """
    if not _table_exists("billing_config"):
        return

    changed = False

    if not _column_exists("billing_config", "waiver_text_skydiver"):
        db.session.execute(
            text("ALTER TABLE billing_config ADD COLUMN waiver_text_skydiver TEXT")
        )
        changed = True

    if not _column_exists("billing_config", "waiver_text_tandem"):
        db.session.execute(
            text("ALTER TABLE billing_config ADD COLUMN waiver_text_tandem TEXT")
        )
        changed = True

    if changed:
        db.session.commit()


def ensure_billing_config_manual_invoice_mail_text_column() -> None:
    """
    Fuegt den E-Mail-Text fuer manuelle Rechnungen in billing_config hinzu (idempotent).
    """
    if not _table_exists("billing_config"):
        return

    changed = False

    if not _column_exists("billing_config", "mail_body_template_manual"):
        db.session.execute(
            text("ALTER TABLE billing_config ADD COLUMN mail_body_template_manual TEXT")
        )
        changed = True

    db.session.execute(
        text(
            "UPDATE billing_config "
            "   SET mail_body_template_manual = COALESCE(NULLIF(TRIM(mail_body_template_manual), ''), :default_text) "
            " WHERE mail_body_template_manual IS NULL OR TRIM(mail_body_template_manual) = ''"
        ),
        {
            "default_text": (
                "Liebe/r {first_name} {last_name},\n\n"
                "in der Anlage erhältst Du Deine Rechnung für {manual_title}.\n"
                "Sollte die Rechnung noch nicht bezahlt sein, bitten wir um Begleichung bis zwei Tage nach Erhalt der Rechnung.\n\n"
                "Bitte antworte nicht auf diese E-Mail, da sie automatisiert generiert wurde. Ggf. Kontakt siehe unten.\n\n"
                "Viele Grüße aus Dessau"
            )
        },
    )

    if changed:
        db.session.commit()


def ensure_invoice_email_audit_columns() -> None:
    """
    Fuegt fehlende E-Mail-Audit-Spalten in invoice hinzu (idempotent).
    """
    if not _table_exists("invoice"):
        return

    changed = False

    if not _column_exists("invoice", "email_last_attempt_at"):
        try:
            db.session.execute(
                text("ALTER TABLE invoice ADD COLUMN email_last_attempt_at DATETIME")
            )
            changed = True
        except OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise

    if not _column_exists("invoice", "email_last_error"):
        try:
            db.session.execute(
                text("ALTER TABLE invoice ADD COLUMN email_last_error VARCHAR(500)")
            )
            changed = True
        except OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise

    if not _column_exists("invoice", "email_last_recipient"):
        try:
            db.session.execute(
                text("ALTER TABLE invoice ADD COLUMN email_last_recipient VARCHAR(255)")
            )
            changed = True
        except OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise

    if not _column_exists("invoice", "email_last_message_id"):
        try:
            db.session.execute(
                text("ALTER TABLE invoice ADD COLUMN email_last_message_id VARCHAR(255)")
            )
            changed = True
        except OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise

    if not _column_exists("invoice", "email_delivery_confirmed_at"):
        try:
            db.session.execute(
                text("ALTER TABLE invoice ADD COLUMN email_delivery_confirmed_at DATETIME")
            )
            changed = True
        except OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise

    if not _column_exists("invoice", "email_delivery_confirmed_by"):
        try:
            db.session.execute(
                text("ALTER TABLE invoice ADD COLUMN email_delivery_confirmed_by VARCHAR(100)")
            )
            changed = True
        except OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise

    if changed:
        db.session.commit()


def ensure_person_newsletter_columns() -> None:
    """Fügt newsletter_opt_out + newsletter_unsubscribe_token zu person hinzu."""
    if not _table_exists("person"):
        return
    if not _column_exists("person", "newsletter_opt_out"):
        db.session.execute(
            text("ALTER TABLE person ADD COLUMN newsletter_opt_out BOOLEAN NOT NULL DEFAULT 0")
        )
    if not _column_exists("person", "newsletter_unsubscribe_token"):
        db.session.execute(
            text("ALTER TABLE person ADD COLUMN newsletter_unsubscribe_token VARCHAR(64)")
        )
        db.session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS "
                "ix_person_newsletter_unsubscribe_token "
                "ON person (newsletter_unsubscribe_token)"
            )
        )
    db.session.commit()


def ensure_email_config_table() -> None:
    """Erstellt email_config Tabelle, falls nicht vorhanden."""
    if _table_exists("email_config"):
        return
    db.session.execute(text("""
        CREATE TABLE email_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name VARCHAR(255),
            logo_filename VARCHAR(200),
            street VARCHAR(255),
            zip_code VARCHAR(10),
            city VARCHAR(50),
            website VARCHAR(255),
            email VARCHAR(100),
            tax_number VARCHAR(50),
            instagram_url VARCHAR(255),
            facebook_url VARCHAR(255),
            mail_sender_address VARCHAR(255),
            mail_sender_name VARCHAR(255),
            mail_subject_template VARCHAR(500),
            mail_body_template TEXT,
            smtp_server VARCHAR(255),
            smtp_fallback_host VARCHAR(255),
            smtp_port INTEGER,
            smtp_use_tls BOOLEAN NOT NULL DEFAULT 1,
            smtp_use_ssl BOOLEAN NOT NULL DEFAULT 0,
            smtp_username VARCHAR(255),
            smtp_password VARCHAR(255),
            qr_instagram_filename VARCHAR(200),
            qr_facebook_filename VARCHAR(200),
            qr_website_filename VARCHAR(200)
        )
    """))
    db.session.commit()


def ensure_email_send_log_table() -> None:
    """Erstellt email_send_log Tabelle, falls nicht vorhanden."""
    if _table_exists("email_send_log"):
        return
    db.session.execute(text("""
        CREATE TABLE email_send_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            subject VARCHAR(500),
            body_preview TEXT,
            recipient_count INTEGER DEFAULT 0,
            recipient_list TEXT,
            mail_type VARCHAR(20) DEFAULT 'email',
            status VARCHAR(20) DEFAULT 'ok',
            error_detail TEXT
        )
    """))
    db.session.commit()


def run_startup_migrations() -> None:
    """
    Sammelpunkt für alle Startup-Migrationen.
    Diese Funktion darf bei jedem Start gefahrlos laufen.
    """
    ensure_load_pricing_model_id_column()
    ensure_person_partner_verein_column()
    ensure_person_tandemmaster_column()
    ensure_person_student_column()
    ensure_person_original_name_column()
    ensure_billing_config_waiver_text_columns()
    ensure_billing_config_manual_invoice_mail_text_column()
    ensure_invoice_email_audit_columns()
    ensure_partner_verein_status_and_prices()
    ensure_billing_config_partner_canopy_rent_columns()
    ensure_person_newsletter_columns()
    ensure_email_config_table()
    ensure_email_send_log_table()