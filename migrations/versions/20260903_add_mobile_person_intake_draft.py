"""Add mobile person intake draft queue.

Revision ID: 20260903_add_mobile_person_intake_draft
Revises: 20260803_add_aff_teacher_kleinunternehmer_fields
"""

from alembic import op
import sqlalchemy as sa


revision = "20260903_add_mobile_person_intake_draft"
down_revision = "20260803_add_aff_teacher_kleinunternehmer_fields"
branch_labels = None
depends_on = None


TABLE_NAME = "mobile_person_intake_draft"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if TABLE_NAME in inspector.get_table_names():
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("submission_token_hash", sa.String(length=64), nullable=False),
        sa.Column("submission_idempotency_key_hash", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=100), nullable=True),
        sa.Column("person_id", sa.Integer(), sa.ForeignKey("person.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("first_name", sa.String(length=50), nullable=True),
        sa.Column("last_name", sa.String(length=50), nullable=True),
        sa.Column("birthdate", sa.Date(), nullable=True),
        sa.Column("weight_kg", sa.Integer(), nullable=True),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("street_and_number", sa.String(length=120), nullable=True),
        sa.Column("zip_code", sa.String(length=10), nullable=True),
        sa.Column("city", sa.String(length=50), nullable=True),
        sa.Column("emergency_name", sa.String(length=100), nullable=True),
        sa.Column("emergency_relation", sa.String(length=50), nullable=True),
        sa.Column("emergency_phone", sa.String(length=30), nullable=True),
        sa.Column("license_number", sa.String(length=50), nullable=True),
        sa.Column("license_type", sa.String(length=50), nullable=True),
        sa.Column("license_valid_until", sa.Date(), nullable=True),
        sa.Column("insurance_provider", sa.String(length=100), nullable=True),
        sa.Column("insurance_number", sa.String(length=100), nullable=True),
        sa.Column("is_member", sa.Boolean(), nullable=True),
        sa.Column("is_partner_verein", sa.Boolean(), nullable=True),
        sa.CheckConstraint("mode IN ('tandem_guest', 'jumper')", name="ck_mobile_person_intake_draft_mode"),
        sa.CheckConstraint("status IN ('open', 'submitted', 'accepted', 'discarded', 'expired')", name="ck_mobile_person_intake_draft_status"),
        sa.UniqueConstraint("submission_token_hash", name="uq_mobile_person_intake_draft_submission_token_hash"),
        sa.UniqueConstraint("submission_idempotency_key_hash", name="uq_mobile_person_intake_draft_idempotency_key_hash"),
    )
    op.create_index("ix_mobile_person_intake_draft_mode", TABLE_NAME, ["mode"])
    op.create_index("ix_mobile_person_intake_draft_status", TABLE_NAME, ["status"])
    op.create_index("ix_mobile_person_intake_draft_expires_at", TABLE_NAME, ["expires_at"])
    op.create_index("ix_mobile_person_intake_draft_created_at", TABLE_NAME, ["created_at"])
    op.create_index("ix_mobile_person_intake_draft_submitted_at", TABLE_NAME, ["submitted_at"])
    op.create_index("ix_mobile_person_intake_draft_person_id", TABLE_NAME, ["person_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if TABLE_NAME in inspector.get_table_names():
        op.drop_table(TABLE_NAME)