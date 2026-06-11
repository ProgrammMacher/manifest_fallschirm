"""
Pricing Service – Pure DB-Query und Berechnungs-Helpers.
Extrahiert aus routes/pricing.py (keine Flask-Route-Logik).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, Optional, Set, Tuple

from sqlalchemy import text

from app import db
from app.helpers.status_code import normalize_status_code
from app.models.billing_config import BillingPrice, BillingPricePeriod
from app.models.flugplatz import Flugplatz
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.load import Load
from app.models.load_entry import LoadEntry
from app.models.status_definition import StatusDefinition


# ---------------------------------------------------------
# Status-Helpers
# ---------------------------------------------------------

def _active_status_defs_canonical() -> Dict[str, StatusDefinition]:
    """
    Liefert aktive StatusDefinition ohne Dopplungen:
    - kanonisiert code
    - pro canonical code erste Definition (sort_order asc) behalten
    """
    rows = (
        StatusDefinition.query
        .filter_by(is_active=True)
        .order_by(StatusDefinition.sort_order.asc(), StatusDefinition.valid_from.desc())
        .all()
    )
    out: Dict[str, StatusDefinition] = {}
    for sd in rows:
        c = normalize_status_code(sd.code)
        if c not in out:
            out[c] = sd
    return out


# ---------------------------------------------------------
# Preis-Map Helpers
# ---------------------------------------------------------

def _load_prices_map(period_id: int) -> Dict[Tuple[str, int], BillingPrice]:
    """
    GLOBAL: Lädt BillingPrice für eine Periode unabhängig vom Flugplatz.
    Wenn mehrere Flugplätze existieren, liegen mehrere Zeilen je (status,height) vor.
    Wir nehmen für die Anzeige die letzte (höchste ID).
    """
    rows = (
        BillingPrice.query
        .filter_by(period_id=period_id)
        .order_by(BillingPrice.id.asc())
        .all()
    )
    tmp: Dict[Tuple[str, int], BillingPrice] = {}
    for r in rows:
        canon = normalize_status_code(r.status_code)
        tmp[(canon, int(r.height_m))] = r
    return tmp


def _global_priced_period_ids() -> Set[int]:
    """Alle Perioden, die irgendwo Preise enthalten (egal welcher Flugplatz)."""
    rows = (
        db.session.query(BillingPrice.period_id)
        .distinct()
        .all()
    )
    return {int(r[0]) for r in rows if r and r[0] is not None}


def _period_is_active_today(p: BillingPricePeriod, today_: date) -> bool:
    """valid_from <= today AND (valid_to is None OR valid_to >= today)"""
    if not p:
        return False
    if p.valid_from and p.valid_from > today_:
        return False
    if p.valid_to and p.valid_to < today_:
        return False
    return True


def _all_airfields() -> list:
    """Alle Flugplätze (für globalen Preismodus)."""
    return Flugplatz.query.order_by(Flugplatz.name.asc()).all()


# ---------------------------------------------------------
# OrgaConfig Helpers
# ---------------------------------------------------------

def _orga_config_table_exists() -> bool:
    try:
        res = db.session.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='billing_orga_config'"
        )).fetchone()
        return bool(res)
    except Exception:
        return False


def _get_orga_cfg_db(period_id: int) -> Optional[dict]:
    """Liest Orga-Konfiguration aus billing_orga_config (falls Tabelle existiert)."""
    if not _orga_config_table_exists():
        return None

    row = db.session.execute(
        text(
            """
            SELECT orga_fee_eur, orga_fee_mode, orga_fee_vat_strategy
            FROM billing_orga_config
            WHERE period_id = :pid
            LIMIT 1
            """
        ),
        {"pid": period_id},
    ).fetchone()

    if not row:
        return None

    return {
        "amount": Decimal(str(row[0] or "0.00")),
        "mode": (row[1] or "period").strip(),
        "vat_strategy": (row[2] or "max_status").strip(),
    }


def _upsert_orga_cfg_db(
    *, period_id: int, amount: Decimal, mode: str, vat_strategy: str
) -> None:
    """Schreibt Orga-Konfiguration in billing_orga_config (UPSERT)."""
    if not _orga_config_table_exists():
        return

    db.session.execute(
        text(
            """
            INSERT INTO billing_orga_config (period_id, orga_fee_eur, orga_fee_mode, orga_fee_vat_strategy)
            VALUES (:pid, :amt, :mode, :vs)
            ON CONFLICT(period_id)
            DO UPDATE SET
                orga_fee_eur = excluded.orga_fee_eur,
                orga_fee_mode = excluded.orga_fee_mode,
                orga_fee_vat_strategy = excluded.orga_fee_vat_strategy
            """
        ),
        {"pid": period_id, "amt": str(amount), "mode": mode, "vs": vat_strategy},
    )


def _load_orga_for_period(period_id: int) -> dict:
    """
    Orga laden (global pro Periode):
    1) billing_orga_config (Periode) wenn vorhanden
    2) billing_price_period.orga_fee_* (Default/Fallback)
    """
    cfg = _get_orga_cfg_db(period_id)
    if cfg:
        return cfg

    amount = Decimal("0.00")
    mode = "period"
    vat_strategy = "max_status"

    period = BillingPricePeriod.query.get(period_id)
    if period:
        if getattr(period, "orga_fee_eur", None) is not None:
            amount = Decimal(str(period.orga_fee_eur or "0.00"))
        mode = (getattr(period, "orga_fee_mode", mode) or mode).strip()
        vat_strategy = (getattr(period, "orga_fee_vat_strategy", vat_strategy) or vat_strategy).strip()

    return {"amount": amount, "mode": mode, "vat_strategy": vat_strategy}


# ---------------------------------------------------------
# Invoice/Usage Guard Helpers
# ---------------------------------------------------------

def _pricing_model_is_used_by_invoices(period_id: int) -> bool:
    """
    True, wenn es mindestens eine NICHT stornierte Rechnung gibt,
    die Positionen aus Loads enthält, die an dieses Preismodell gebunden sind.
    """
    q = (
        db.session.query(Invoice.id)
        .join(InvoiceItem, InvoiceItem.invoice_id == Invoice.id)
        .join(LoadEntry, LoadEntry.id == InvoiceItem.load_entry_id)
        .join(Load, Load.id == LoadEntry.load_id)
        .filter(Invoice.is_deleted.is_(False))
        .filter(getattr(Load, "pricing_model_id") == period_id)
        .limit(1)
    )
    return q.first() is not None


def _used_jump_price_keys_by_invoices(period_id: int) -> Set[Tuple[str, int]]:
    """
    Liefert alle Sprungpreis-Schlüssel (status_code, height_m), die bereits
    in nicht stornierten Rechnungen für dieses Preismodell verwendet wurden.
    """
    rows = (
        db.session.query(LoadEntry.status_code, LoadEntry.height_m)
        .select_from(Invoice)
        .join(InvoiceItem, InvoiceItem.invoice_id == Invoice.id)
        .join(LoadEntry, LoadEntry.id == InvoiceItem.load_entry_id)
        .join(Load, Load.id == LoadEntry.load_id)
        .filter(Invoice.is_deleted.is_(False))
        .filter(InvoiceItem.description.like("Sprung %"))
        .filter(getattr(Load, "pricing_model_id") == period_id)
        .distinct()
        .all()
    )
    return {
        (normalize_status_code(status_code), int(height_m or 0))
        for status_code, height_m in rows
    }


def _orga_price_is_used_by_invoices(period_id: int) -> bool:
    """
    True, wenn die Orga-Pauschale dieses Preismodells bereits in nicht
    stornierten Rechnungen vorkommt.
    """
    q = (
        db.session.query(InvoiceItem.id)
        .select_from(Invoice)
        .join(InvoiceItem, InvoiceItem.invoice_id == Invoice.id)
        .join(LoadEntry, LoadEntry.id == InvoiceItem.load_entry_id)
        .join(Load, Load.id == LoadEntry.load_id)
        .filter(Invoice.is_deleted.is_(False))
        .filter(InvoiceItem.description.like("Organisationspauschale%"))
        .filter(getattr(Load, "pricing_model_id") == period_id)
        .limit(1)
    )
    return q.first() is not None


def _used_price_key_tokens(period_id: int) -> Set[str]:
    return {
        f"{code}|{height_m}"
        for code, height_m in _used_jump_price_keys_by_invoices(period_id)
    }


def _used_vat_status_codes(period_id: int) -> Set[str]:
    return {
        code
        for code, _ in _used_jump_price_keys_by_invoices(period_id)
    }


# Hinzugefügt: Funktion zur Generierung des neuen Verwendungszwecks

def generate_invoice_purpose(invoice, airfield, start_date, end_date):
    """
    Generiert den Verwendungszweck für eine Rechnung.
    Beispiel: "Rechnung 2026-Spruenge-Nr. 21 - Mellenthin vom 9.5. bis 12.5.2026 - Oliver Uhlmann"
    """
    purpose = f"Rechnung {invoice.created_at.year}-Spruenge-Nr. {invoice.seq_number or invoice.id}"
    if airfield:
        purpose += f" - {airfield}"
    if start_date and end_date:
        purpose += f" vom {start_date.strftime('%d.%m.%Y')} bis {end_date.strftime('%d.%m.%Y')}"
    purpose += f" - {invoice.person.full_name}"
    return purpose
