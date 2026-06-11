"""Add email audit fields to invoice

- email_sent_at: DateTime when email was successfully sent
- email_sent_ok: Boolean flag for successful send

This enables tracking of invoice email sends with timestamps and prevents accidental resends
(for non-admin users).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260410_add_email_audit_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('invoice', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email_sent_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('email_sent_ok', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('invoice', schema=None) as batch_op:
        batch_op.drop_column('email_sent_ok')
        batch_op.drop_column('email_sent_at')
