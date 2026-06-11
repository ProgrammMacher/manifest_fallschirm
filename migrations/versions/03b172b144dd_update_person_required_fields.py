"""Update required fields for Person model (SQLite compatible)"""

from alembic import op
import sqlalchemy as sa


revision = '03b172b144dd'
down_revision = 'ea2f629c8597'
branch_labels = None
depends_on = None


def upgrade():
    # 1) Neue Tabelle mit korrekten NOT NULL Feldern erstellen
    op.create_table(
        'person_new',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('first_name', sa.String(50), nullable=False),
        sa.Column('last_name', sa.String(50), nullable=False),
        sa.Column('phone', sa.String(30), nullable=False),
        sa.Column('weight_kg', sa.Integer, nullable=False),
        sa.Column('height_cm', sa.Integer),
        sa.Column('birthdate', sa.Date),
        sa.Column('email', sa.String(100), nullable=False),
        sa.Column('street_and_number', sa.String(120)),
        sa.Column('zip_code', sa.String(10)),
        sa.Column('city', sa.String(50)),
        sa.Column('is_member', sa.Boolean, default=False),
        sa.Column('status_key', sa.String(50), nullable=False, default="gast"),
        sa.Column('is_tandem_guest', sa.Boolean, default=False),
        sa.Column('license_number', sa.String(50)),
        sa.Column('insurance_provider', sa.String(100)),
        sa.Column('insurance_number', sa.String(100)),
        sa.Column('license_file', sa.String(255)),
        sa.Column('insurance_file', sa.String(255)),
        sa.Column('emergency_name', sa.String(100), nullable=False),
        sa.Column('emergency_relation', sa.String(50)),
        sa.Column('emergency_phone', sa.String(30), nullable=False),
        sa.Column('emergency_email', sa.String(100)),
        sa.Column('iban', sa.String(34)),
        sa.Column('bic', sa.String(11)),
        sa.Column('account_holder', sa.String(120)),
        sa.Column('comment', sa.Text),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('liability_waiver_date', sa.Date)
    )

    # 2) Daten aus alter Tabelle kopieren
    op.execute("""
        INSERT INTO person_new (
            id, first_name, last_name, phone, weight_kg, height_cm, birthdate,
            email, street_and_number, zip_code, city, is_member, status_key,
            is_tandem_guest, license_number, insurance_provider, insurance_number,
            license_file, insurance_file, emergency_name, emergency_relation,
            emergency_phone, emergency_email, iban, bic, account_holder,
            comment, notes, created_at, liability_waiver_date
        )
        SELECT
            id, first_name, last_name, phone, weight_kg, height_cm, birthdate,
            COALESCE(email, ''),  -- Pflichtfeld
            street_and_number, zip_code, city, is_member, status_key,
            is_tandem_guest, license_number, insurance_provider, insurance_number,
            license_file, insurance_file,
            COALESCE(emergency_name, ''),  -- Pflichtfeld
            emergency_relation,
            COALESCE(emergency_phone, ''), -- Pflichtfeld
            emergency_email, iban, bic, account_holder,
            comment, notes, created_at, liability_waiver_date
        FROM person;
    """)

    # 3) Alte Tabelle löschen
    op.drop_table('person')

    # 4) Neue Tabelle umbenennen
    op.rename_table('person_new', 'person')


def downgrade():
    # Downgrade nicht implementiert (SQLite-kompatible Migration)
    pass
