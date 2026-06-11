"""
Migration: Einheit für manuelle Rechnungspositionen hinzufügen
Datum: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260602_add_manual_unit_to_invoice_item"
down_revision = "20260602_add_manual_invoice_support"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("invoice_item")}

    if "manual_unit" not in cols:
        op.add_column("invoice_item", sa.Column("manual_unit", sa.String(length=50), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("invoice_item")}

    if "manual_unit" in cols:
        op.drop_column("invoice_item", "manual_unit")
