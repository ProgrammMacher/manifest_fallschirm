"""
Migration: AFF-Lehrer Kleinunternehmer-Felder fuer Abrechnung
Datum: 2026-08-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260803_add_aff_teacher_kleinunternehmer_fields"
down_revision = "20260802_add_ku_credit_payout_fields"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return {c["name"] for c in insp.get_columns(table_name)}


def upgrade() -> None:
    person_cols = _columns("person")
    if "is_aff_teacher_kleinunternehmer" not in person_cols:
        op.add_column(
            "person",
            sa.Column(
                "is_aff_teacher_kleinunternehmer",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            ),
        )

    invoice_cols = _columns("invoice")
    if "is_aff_teacher_kleinunternehmer" not in invoice_cols:
        op.add_column(
            "invoice",
            sa.Column(
                "is_aff_teacher_kleinunternehmer",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            ),
        )

    idx_names = {ix["name"] for ix in sa.inspect(op.get_bind()).get_indexes("invoice")}
    if "ix_invoice_is_aff_teacher_kleinunternehmer" not in idx_names:
        op.create_index(
            "ix_invoice_is_aff_teacher_kleinunternehmer",
            "invoice",
            ["is_aff_teacher_kleinunternehmer"],
            unique=False,
        )


def downgrade() -> None:
    invoice_cols = _columns("invoice")
    if "is_aff_teacher_kleinunternehmer" in invoice_cols:
        idx_names = {ix["name"] for ix in sa.inspect(op.get_bind()).get_indexes("invoice")}
        if "ix_invoice_is_aff_teacher_kleinunternehmer" in idx_names:
            op.drop_index("ix_invoice_is_aff_teacher_kleinunternehmer", table_name="invoice")
        op.drop_column("invoice", "is_aff_teacher_kleinunternehmer")

    person_cols = _columns("person")
    if "is_aff_teacher_kleinunternehmer" in person_cols:
        op.drop_column("person", "is_aff_teacher_kleinunternehmer")
