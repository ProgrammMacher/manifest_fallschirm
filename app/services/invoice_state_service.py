from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app import now_local
from app.constants import (
    INVOICE_PAYMENT_STATE_OPEN,
    INVOICE_PAYMENT_STATE_PAID,
    INVOICE_PAYMENT_STATE_SEPA_EXPORTED,
    INVOICE_PAYMENT_STATE_SEPA_PENDING,
    INVOICE_PAYMENT_STATE_SEPA_RETURNED,
    INVOICE_PAYMENT_STATES,
    TANDEM_GUEST_STATUSES,
)
from app.helpers.status_code import normalize_status_code

if TYPE_CHECKING:
    from app.models.invoice import Invoice
    from app.models.person import Person


now_berlin = now_local

PAYMENT_STATE_LABELS = {
    INVOICE_PAYMENT_STATE_OPEN: "Offen",
    INVOICE_PAYMENT_STATE_SEPA_PENDING: "SEPA vorgemerkt",
    INVOICE_PAYMENT_STATE_SEPA_EXPORTED: "SEPA exportiert",
    INVOICE_PAYMENT_STATE_PAID: "Bezahlt",
    INVOICE_PAYMENT_STATE_SEPA_RETURNED: "Rücklastschrift",
}

_TANDEM_GUEST_STATUS_CODES = {normalize_status_code(code) for code in TANDEM_GUEST_STATUSES}


def _person_allows_sepa(person: Any | None) -> bool:
    if not person:
        return False
    if bool(getattr(person, "is_tandem_guest", False)):
        return False
    if not bool(getattr(person, "sepa_enabled", False)):
        return False
    if not (getattr(person, "iban", "") or "").strip():
        return False
    if not (getattr(person, "account_holder", "") or "").strip():
        return False
    if getattr(person, "sepa_mandate_date", None) is None:
        return False
    return True


def _invoice_has_tandem_guest_context(invoice: Any | None) -> bool:
    if not invoice:
        return False

    for item in getattr(invoice, "items", []) or []:
        load_entry = getattr(item, "load_entry", None)
        if not load_entry:
            continue
        status_code = normalize_status_code(getattr(load_entry, "status_code", ""))
        if status_code in _TANDEM_GUEST_STATUS_CODES:
            return True

    return False


def _invoice_allows_sepa(invoice: Any | None) -> bool:
    if not invoice:
        return False
    if not _person_allows_sepa(getattr(invoice, "person", None)):
        return False
    if _invoice_has_tandem_guest_context(invoice):
        return False
    return True


def _invoice_payment_state(invoice: Any | None) -> str:
    if not invoice:
        return INVOICE_PAYMENT_STATE_OPEN

    if bool(getattr(invoice, "is_paid", False)):
        return INVOICE_PAYMENT_STATE_PAID

    raw = (getattr(invoice, "payment_state", "") or "").strip().lower()
    if raw in INVOICE_PAYMENT_STATES:
        if raw == INVOICE_PAYMENT_STATE_PAID:
            return INVOICE_PAYMENT_STATE_OPEN
        if (
            raw in {
                INVOICE_PAYMENT_STATE_SEPA_PENDING,
                INVOICE_PAYMENT_STATE_SEPA_EXPORTED,
                INVOICE_PAYMENT_STATE_SEPA_RETURNED,
            }
            and not _invoice_allows_sepa(invoice)
        ):
            return INVOICE_PAYMENT_STATE_OPEN
        return raw

    if (getattr(invoice, "payment_method", "") or "").strip().lower() == "sepa" and _invoice_allows_sepa(invoice):
        return INVOICE_PAYMENT_STATE_SEPA_PENDING
    return INVOICE_PAYMENT_STATE_OPEN


def _invoice_payment_state_label(invoice: Any | None) -> str:
    return PAYMENT_STATE_LABELS.get(_invoice_payment_state(invoice), "Offen")


def _reset_invoice_after_sepa_rollback(invoice: Any) -> None:
    """Setzt eine Rechnung nach einem Dev-Rollback wieder auf einen neutralen offenen Zustand zurück."""
    _set_invoice_payment_state(invoice, INVOICE_PAYMENT_STATE_OPEN)
    invoice.payment_method = None
    invoice.is_paid = False
    invoice.paid_at = None


def _set_invoice_payment_state(invoice: Any, payment_state: str) -> str:
    state = (payment_state or "").strip().lower()
    if state not in INVOICE_PAYMENT_STATES:
        state = INVOICE_PAYMENT_STATE_OPEN

    if state in {
        INVOICE_PAYMENT_STATE_SEPA_PENDING,
        INVOICE_PAYMENT_STATE_SEPA_EXPORTED,
        INVOICE_PAYMENT_STATE_SEPA_RETURNED,
    } and not _invoice_allows_sepa(invoice):
        state = INVOICE_PAYMENT_STATE_OPEN

    invoice.payment_state = state
    if state == INVOICE_PAYMENT_STATE_PAID:
        invoice.is_paid = True
        if not getattr(invoice, "paid_at", None):
            invoice.paid_at = now_berlin().replace(tzinfo=None)
    else:
        invoice.is_paid = False
        invoice.paid_at = None

    if state in {INVOICE_PAYMENT_STATE_SEPA_PENDING, INVOICE_PAYMENT_STATE_SEPA_EXPORTED, INVOICE_PAYMENT_STATE_SEPA_RETURNED}:
        invoice.payment_method = "sepa"

    return state


def _is_allowed_payment_state_transition(current_state: str, next_state: str) -> bool:
    allowed = {
        INVOICE_PAYMENT_STATE_OPEN: {
            INVOICE_PAYMENT_STATE_OPEN,
            INVOICE_PAYMENT_STATE_SEPA_PENDING,
            INVOICE_PAYMENT_STATE_PAID,
        },
        INVOICE_PAYMENT_STATE_SEPA_PENDING: {
            INVOICE_PAYMENT_STATE_OPEN,
            INVOICE_PAYMENT_STATE_SEPA_PENDING,
            INVOICE_PAYMENT_STATE_SEPA_EXPORTED,
            INVOICE_PAYMENT_STATE_PAID,
        },
        INVOICE_PAYMENT_STATE_SEPA_EXPORTED: {
            INVOICE_PAYMENT_STATE_OPEN,
            INVOICE_PAYMENT_STATE_SEPA_EXPORTED,
            INVOICE_PAYMENT_STATE_SEPA_RETURNED,
            INVOICE_PAYMENT_STATE_PAID,
        },
        INVOICE_PAYMENT_STATE_SEPA_RETURNED: {
            INVOICE_PAYMENT_STATE_OPEN,
            INVOICE_PAYMENT_STATE_SEPA_PENDING,
            INVOICE_PAYMENT_STATE_SEPA_RETURNED,
            INVOICE_PAYMENT_STATE_PAID,
        },
        INVOICE_PAYMENT_STATE_PAID: {
            INVOICE_PAYMENT_STATE_OPEN,
            INVOICE_PAYMENT_STATE_SEPA_RETURNED,
            INVOICE_PAYMENT_STATE_PAID,
        },
    }
    return next_state in allowed.get(current_state, {INVOICE_PAYMENT_STATE_OPEN})
