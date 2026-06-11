"""Add is_partner_verein to person

Revision ID: 20260416_add_partner_verein_to_person
Revises: 20260411_add_pdf_bytes_to_invoice
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260416_add_partner_verein_to_person"
down_revision = "20260411_add_pdf_bytes_to_invoice"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in cols


def upgrade() -> None:
    if not _column_exists("person", "is_partner_verein"):
        op.add_column(
            "person",
            sa.Column("is_partner_verein", sa.Boolean(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    if _column_exists("person", "is_partner_verein"):
        with op.batch_alter_table("person") as batch_op:
            batch_op.drop_column("is_partner_verein")
