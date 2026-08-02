"""
Migration: Add KU credit payout basis fields to billing_price and invoice_item.
Date: 2026-08-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260802_add_ku_credit_payout_fields"
down_revision = "20260718_add_sepa_export_infrastructure"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return {c["name"] for c in insp.get_columns(table_name)}


def upgrade() -> None:
    billing_price_cols = _columns("billing_price")
    if "ku_credit_payout_basis" not in billing_price_cols:
        op.add_column(
            "billing_price",
            sa.Column(
                "ku_credit_payout_basis",
                sa.String(length=10),
                nullable=False,
                server_default="gross",
            ),
        )

    invoice_item_cols = _columns("invoice_item")
    if "price_source_eur" not in invoice_item_cols:
        op.add_column(
            "invoice_item",
            sa.Column("price_source_eur", sa.Numeric(10, 2), nullable=True),
        )
    if "price_source_vat_rate" not in invoice_item_cols:
        op.add_column(
            "invoice_item",
            sa.Column("price_source_vat_rate", sa.Numeric(5, 2), nullable=True),
        )
    if "ku_credit_payout_basis" not in invoice_item_cols:
        op.add_column(
            "invoice_item",
            sa.Column("ku_credit_payout_basis", sa.String(length=10), nullable=True),
        )
    if "ku_credit_payout_amount" not in invoice_item_cols:
        op.add_column(
            "invoice_item",
            sa.Column("ku_credit_payout_amount", sa.Numeric(10, 2), nullable=True),
        )


def downgrade() -> None:
    invoice_item_cols = _columns("invoice_item")
    if "ku_credit_payout_amount" in invoice_item_cols:
        op.drop_column("invoice_item", "ku_credit_payout_amount")
    if "ku_credit_payout_basis" in invoice_item_cols:
        op.drop_column("invoice_item", "ku_credit_payout_basis")
    if "price_source_vat_rate" in invoice_item_cols:
        op.drop_column("invoice_item", "price_source_vat_rate")
    if "price_source_eur" in invoice_item_cols:
        op.drop_column("invoice_item", "price_source_eur")

    billing_price_cols = _columns("billing_price")
    if "ku_credit_payout_basis" in billing_price_cols:
        op.drop_column("billing_price", "ku_credit_payout_basis")
