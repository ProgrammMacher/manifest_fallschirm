"""Add teacher fields to Person (robust / SQLite-safe)

Revision ID: 0fbbe3921349
Revises: 0f44ab004d0d
Create Date: (generated originally)
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0fbbe3921349"
down_revision = "0f44ab004d0d"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in cols


def upgrade():
    # --- Add columns only if missing (idempotent for dev DBs created via create_all) ---
    if not _column_exists("person", "is_teacher"):
        op.add_column(
            "person",
            sa.Column("is_teacher", sa.Boolean(), nullable=False, server_default="0"),
        )

    if not _column_exists("person", "teacher_license_expires"):
        op.add_column(
            "person",
            sa.Column("teacher_license_expires", sa.Date(), nullable=True),
        )

    # --- Cleanup from older/failed sqlite table-rebuild patterns ---
    # This must NEVER fail if the table doesn't exist.
    op.execute("DROP TABLE IF EXISTS person_new")


def downgrade():
    # SQLite supports drop-column via batch operations
    with op.batch_alter_table("person") as batch_op:
        if _column_exists("person", "teacher_license_expires"):
            batch_op.drop_column("teacher_license_expires")
        if _column_exists("person", "is_teacher"):
            batch_op.drop_column("is_teacher")

    op.execute("DROP TABLE IF EXISTS person_new")