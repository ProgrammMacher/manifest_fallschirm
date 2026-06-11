"""
Migration: Überschrift für manuelle Rechnungen hinzufügen
Datum: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260602_add_manual_title_to_invoice"
down_revision = "20260602_add_manual_unit_to_invoice_item"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("invoice")}

    if "manual_title" not in cols:
        op.add_column(
            "invoice",
            sa.Column(
                "manual_title",
                sa.String(length=120),
                nullable=False,
                server_default="Manuelle Positionen",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("invoice")}

    if "manual_title" in cols:
        op.drop_column("invoice", "manual_title")
