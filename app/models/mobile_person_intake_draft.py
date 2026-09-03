from datetime import datetime

from app import db


MOBILE_PERSON_INTAKE_MODE_TANDEM_GUEST = "tandem_guest"
MOBILE_PERSON_INTAKE_MODE_JUMPER = "jumper"
MOBILE_PERSON_INTAKE_MODES = {
    MOBILE_PERSON_INTAKE_MODE_TANDEM_GUEST,
    MOBILE_PERSON_INTAKE_MODE_JUMPER,
}

MOBILE_PERSON_INTAKE_STATUS_OPEN = "open"
MOBILE_PERSON_INTAKE_STATUS_SUBMITTED = "submitted"
MOBILE_PERSON_INTAKE_STATUS_ACCEPTED = "accepted"
MOBILE_PERSON_INTAKE_STATUS_DISCARDED = "discarded"
MOBILE_PERSON_INTAKE_STATUS_EXPIRED = "expired"
MOBILE_PERSON_INTAKE_STATUSES = {
    MOBILE_PERSON_INTAKE_STATUS_OPEN,
    MOBILE_PERSON_INTAKE_STATUS_SUBMITTED,
    MOBILE_PERSON_INTAKE_STATUS_ACCEPTED,
    MOBILE_PERSON_INTAKE_STATUS_DISCARDED,
    MOBILE_PERSON_INTAKE_STATUS_EXPIRED,
}


class MobilePersonIntakeDraft(db.Model):
    """Zwischenspeicher fuer mobile Personenerfassungen vor der Freigabe."""

    __tablename__ = "mobile_person_intake_draft"

    id = db.Column(db.Integer, primary_key=True)

    mode = db.Column(db.String(20), nullable=False, index=True)
    status = db.Column(
        db.String(20),
        nullable=False,
        default=MOBILE_PERSON_INTAKE_STATUS_OPEN,
        server_default=MOBILE_PERSON_INTAKE_STATUS_OPEN,
        index=True,
    )

    submission_token_hash = db.Column(db.String(64), nullable=False, unique=True)
    submission_idempotency_key_hash = db.Column(db.String(64), nullable=True, unique=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.now(),
        index=True,
    )
    submitted_at = db.Column(db.DateTime, nullable=True, index=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(db.String(100), nullable=True)
    person_id = db.Column(
        db.Integer,
        db.ForeignKey("person.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    rejection_reason = db.Column(db.Text, nullable=True)

    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    birthdate = db.Column(db.Date, nullable=True)
    weight_kg = db.Column(db.Integer, nullable=True)
    height_cm = db.Column(db.Integer, nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(100), nullable=True)

    street_and_number = db.Column(db.String(120), nullable=True)
    zip_code = db.Column(db.String(10), nullable=True)
    city = db.Column(db.String(50), nullable=True)

    emergency_name = db.Column(db.String(100), nullable=True)
    emergency_relation = db.Column(db.String(50), nullable=True)
    emergency_phone = db.Column(db.String(30), nullable=True)

    license_number = db.Column(db.String(50), nullable=True)
    license_type = db.Column(db.String(50), nullable=True)
    license_valid_until = db.Column(db.Date, nullable=True)
    insurance_provider = db.Column(db.String(100), nullable=True)
    insurance_number = db.Column(db.String(100), nullable=True)
    is_member = db.Column(db.Boolean, nullable=True)
    is_partner_verein = db.Column(db.Boolean, nullable=True)

    __table_args__ = (
        db.CheckConstraint(
            "mode IN ('tandem_guest', 'jumper')",
            name="ck_mobile_person_intake_draft_mode",
        ),
        db.CheckConstraint(
            "status IN ('open', 'submitted', 'accepted', 'discarded', 'expired')",
            name="ck_mobile_person_intake_draft_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<MobilePersonIntakeDraft {self.id}: {self.mode}/{self.status}>"