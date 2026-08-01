from __future__ import annotations

from types import SimpleNamespace

from app.constants import INVOICE_PAYMENT_STATE_OPEN, INVOICE_PAYMENT_STATE_PAID
from app.services.invoice_state_service import (
    _invoice_payment_state,
    _invoice_payment_state_label,
    _set_invoice_payment_state,
)


def test_set_invoice_payment_state_marks_invoice_paid_and_labels_it():
    invoice = SimpleNamespace(
        stage="final",
        total_amount=100,
        payment_state=INVOICE_PAYMENT_STATE_OPEN,
        is_paid=False,
        paid_at=None,
        payment_method=None,
        person=None,
        items=[],
    )

    state = _set_invoice_payment_state(invoice, INVOICE_PAYMENT_STATE_PAID)

    assert state == INVOICE_PAYMENT_STATE_PAID
    assert invoice.is_paid is True
    assert invoice.paid_at is not None
    assert _invoice_payment_state(invoice) == INVOICE_PAYMENT_STATE_PAID
    assert _invoice_payment_state_label(invoice) == "Bezahlt"
