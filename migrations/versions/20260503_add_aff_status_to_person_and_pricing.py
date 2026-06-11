"""
Migration: Neue Felder für AFF-Lehrer und Schüler-AFF in Person, neue Status für Preismatrix
Datum: 2026-05-03

Revision ID: 20260503_add_aff_status_to_person_and_pricing
Revises: 20260417_add_waiver_texts_to_billing_config
Create Date: 2026-05-03
"""

from alembic import op
import sqlalchemy as sa

revision = "20260503_add_aff_status_to_person_and_pricing"
down_revision = "20260417_add_waiver_texts_to_billing_config"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    person_cols = {c["name"] for c in insp.get_columns("person")}

    # --- Personenstatus ---
    if 'is_aff_teacher' not in person_cols:
        op.add_column('person', sa.Column('is_aff_teacher', sa.Boolean(), nullable=False, server_default='0'))
    if 'is_aff_student' not in person_cols:
        op.add_column('person', sa.Column('is_aff_student', sa.Boolean(), nullable=False, server_default='0'))

    # --- Preismatrix-Status (StatusDefinition) ---
    # 1. AFF-Lehrer
    op.execute("""
        INSERT INTO status_definitions (code, label, beschreibung, sort_order, preis_1500, preis_3000, preis_4000, vat_rate, is_active, valid_from)
        SELECT 'AFF-LEHRER', 'AFF-Lehrer', 'AFF-Lehrer (Instructor)', 41, 0, 0, 0, 19.00, 1, CURRENT_TIMESTAMP
        WHERE NOT EXISTS (SELECT 1 FROM status_definitions WHERE code = 'AFF-LEHRER')
    """)
    # 2. Schüler-AFF-2-Lehrer
    op.execute("""
        INSERT INTO status_definitions (code, label, beschreibung, sort_order, preis_1500, preis_3000, preis_4000, vat_rate, is_active, valid_from)
        SELECT 'SCHUELER-AFF-2', 'Schüler-AFF-2-Lehrer', 'AFF-Schüler mit 2 Lehrern', 61, 0, 0, 0, 19.00, 1, CURRENT_TIMESTAMP
        WHERE NOT EXISTS (SELECT 1 FROM status_definitions WHERE code = 'SCHUELER-AFF-2')
    """)
    # 3. Schüler-AFF-1-Lehrer
    op.execute("""
        INSERT INTO status_definitions (code, label, beschreibung, sort_order, preis_1500, preis_3000, preis_4000, vat_rate, is_active, valid_from)
        SELECT 'SCHUELER-AFF-1', 'Schüler-AFF-1-Lehrer', 'AFF-Schüler mit 1 Lehrer', 62, 0, 0, 0, 19.00, 1, CURRENT_TIMESTAMP
        WHERE NOT EXISTS (SELECT 1 FROM status_definitions WHERE code = 'SCHUELER-AFF-1')
    """)

def downgrade():
    op.drop_column('person', 'is_aff_teacher')
    op.drop_column('person', 'is_aff_student')
    op.execute("DELETE FROM status_definitions WHERE code IN ('AFF-LEHRER', 'SCHUELER-AFF-2', 'SCHUELER-AFF-1')")
