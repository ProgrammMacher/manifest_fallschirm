"""
Migration: seq_number (fortlaufende Rechnungsnummer) zur Invoice-Tabelle hinzufügen
Datum: 2026-05-04

Revision ID: 20260504_add_seq_number_to_invoice
Revises: 20260503_add_aff_status_to_person_and_pricing
Create Date: 2026-05-04

Backfill: bestehende Rechnungen erhalten seq_number = id, um die bisherige
Nummerierung zu erhalten.
"""

from alembic import op
import sqlalchemy as sa

revision = "20260504_add_seq_number_to_invoice"
down_revision = "20260503_add_aff_status_to_person_and_pricing"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    invoice_cols = {c["name"] for c in inspector.get_columns("invoice")}

    if 'seq_number' not in invoice_cols:
        op.add_column('invoice', sa.Column('seq_number', sa.Integer(), nullable=True))

    # Einmaliger Backfill: seq_number = id für alle vorhandenen Rechnungen
    op.execute("UPDATE invoice SET seq_number = id WHERE seq_number IS NULL")

    idx_names = {i["name"] for i in inspector.get_indexes("invoice")}
    if 'ix_invoice_seq_number' not in idx_names:
        # Unique-Index anlegen (nach Backfill)
        op.create_index('ix_invoice_seq_number', 'invoice', ['seq_number'], unique=True)


def downgrade():
    op.drop_index('ix_invoice_seq_number', table_name='invoice')
    op.drop_column('invoice', 'seq_number')
