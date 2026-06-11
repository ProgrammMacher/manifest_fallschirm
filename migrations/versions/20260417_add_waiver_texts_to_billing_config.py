"""Add waiver text fields to billing_config

Revision ID: 20260417_add_waiver_texts_to_billing_config
Revises: 20260416_add_partner_verein_to_person
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260417_add_waiver_texts_to_billing_config"
down_revision = "20260416_add_partner_verein_to_person"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in cols


def upgrade() -> None:
    if not _column_exists("billing_config", "waiver_text_skydiver"):
        op.add_column(
            "billing_config",
            sa.Column("waiver_text_skydiver", sa.Text(), nullable=True),
        )

    if not _column_exists("billing_config", "waiver_text_tandem"):
        op.add_column(
            "billing_config",
            sa.Column("waiver_text_tandem", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    if _column_exists("billing_config", "waiver_text_tandem"):
        with op.batch_alter_table("billing_config") as batch_op:
            batch_op.drop_column("waiver_text_tandem")

    if _column_exists("billing_config", "waiver_text_skydiver"):
        with op.batch_alter_table("billing_config") as batch_op:
            batch_op.drop_column("waiver_text_skydiver")
