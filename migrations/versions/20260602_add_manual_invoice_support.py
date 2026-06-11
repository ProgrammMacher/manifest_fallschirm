"""
Migration: Manuelle Rechnungen ermöglichen
Datum: 2026-06-02

- invoice.service_date hinzufügen
- invoice_item.load_entry_id nullable machen
- invoice_item um manuelle Positionsfelder erweitern
"""

from alembic import op
import sqlalchemy as sa


revision = "20260602_add_manual_invoice_support"
down_revision = "20260525_add_invoice_prepaid_voucher_amount"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return {c["name"] for c in insp.get_columns(table_name)}


def upgrade() -> None:
    invoice_cols = _columns("invoice")
    if "service_date" not in invoice_cols:
        op.add_column("invoice", sa.Column("service_date", sa.Date(), nullable=True))

    item_cols = _columns("invoice_item")

    if "item_source" not in item_cols:
        op.add_column(
            "invoice_item",
            sa.Column("item_source", sa.String(length=20), nullable=False, server_default="load"),
        )
    if "quantity" not in item_cols:
        op.add_column(
            "invoice_item",
            sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="1"),
        )
    if "unit_price_gross" not in item_cols:
        op.add_column(
            "invoice_item",
            sa.Column("unit_price_gross", sa.Numeric(10, 2), nullable=False, server_default="0"),
        )
    if "manual_position_code" not in item_cols:
        op.add_column(
            "invoice_item",
            sa.Column("manual_position_code", sa.String(length=50), nullable=True),
        )

    with op.batch_alter_table("invoice_item") as batch_op:
        batch_op.alter_column("load_entry_id", existing_type=sa.Integer(), nullable=True)

    op.create_index(
        "ix_invoice_item_item_source",
        "invoice_item",
        ["item_source"],
        unique=False,
    )

    op.execute("UPDATE invoice_item SET item_source = 'load' WHERE item_source IS NULL")
    op.execute("UPDATE invoice_item SET quantity = 1 WHERE quantity IS NULL")
    op.execute("UPDATE invoice_item SET unit_price_gross = amount WHERE unit_price_gross IS NULL")


def downgrade() -> None:
    item_cols = _columns("invoice_item")

    with op.batch_alter_table("invoice_item") as batch_op:
        batch_op.alter_column("load_entry_id", existing_type=sa.Integer(), nullable=False)

    index_names = {ix["name"] for ix in sa.inspect(op.get_bind()).get_indexes("invoice_item")}
    if "ix_invoice_item_item_source" in index_names:
        op.drop_index("ix_invoice_item_item_source", table_name="invoice_item")

    if "manual_position_code" in item_cols:
        op.drop_column("invoice_item", "manual_position_code")
    if "unit_price_gross" in item_cols:
        op.drop_column("invoice_item", "unit_price_gross")
    if "quantity" in item_cols:
        op.drop_column("invoice_item", "quantity")
    if "item_source" in item_cols:
        op.drop_column("invoice_item", "item_source")

    invoice_cols = _columns("invoice")
    if "service_date" in invoice_cols:
        op.drop_column("invoice", "service_date")
