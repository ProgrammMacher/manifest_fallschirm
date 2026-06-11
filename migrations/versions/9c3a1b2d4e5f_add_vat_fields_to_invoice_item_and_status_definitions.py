"""Add VAT fields to invoice_item and status_definitions

Revision ID: 9c3a1b2d4e5f
Revises: 201e783c2508
Create Date: 2026-03-17

- invoice_item: vat_rate, net_amount, vat_amount
- status_definitions: vat_rate
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9c3a1b2d4e5f"
down_revision = "201e783c2508"  # ggf. auf euren aktuellen Head ändern
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ----------------------------
    # invoice_item erweitern
    # ----------------------------
    op.add_column(
        "invoice_item",
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "invoice_item",
        sa.Column("net_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "invoice_item",
        sa.Column("vat_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )

    # Bestehende Rechnungspositionen: net_amount initial = amount (Brutto),
    # vat_rate bleibt 0, vat_amount bleibt 0.
    # So bleiben alte Rechnungen sinnvoll darstellbar, ohne MwSt-Annahmen zu treffen.
    op.execute("UPDATE invoice_item SET net_amount = amount")

    # ----------------------------
    # status_definitions erweitern
    # ----------------------------
    op.add_column(
        "status_definitions",
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False, server_default="0"),
    )
    # Keine automatische Zuordnung in der Migration:
    # MwSt-Sätze werden anschließend über eure UI /pricing gepflegt,
    # passend zu eurer Dessau-Preismatrix.


def downgrade() -> None:
    # Rollback: Spalten wieder entfernen (umgekehrte Reihenfolge)
    op.drop_column("status_definitions", "vat_rate")

    op.drop_column("invoice_item", "vat_amount")
    op.drop_column("invoice_item", "net_amount")
    op.drop_column("invoice_item", "vat_rate")