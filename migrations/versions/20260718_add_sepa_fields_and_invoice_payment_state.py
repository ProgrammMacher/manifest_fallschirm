"""
Migration: SEPA-Stammdaten und erweiterter Rechnungszahlungsstatus
Datum: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa


revision = "20260718_add_sepa_fields_and_invoice_payment_state"
down_revision = "20260709_add_tandem_kleinunternehmer_fields"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return {c["name"] for c in insp.get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return {ix["name"] for ix in insp.get_indexes(table_name)}


def upgrade() -> None:
    person_cols = _columns("person")

    if "sepa_enabled" not in person_cols:
        op.add_column(
            "person",
            sa.Column("sepa_enabled", sa.Boolean(), nullable=False, server_default="0"),
        )

    if "sepa_mandate_reference" not in person_cols:
        op.add_column(
            "person",
            sa.Column("sepa_mandate_reference", sa.String(length=32), nullable=True),
        )

    if "sepa_mandate_date" not in person_cols:
        op.add_column(
            "person",
            sa.Column("sepa_mandate_date", sa.Date(), nullable=True),
        )

    if "sepa_first_collection_done" not in person_cols:
        op.add_column(
            "person",
            sa.Column("sepa_first_collection_done", sa.Boolean(), nullable=False, server_default="0"),
        )

    person_indexes = _indexes("person")
    if "ix_person_sepa_mandate_reference" not in person_indexes:
        op.create_index(
            "ix_person_sepa_mandate_reference",
            "person",
            ["sepa_mandate_reference"],
            unique=False,
        )

    invoice_cols = _columns("invoice")
    if "payment_state" not in invoice_cols:
        op.add_column(
            "invoice",
            sa.Column("payment_state", sa.String(length=20), nullable=False, server_default="open"),
        )

    invoice_indexes = _indexes("invoice")
    if "ix_invoice_payment_state" not in invoice_indexes:
        op.create_index(
            "ix_invoice_payment_state",
            "invoice",
            ["payment_state"],
            unique=False,
        )

    # Legacy-Daten kompatibel hochziehen
    op.execute(
        """
        UPDATE invoice
           SET payment_state = CASE
               WHEN COALESCE(is_paid, 0) = 1 THEN 'paid'
               WHEN lower(COALESCE(payment_method, '')) = 'sepa' THEN 'sepa_pending'
               ELSE 'open'
           END
         WHERE payment_state IS NULL OR payment_state = '' OR payment_state = 'open'
        """
    )


def downgrade() -> None:
    invoice_cols = _columns("invoice")
    if "payment_state" in invoice_cols:
        invoice_indexes = _indexes("invoice")
        if "ix_invoice_payment_state" in invoice_indexes:
            op.drop_index("ix_invoice_payment_state", table_name="invoice")
        op.drop_column("invoice", "payment_state")

    person_cols = _columns("person")
    person_indexes = _indexes("person")

    if "ix_person_sepa_mandate_reference" in person_indexes:
        op.drop_index("ix_person_sepa_mandate_reference", table_name="person")

    if "sepa_first_collection_done" in person_cols:
        op.drop_column("person", "sepa_first_collection_done")

    if "sepa_mandate_date" in person_cols:
        op.drop_column("person", "sepa_mandate_date")

    if "sepa_mandate_reference" in person_cols:
        op.drop_column("person", "sepa_mandate_reference")

    if "sepa_enabled" in person_cols:
        op.drop_column("person", "sepa_enabled")
