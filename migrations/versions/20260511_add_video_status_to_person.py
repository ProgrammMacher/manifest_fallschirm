"""
Migration: Video-Statusfeld in Person ergänzen
Datum: 2026-05-11

Revision ID: 20260511_add_video_status_to_person
Revises: 20260504_add_seq_number_to_invoice
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa

revision = "20260511_add_video_status_to_person"
down_revision = "20260504_add_seq_number_to_invoice"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    person_cols = {c["name"] for c in insp.get_columns("person")}

    if "is_video" not in person_cols:
        op.add_column(
            "person",
            sa.Column("is_video", sa.Boolean(), nullable=False, server_default="0"),
        )


def downgrade():
    op.drop_column("person", "is_video")
