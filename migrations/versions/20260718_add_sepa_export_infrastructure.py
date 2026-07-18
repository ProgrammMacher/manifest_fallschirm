"""SEPA export infrastructure tables

Revision ID: 20260718_add_sepa_export_infrastructure
Revises: 20260718_add_sepa_fields_and_invoice_payment_state
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa


revision = "20260718_add_sepa_export_infrastructure"
down_revision = "20260718_add_sepa_fields_and_invoice_payment_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sepa_export",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("export_code", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("invoice_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="created"),
        sa.Column("xml_version", sa.String(length=30), nullable=False, server_default="infra-v1"),
        sa.Column("selection_scope", sa.String(length=30), nullable=False, server_default="manual"),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("submitted_by", sa.String(length=100), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("executed_by", sa.String(length=100), nullable=True),
        sa.Column("file_deleted_at", sa.DateTime(), nullable=True),
        sa.Column("file_deleted_by", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sepa_export_export_code", "sepa_export", ["export_code"], unique=True)
    op.create_index("ix_sepa_export_created_at", "sepa_export", ["created_at"], unique=False)
    op.create_index("ix_sepa_export_status", "sepa_export", ["status"], unique=False)

    op.create_table(
        "sepa_export_invoice",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("export_id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("invoice_number_snapshot", sa.String(length=50), nullable=False),
        sa.Column("invoice_total_snapshot", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("person_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("iban_snapshot", sa.String(length=34), nullable=True),
        sa.Column("mandate_reference_snapshot", sa.String(length=32), nullable=True),
        sa.Column("payment_method_snapshot", sa.String(length=20), nullable=True),
        sa.Column("payment_state_snapshot", sa.String(length=20), nullable=False),
        sa.Column("load_date_from", sa.Date(), nullable=True),
        sa.Column("load_date_to", sa.Date(), nullable=True),
        sa.Column("load_dates_text", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["export_id"], ["sepa_export.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoice.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("export_id", "invoice_id", name="uq_sepa_export_invoice_export_invoice"),
    )
    op.create_index("ix_sepa_export_invoice_export_id", "sepa_export_invoice", ["export_id"], unique=False)
    op.create_index("ix_sepa_export_invoice_invoice_id", "sepa_export_invoice", ["invoice_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sepa_export_invoice_invoice_id", table_name="sepa_export_invoice")
    op.drop_index("ix_sepa_export_invoice_export_id", table_name="sepa_export_invoice")
    op.drop_table("sepa_export_invoice")

    op.drop_index("ix_sepa_export_status", table_name="sepa_export")
    op.drop_index("ix_sepa_export_created_at", table_name="sepa_export")
    op.drop_index("ix_sepa_export_export_code", table_name="sepa_export")
    op.drop_table("sepa_export")
