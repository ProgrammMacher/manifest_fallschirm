from app.routes.billing import _parse_invoice_list_filters, _sort_invoices_for_list
from app.models.invoice import Invoice
from app.models.person import Person
from app.models.billing_config import BillingConfig


def test_parse_invoice_list_filters_accepts_sepa_filter_values():
    filters = _parse_invoice_list_filters({
        "status": "sepa_pending",
        "sort": "sepa_pending_first",
    })

    assert filters["status"] == "sepa_pending"
    assert filters["sort"] == "sepa_pending_first"


def test_sort_invoices_for_list_supports_sepa_priority_orders():
    invoice_a = Invoice(id=1, payment_state="sepa_exported")
    invoice_b = Invoice(id=2, payment_state="sepa_pending")
    invoice_c = Invoice(id=3, payment_state="open")

    ordered = _sort_invoices_for_list([invoice_a, invoice_b, invoice_c], "sepa_pending_first")
    assert [inv.id for inv in ordered] == [2, 1, 3]

    ordered = _sort_invoices_for_list([invoice_a, invoice_b, invoice_c], "sepa_exported_first")
    assert [inv.id for inv in ordered] == [1, 2, 3]

    ordered = _sort_invoices_for_list([invoice_a, invoice_b, invoice_c], "sepa_last")
    assert [inv.id for inv in ordered] == [3, 2, 1]
