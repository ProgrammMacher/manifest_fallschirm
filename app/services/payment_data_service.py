from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from app.models.billing_config import BillingConfig

if TYPE_CHECKING:
    from app.models.invoice import Invoice


def _short_airfield_place(name: str) -> str:
    raw = (name or "").strip()
    if not raw:
        return ""

    lowered = raw.lower()
    prefixes = (
        "flugplatz ",
        "flugfeld ",
        "airfield ",
        "airport ",
        "dz ",
        "dropzone ",
    )
    for prefix in prefixes:
        if lowered.startswith(prefix):
            raw = raw[len(prefix):].strip(" -")
            break

    for sep in (" - ", " / ", ", ", "("):
        if sep in raw:
            raw = raw.split(sep, 1)[0].strip()
            break

    return raw.split()[0] if raw.split() else ""


def _invoice_airfield_and_date_range(invoice: Invoice):
    airfields = set()
    jump_dates = []

    for item in list(getattr(invoice, "items", []) or []):
        le = getattr(item, "load_entry", None)
        ld = getattr(le, "load", None) if le else None
        if not ld:
            continue

        airfield = getattr(ld, "airfield", None)
        airfield_name = getattr(airfield, "name", "") if airfield else ""
        short_name = _short_airfield_place(airfield_name)
        if short_name:
            airfields.add(short_name)

        dt_value = getattr(ld, "actual_time", None) or getattr(ld, "scheduled_time", None) or getattr(ld, "created_at", None)
        if dt_value:
            jump_dates.append(dt_value.date())

    airfield_text = ""
    if len(airfields) == 1:
        airfield_text = next(iter(airfields))
    elif len(airfields) > 1:
        airfield_text = "mehrere Orte"

    start_date = min(jump_dates) if jump_dates else None
    end_date = max(jump_dates) if jump_dates else None
    return airfield_text, start_date, end_date


def _format_purpose_date_range(start_date, end_date) -> str:
    if not start_date or not end_date:
        return ""
    if start_date == end_date:
        return f"vom {start_date.day}.{start_date.month}.{start_date.year}"
    if start_date.year == end_date.year:
        return (
            f"vom {start_date.day}.{start_date.month}. bis "
            f"{end_date.day}.{end_date.month}.{end_date.year}"
        )
    return (
        f"vom {start_date.day}.{start_date.month}.{start_date.year} bis "
        f"{end_date.day}.{end_date.month}.{end_date.year}"
    )


def build_invoice_payment_purpose(invoice: "Invoice", doc_label: str = "Rechnung", invoice_number: int | None = None) -> str:
    inv_year = invoice.created_at.year if getattr(invoice, "created_at", None) else date.today().year
    inv_no = invoice_number if invoice_number is not None else getattr(invoice, "seq_number", None) or getattr(invoice, "id", 0) or 0
    person_name = (getattr(getattr(invoice, "person", None), "full_name", "") or "").strip()

    has_manual_items = False
    has_load_items = False
    for item in list(getattr(invoice, "items", []) or []):
        if (getattr(item, "item_source", "") or "").strip().lower() == "manual":
            has_manual_items = True
        if getattr(item, "load_entry", None):
            has_load_items = True

    purpose_topic = "Spruenge"
    if has_manual_items and not has_load_items:
        purpose_topic = (getattr(invoice, "manual_title", "") or "").strip() or "Manuelle Positionen"
    elif has_manual_items and has_load_items:
        purpose_topic = "Leistungen"

    parts = [f"{doc_label} {inv_year}-{purpose_topic}-Nr. {inv_no}"]
    airfield_text, start_date, end_date = _invoice_airfield_and_date_range(invoice)
    if (not start_date or not end_date) and getattr(invoice, "service_date", None):
        start_date = invoice.service_date
        end_date = invoice.service_date
    if airfield_text:
        parts.append(airfield_text)

    date_text = _format_purpose_date_range(start_date, end_date)
    if date_text:
        parts.append(date_text)

    if person_name:
        parts.append(person_name)

    return " - ".join(parts)


def build_payment_context(*, invoice: "Invoice", billing_config: BillingConfig | None, invoice_number: int | None = None, amount_eur: Decimal | None = None) -> dict[str, Any]:
    payment_purpose = build_invoice_payment_purpose(invoice, invoice_number=invoice_number)
    if billing_config is None:
        billing_config = BillingConfig()

    creditor_name = (getattr(billing_config, "company_name", "") or "").strip()
    creditor_iban = (getattr(billing_config, "iban", "") or "").strip()
    creditor_bic = (getattr(billing_config, "bic", "") or "").strip()

    amount_value = Decimal(str(amount_eur or "0.00"))
    amount_str = f"{amount_value:.2f}"
    remittance = payment_purpose

    lines = [
        "BCD",
        "002",
        "1",
        "SCT",
        (creditor_bic or "").strip(),
        (creditor_name or "").strip(),
        (creditor_iban or "").replace(" ", "").strip(),
        f"EUR{amount_str}",
        "",
        remittance,
        "",
    ]
    payload = "\n".join(lines)

    return {
        "company_name": creditor_name,
        "iban": creditor_iban,
        "bic": creditor_bic,
        "remittance_information": remittance,
        "epc_payload": payload,
    }
