from __future__ import annotations

from datetime import datetime
import hashlib
import secrets

from app import db
from app.models.mobile_person_intake_draft import (
    MOBILE_PERSON_INTAKE_MODES,
    MOBILE_PERSON_INTAKE_STATUS_ACCEPTED,
    MOBILE_PERSON_INTAKE_STATUS_DISCARDED,
    MOBILE_PERSON_INTAKE_STATUS_EXPIRED,
    MOBILE_PERSON_INTAKE_STATUS_OPEN,
    MOBILE_PERSON_INTAKE_STATUS_SUBMITTED,
    MobilePersonIntakeDraft,
)


SUBMISSION_FIELDS = {
    "first_name",
    "last_name",
    "birthdate",
    "weight_kg",
    "height_cm",
    "phone",
    "email",
    "street_and_number",
    "zip_code",
    "city",
    "emergency_name",
    "emergency_relation",
    "emergency_phone",
    "license_number",
    "license_valid_until",
    "insurance_provider",
    "insurance_number",
    "is_member",
    "is_partner_verein",
}


ALLOWED_STATUS_TRANSITIONS = {
    MOBILE_PERSON_INTAKE_STATUS_OPEN: {
        MOBILE_PERSON_INTAKE_STATUS_SUBMITTED,
        MOBILE_PERSON_INTAKE_STATUS_EXPIRED,
    },
    MOBILE_PERSON_INTAKE_STATUS_SUBMITTED: {
        MOBILE_PERSON_INTAKE_STATUS_ACCEPTED,
        MOBILE_PERSON_INTAKE_STATUS_DISCARDED,
    },
    MOBILE_PERSON_INTAKE_STATUS_ACCEPTED: set(),
    MOBILE_PERSON_INTAKE_STATUS_DISCARDED: set(),
    MOBILE_PERSON_INTAKE_STATUS_EXPIRED: set(),
}


def _transition_draft_status(draft: MobilePersonIntakeDraft, target_status: str) -> None:
    allowed_targets = ALLOWED_STATUS_TRANSITIONS.get(draft.status, set())
    if target_status not in allowed_targets:
        raise ValueError(
            f"Ungültiger Statuswechsel: {draft.status} -> {target_status}."
        )
    draft.status = target_status


def generate_submission_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_draft_by_submission_token(token: str) -> MobilePersonIntakeDraft | None:
    token_hash = hashlib.sha256((token or "").encode("utf-8")).hexdigest()
    return MobilePersonIntakeDraft.query.filter_by(
        submission_token_hash=token_hash
    ).one_or_none()


def expire_draft_if_needed(
    draft: MobilePersonIntakeDraft,
    *,
    now: datetime | None = None,
) -> bool:
    now = now or datetime.utcnow()
    if (
        draft.status == MOBILE_PERSON_INTAKE_STATUS_OPEN
        and draft.expires_at <= now
    ):
        _transition_draft_status(draft, MOBILE_PERSON_INTAKE_STATUS_EXPIRED)
        db.session.commit()
        return True
    return False


def create_draft(*, mode: str, submission_token_hash: str, expires_at: datetime) -> MobilePersonIntakeDraft:
    if mode not in MOBILE_PERSON_INTAKE_MODES:
        raise ValueError("Unbekannter Erfassungsmodus.")
    if not submission_token_hash:
        raise ValueError("Ein Token-Hash ist erforderlich.")

    draft = MobilePersonIntakeDraft(
        mode=mode,
        status=MOBILE_PERSON_INTAKE_STATUS_OPEN,
        submission_token_hash=submission_token_hash,
        expires_at=expires_at,
    )
    db.session.add(draft)
    db.session.commit()
    return draft


def get_draft(draft_id: int) -> MobilePersonIntakeDraft | None:
    return db.session.get(MobilePersonIntakeDraft, draft_id)


def list_drafts(*, status: str | None = None) -> list[MobilePersonIntakeDraft]:
    query = MobilePersonIntakeDraft.query.order_by(MobilePersonIntakeDraft.created_at.desc())
    if status is not None:
        query = query.filter_by(status=status)
    return query.all()


def list_open_drafts() -> list[MobilePersonIntakeDraft]:
    return (
        MobilePersonIntakeDraft.query.filter(
            MobilePersonIntakeDraft.status.in_(
                (MOBILE_PERSON_INTAKE_STATUS_OPEN, MOBILE_PERSON_INTAKE_STATUS_SUBMITTED)
            )
        )
        .order_by(MobilePersonIntakeDraft.created_at.desc())
        .all()
    )


def submit_draft(
    draft: MobilePersonIntakeDraft,
    *,
    values: dict,
    idempotency_key_hash: str,
    submitted_at: datetime | None = None,
) -> MobilePersonIntakeDraft:
    if draft.status != MOBILE_PERSON_INTAKE_STATUS_OPEN:
        raise ValueError("Der Entwurf kann nicht mehr übermittelt werden.")
    if not idempotency_key_hash:
        raise ValueError("Ein Idempotenz-Hash ist erforderlich.")
    if expire_draft_if_needed(draft):
        raise ValueError("Der Entwurf ist abgelaufen.")

    for field_name, value in values.items():
        if field_name in SUBMISSION_FIELDS:
            setattr(draft, field_name, value)

    draft.submission_idempotency_key_hash = idempotency_key_hash
    draft.submitted_at = submitted_at or datetime.utcnow()
    _transition_draft_status(draft, MOBILE_PERSON_INTAKE_STATUS_SUBMITTED)
    db.session.commit()
    return draft


def accept_draft(
    draft: MobilePersonIntakeDraft,
    *,
    reviewed_by: str,
    person_id: int,
    reviewed_at: datetime | None = None,
    commit: bool = True,
) -> MobilePersonIntakeDraft:
    if draft.status != MOBILE_PERSON_INTAKE_STATUS_SUBMITTED:
        raise ValueError("Nur übermittelte Entwürfe können übernommen werden.")

    _transition_draft_status(draft, MOBILE_PERSON_INTAKE_STATUS_ACCEPTED)
    draft.reviewed_by = reviewed_by
    draft.reviewed_at = reviewed_at or datetime.utcnow()
    draft.person_id = person_id
    if commit:
        db.session.commit()
    return draft


def discard_draft(
    draft: MobilePersonIntakeDraft,
    *,
    reviewed_by: str,
    rejection_reason: str = "",
    reviewed_at: datetime | None = None,
) -> MobilePersonIntakeDraft:
    if draft.status != MOBILE_PERSON_INTAKE_STATUS_SUBMITTED:
        raise ValueError("Nur übermittelte Entwürfe können verworfen werden.")

    _transition_draft_status(draft, MOBILE_PERSON_INTAKE_STATUS_DISCARDED)
    draft.reviewed_by = reviewed_by
    draft.reviewed_at = reviewed_at or datetime.utcnow()
    draft.rejection_reason = rejection_reason or None
    db.session.commit()
    return draft


def expire_open_drafts(*, now: datetime | None = None) -> int:
    now = now or datetime.utcnow()
    drafts = MobilePersonIntakeDraft.query.filter(
        MobilePersonIntakeDraft.status == MOBILE_PERSON_INTAKE_STATUS_OPEN,
        MobilePersonIntakeDraft.expires_at <= now,
    ).all()
    for draft in drafts:
        _transition_draft_status(draft, MOBILE_PERSON_INTAKE_STATUS_EXPIRED)
    if drafts:
        db.session.commit()
    return len(drafts)