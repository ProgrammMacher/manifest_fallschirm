"""add fuel_required to load

Revision ID: 20260504_add_fuel_required_to_load
Revises: 20260504_add_seq_number_to_invoice
Create Date: 2026-05-04
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260504_add_fuel_required_to_load'
down_revision = '20260504_add_seq_number_to_invoice'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {c["name"] for c in inspector.get_columns("load")}

    # Idempotent: Spalte nur hinzufügen, wenn sie noch nicht vorhanden ist.
    if "fuel_required" not in column_names:
        op.add_column(
            'load',
            sa.Column(
                'fuel_required',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('0')
            )
        )

        # Default wieder entfernen (optional sauber)
        op.alter_column(
            'load',
            'fuel_required',
            server_default=None
        )


def downgrade():
    op.drop_column('load', 'fuel_required')