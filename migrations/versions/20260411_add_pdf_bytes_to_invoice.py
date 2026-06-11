"""Add pdf_bytes column to invoice

Revision ID: 20260411_add_pdf_bytes_to_invoice
Revises: ad0eea18cea1
Create Date: 2026-04-11

- invoice: pdf_bytes (LargeBinary)
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260411_add_pdf_bytes_to_invoice"
down_revision = "ad0eea18cea1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("invoice")}
    if "pdf_bytes" not in cols:
        op.add_column(
            "invoice",
            sa.Column("pdf_bytes", sa.LargeBinary(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("invoice")}
    if "pdf_bytes" in cols:
        op.drop_column("invoice", "pdf_bytes")