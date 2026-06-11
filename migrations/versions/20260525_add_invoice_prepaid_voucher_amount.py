"""
Migration: Vorkasse/Gutschein-Teilbetrag zur Invoice hinzufügen
Datum: 2026-05-25

Revision ID: 20260525_add_invoice_prepaid_voucher_amount
Revises: 20260513_add_invoice_billing_address_fields
Create Date: 2026-05-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260525_add_invoice_prepaid_voucher_amount"
down_revision = "20260513_add_invoice_billing_address_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("invoice")}

    if "prepaid_voucher_amount" not in cols:
        op.add_column(
            "invoice",
            sa.Column(
                "prepaid_voucher_amount",
                sa.Numeric(10, 2),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("invoice")}

    if "prepaid_voucher_amount" in cols:
        op.drop_column("invoice", "prepaid_voucher_amount")
