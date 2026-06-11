"""merge heads before VAT migration

Revision ID: ad0eea18cea1
Revises: 71bde9ba21f0, 9c3a1b2d4e5f
Create Date: 2026-03-17 23:53:06.135133

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ad0eea18cea1'
down_revision = ('71bde9ba21f0', '9c3a1b2d4e5f')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
