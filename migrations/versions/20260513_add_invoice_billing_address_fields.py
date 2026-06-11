"""
Migration: Abweichende Rechnungsanschrift-Felder zur Invoice-Tabelle hinzufügen
Datum: 2026-05-13

Revision ID: 20260513_add_invoice_billing_address_fields
Revises: 20260511_add_video_status_to_person
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260513_add_invoice_billing_address_fields"
down_revision = "20260511_add_video_status_to_person"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("invoice")}

    if "billing_address_name" not in cols:
        op.add_column("invoice", sa.Column("billing_address_name", sa.String(length=200), nullable=True))
    if "billing_address_street" not in cols:
        op.add_column("invoice", sa.Column("billing_address_street", sa.String(length=200), nullable=True))
    if "billing_address_zip" not in cols:
        op.add_column("invoice", sa.Column("billing_address_zip", sa.String(length=20), nullable=True))
    if "billing_address_city" not in cols:
        op.add_column("invoice", sa.Column("billing_address_city", sa.String(length=100), nullable=True))
    if "billing_address_email" not in cols:
        op.add_column("invoice", sa.Column("billing_address_email", sa.String(length=200), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("invoice")}

    if "billing_address_email" in cols:
        op.drop_column("invoice", "billing_address_email")
    if "billing_address_city" in cols:
        op.drop_column("invoice", "billing_address_city")
    if "billing_address_zip" in cols:
        op.drop_column("invoice", "billing_address_zip")
    if "billing_address_street" in cols:
        op.drop_column("invoice", "billing_address_street")
    if "billing_address_name" in cols:
        op.drop_column("invoice", "billing_address_name")
