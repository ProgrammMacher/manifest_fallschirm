# C:\manifest_fallschirm\app\routes\pricing.py
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, Tuple, List, Optional, Set, Iterable
import os
import base64

from flask import Blueprint, request, render_template, redirect, url_for, flash, session, current_app, make_response
from sqlalchemy import text

from app import db, now_local
from app.models.flugplatz import Flugplatz
from app.models.billing_config import (
    BillingConfig,
    BillingPrice,
    BillingPricePeriod,
    BillingOrgaRule,
)
from app.models.status_definition import StatusDefinition
from app.services.price_seed_service import PriceSeedService
from app.helpers.status_code import is_ku_credit_payout_applicable_status, normalize_status_code

# Für Safety-Guard „Matrix darf nicht geändert werden, wenn Rechnungen existieren“
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.load_entry import LoadEntry
from app.models.load import Load  # benötigt pricing_model_id im Load-Model
from app.helpers.pdf_runtime import ensure_weasyprint_pdf_runtime
from app.services.billing_service import _image_to_data_uri

# Service-Layer: extrahierte DB-Query-Helpers
from app.services.pricing_service import (
    _active_status_defs_canonical,
    _load_prices_map,
    _global_priced_period_ids,
    _period_is_active_today,
    _all_airfields,
    _orga_config_table_exists,
    _get_orga_cfg_db,
    _upsert_orga_cfg_db,
    _load_orga_for_period,
    _pricing_model_is_used_by_invoices,
    _used_jump_price_keys_by_invoices,
    _orga_price_is_used_by_invoices,
    _used_price_key_tokens,
    _used_vat_status_codes,
)


bp_pricing = Blueprint("pricing", __name__, url_prefix="/pricing")


# =========================================================
# 🔒 ADMIN-GUARD: Preismatrix nur für Admins
# =========================================================
@bp_pricing.before_request
def _pricing_admin_only():
    if not session.get("is_admin"):
        flash(
            "Zugriff verweigert: Die Preismatrix ist ein Administrationsbereich.",
            "danger",
        )
        return redirect(url_for("load.list_loads"))


# =========================================================
# ✅ Variante A – GLOBALER PREISMODUS (flugplatzunabhängig in der UI)
# =========================================================
# Technische Realität (DB): Preise sind global pro Periode/Status/Höhe.
# Speichern/Seed/Reset/Normalize arbeiten flugplatzunabhängig.
GLOBAL_PRICE_MODE = True


# ---------------------------------------------------------
# Gültige Absprunghöhen für die Preismatrix
# ---------------------------------------------------------
VALID_HEIGHTS: List[int] = [1500, 3000, 4000]

# ---------------------------------------------------------
# Filter: Status, die NICHT in der Sprungpreis-Matrix erscheinen
# ---------------------------------------------------------
EXCLUDE_STATUS_PREFIXES = (
    "Miete ",
    "Miete Fallschirm ",
)
EXCLUDE_CODES_EXACT = {"Orga"}

PARTNER_TOPUP_CODE = "Auffüller Partner-Verein"
MEMBER_TOPUP_CODE = "Auffüller Verein"
GUEST_TOPUP_CODE = "Auffüller Gast"
PARTNER_TOPUP_FALLBACK_LABEL = "Auffüller eines Tandemloads – Partner-Verein Auffüller Partner-Verein"



# ---------------------------------------------------------
# Helpers: Parsing
# ---------------------------------------------------------
def _dec(raw: Optional[str], default: Decimal = Decimal("0.00")) -> Decimal:
    """Robust: '22,00', '22.00', ' 22 ', '22 €'."""
    if raw is None:
        return default
    s = str(raw).strip().replace("€", "").replace(" ", "").replace(",", ".")
    if not s:
        return default
    try:
        return Decimal(s)
    except InvalidOperation:
        return default


def _int(raw: Optional[str], default: int = 0) -> int:
    try:
        if raw is None:
            return default
        s = str(raw).strip()
        if not s:
            return default
        return int(s)
    except Exception:
        return default


def _parse_date_any(s: str) -> Optional[date]:
    """Akzeptiert TT.MM.JJJJ oder YYYY-MM-DD."""
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError("invalid date")


# ---------------------------------------------------------
# Helper: Schirmmiete-Konfiguration für die Preismatrix
# ---------------------------------------------------------
def _build_canopy_rent_config(config: Optional[BillingConfig]) -> Dict[str, dict]:
    """
    Baut die Schirmmiete-Datenstruktur für das Template.
    Diese Werte sind NICHT höhenabhängig und gelten global.

    Keys müssen zum Template passen:
      - verein
      - gast
      - tandemmaster
    """
    z = Decimal("0.00")

    # Fallback: keine BillingConfig vorhanden
    if not config:
        return {
            "verein": {
                "label": "Miete Fallschirm Verein, maximale Berechnung x pro Tag",
                "price": z,
                "max_count": 0,
                "vat_rate": z,
            },
            "partner_verein": {
                "label": "Miete Fallschirm Partner-Verein, maximale Berechnung x pro Tag",
                "price": z,
                "max_count": 0,
                "vat_rate": z,
            },
            "gast": {
                "label": "Miete Fallschirm Gast, maximale Berechnung x pro Tag",
                "price": z,
                "max_count": 0,
                "vat_rate": z,
            },
            "tandemmaster": {
                "label": "Miete Fallschirm Tandemmaster, maximale Berechnung x pro Tag",
                "price": z,
                "max_count": 0,
                "vat_rate": z,
            },
        }

    # Normale Konfiguration aus BillingConfig
    return {
        "verein": {
            "label": "Miete Fallschirm Verein, maximale Berechnung x pro Tag",
            "price": Decimal(str(getattr(config, "canopy_rent_member_eur", 0) or "0.00")),
            "max_count": int(getattr(config, "canopy_rent_member_max_count", 0) or 0),
            "vat_rate": Decimal(str(getattr(config, "canopy_rent_member_vat_rate", 0) or "0.00")),
        },
        # Partner-Verein nutzt dieselbe Logik/Preise wie Verein.
        "partner_verein": {
            "label": "Miete Fallschirm Partner-Verein, maximale Berechnung x pro Tag",
            "price": Decimal(str(getattr(config, "canopy_rent_partner_member_eur", 0) or "0.00")),
            "max_count": int(getattr(config, "canopy_rent_partner_member_max_count", 0) or 0),
            "vat_rate": Decimal(str(getattr(config, "canopy_rent_partner_member_vat_rate", 0) or "0.00")),
        },
        "gast": {
            "label": "Miete Fallschirm Gast, maximale Berechnung x pro Tag",
            "price": Decimal(str(getattr(config, "canopy_rent_guest_eur", 0) or "0.00")),
            "max_count": int(getattr(config, "canopy_rent_guest_max_count", 0) or 0),
            "vat_rate": Decimal(str(getattr(config, "canopy_rent_guest_vat_rate", 0) or "0.00")),
        },
        "tandemmaster": {
            "label": "Miete Fallschirm Tandemmaster, maximale Berechnung x pro Tag",
            "price": Decimal(str(getattr(config, "canopy_rent_tm_eur", 0) or "0.00")),
            "max_count": int(getattr(config, "canopy_rent_tm_max_count", 0) or 0),
            "vat_rate": Decimal(str(getattr(config, "canopy_rent_tm_vat_rate", 0) or "0.00")),
        },
    }

# ---------------------------------------------------------
# Helpers: Status/Matrix
# ---------------------------------------------------------
def _clean_label(code: str, label: str) -> str:
    """Entfernt unerwünschte Geldbeträge aus Schüler-Kurs-Labels (nur Anzeige)."""
    if not label:
        return label
    if code in ("Schüler Ek 1", "Schüler Ek 2", "Schüler GK 6"):
        label = (
            label
            .replace(" - 250 €", "")
            .replace(" - 290 €", "")
            .replace(" - 600 €", "")
            .replace(" 250 €", "")
            .replace(" 290 €", "")
            .replace(" 600 €", "")
        )
    return label


def _is_excluded_from_jump_matrix(code: str) -> bool:
    """Entfernt Miete-* und Orga aus der Sprungpreis-Matrix."""
    if code in EXCLUDE_CODES_EXACT:
        return True
    for pref in EXCLUDE_STATUS_PREFIXES:
        if code.startswith(pref):
            return True
    return False


# ---------------------------------------------------------
# Preis-Matrix (GLOBAL) – via pricing_service
# ---------------------------------------------------------
def _format_price_conflict_label(
    code: str,
    height_m: int,
    statuses: Dict[str, StatusDefinition],
) -> str:
    sd = statuses.get(code)
    label = _clean_label(code, sd.label or code) if sd is not None else code
    return f"{label} ({height_m} m)"


def _find_used_price_conflicts(period_id: int, form) -> List[str]:
    """
    Prüft nur tatsächlich geänderte Preise. Bereits verwendete Preise dürfen
    nicht überschrieben werden; unbenutzte Preise derselben Matrix schon.
    """
    existing_prices = _load_prices_map(period_id)
    statuses = _active_status_defs_canonical()
    used_jump_keys = _used_jump_price_keys_by_invoices(period_id)

    conflicts: List[str] = []
    seen_conflicts: Set[str] = set()

    for code_raw in form.getlist("status_code"):
        code = normalize_status_code(code_raw)
        if _is_excluded_from_jump_matrix(code):
            continue

        vat_val = _dec(form.get(f"vat_{code}"), default=Decimal("0.00"))
        sd = (
            StatusDefinition.query
            .filter_by(code=code, is_active=True)
            .order_by(StatusDefinition.valid_from.desc())
            .first()
        )
        old_vat = (
            Decimal(str(sd.vat_rate))
            if sd is not None and sd.vat_rate is not None
            else Decimal("0.00")
        )
        if vat_val != old_vat and any(used_code == code for used_code, _ in used_jump_keys):
            label = _clean_label(code, sd.label or code) if sd is not None else code
            vat_conflict = f"MwSt für {label}"
            if vat_conflict not in seen_conflicts:
                conflicts.append(vat_conflict)
                seen_conflicts.add(vat_conflict)

        for h in VALID_HEIGHTS:
            new_price = _dec(form.get(f"price_{code}_{h}"), default=Decimal("0.00"))
            existing = existing_prices.get((code, int(h)))
            old_price = (
                Decimal(str(existing.price_eur))
                if existing is not None
                else Decimal("0.00")
            )
            if new_price == old_price:
                continue
            if (code, int(h)) not in used_jump_keys:
                continue

            label = _format_price_conflict_label(code, int(h), statuses)
            if label not in seen_conflicts:
                conflicts.append(label)
                seen_conflicts.add(label)

    old_orga_amount = Decimal(str(_load_orga_for_period(period_id).get("amount") or "0.00"))
    new_orga_amount = _dec(form.get("orga_fee_eur"), default=Decimal("0.00"))
    if new_orga_amount != old_orga_amount and _orga_price_is_used_by_invoices(period_id):
        conflicts.append("Orga – Organisationspauschale")

    return conflicts


def _find_inconsistent_ku_payout_basis(period_id: int, statuses: Optional[Dict[str, StatusDefinition]] = None) -> List[Dict[str, object]]:
    """Findet innerhalb derselben Periode inkonsistente KU-Vergütungsregeln pro Status."""
    rows = BillingPrice.query.filter_by(period_id=period_id).all()
    grouped: Dict[str, set[str]] = {}

    for row in rows:
        code = normalize_status_code(getattr(row, "status_code", "") or "")
        if not code or not is_ku_credit_payout_applicable_status(code):
            continue
        basis = (getattr(row, "ku_credit_payout_basis", None) or "gross").strip().lower()
        if basis not in {"gross", "net"}:
            basis = "gross"
        grouped.setdefault(code, set()).add(basis)

    inconsistencies: List[Dict[str, object]] = []
    for code, values in sorted(grouped.items()):
        if len(values) <= 1:
            continue
        label = code
        if statuses:
            sd = statuses.get(code)
            if sd is not None:
                label = _clean_label(code, sd.label or code)
        display_values = ["Brutto" if value == "gross" else "Netto" for value in sorted(values)]
        inconsistencies.append({
            "code": code,
            "label": label,
            "values": display_values,
        })

    return inconsistencies


# ---------------------------------------------------------
# GET: Preismatrix
# ---------------------------------------------------------
@bp_pricing.route("/", methods=["GET"])
def pricing_matrix():
    periods_all = BillingPricePeriod.query.order_by(BillingPricePeriod.valid_from.desc()).all()
    periods = periods_all
    today = date.today()
    period_by_id = {p.id: p for p in periods}

    # Global: Perioden, die irgendwo Preise haben
    global_priced_period_ids = _global_priced_period_ids()

    # Valid heute + abgelaufen (für Anzeige)
    valid_today_ids: Set[int] = set()
    expired_ids: Set[int] = set()
    period_is_expired: Dict[int, bool] = {}

    for pid in global_priced_period_ids:
        p = period_by_id.get(pid)
        if not p:
            continue
        if _period_is_active_today(p, today):
            valid_today_ids.add(pid)
            period_is_expired[pid] = False
        else:
            expired_ids.add(pid)
            period_is_expired[pid] = True

    expired_periods_exist = bool(expired_ids)

    # Auswahl: Nutzer will „Arbeitsmatrix setzen“
    requested_period_id = request.args.get("period_id", type=int)

    selected_period_id: Optional[int] = None
    selected_period: Optional[BillingPricePeriod] = None

    explicit_request = requested_period_id is not None

    if requested_period_id is not None:
        p = period_by_id.get(requested_period_id)
        if not p:
            flash("Die gewählte Preismatrix existiert nicht. Bitte eine gültige Preismatrix auswählen.", "warning")
        elif requested_period_id not in global_priced_period_ids:
            flash(
                "Die gewählte Preismatrix enthält noch keine Preise. "
                "Bitte zuerst Preise pflegen oder aus einer Vorlage kopieren.",
                "warning",
            )
        else:
            selected_period_id = requested_period_id
            selected_period = p
            # Nur zeitlich gültige Matrizen dürfen als Arbeitsmatrix aktiv werden.
            if _period_is_active_today(p, today):
                session["active_pricing_model_id"] = selected_period_id
            else:
                flash(
                    f"Hinweis: „{p.name}“ ist derzeit nicht zeitlich gültig und wird nur zur Bearbeitung angezeigt.",
                    "info",
                )

    if selected_period_id is None and not explicit_request:
        # Vorrang: bereits gesetztes aktives Preismodell aus der Session beibehalten.
        session_active_id = None
        try:
            mid = session.get("active_pricing_model_id")
            session_active_id = int(mid) if mid is not None else None
        except Exception:
            session_active_id = None

        if (
            session_active_id is not None
            and session_active_id in valid_today_ids
            and session_active_id in global_priced_period_ids
        ):
            selected_period_id = session_active_id
            selected_period = period_by_id.get(session_active_id)
        # Fallback: erste zeitlich gültige Periode (global)
        elif valid_today_ids:
            for p in periods:
                if p.id in valid_today_ids:
                    selected_period_id = p.id
                    selected_period = p
                    session["active_pricing_model_id"] = selected_period_id
                    break
        else:
            flash(
                "Es gibt aktuell keine zeitlich gültige Preismatrix mit Preisen. "
                "Bitte zuerst eine Preismatrix anlegen oder kopieren.",
                "danger",
            )

    active_work_period_id: Optional[int] = None
    active_work_period: Optional[BillingPricePeriod] = None
    try:
        mid = session.get("active_pricing_model_id")
        active_work_period_id = int(mid) if mid is not None else None
    except Exception:
        active_work_period_id = None

    if (
        active_work_period_id is not None
        and active_work_period_id in valid_today_ids
        and active_work_period_id in global_priced_period_ids
    ):
        active_work_period = period_by_id.get(active_work_period_id)
    else:
        active_work_period_id = None

    no_active_matrix = selected_period_id is None

    # Matrix / Preise nur laden, wenn gesetzt
    statuses = _active_status_defs_canonical()
    matrix: Dict[str, dict] = {}
    prices_map: Dict[Tuple[str, int], BillingPrice] = {}
    used_price_keys: Set[str] = set()
    used_vat_codes: Set[str] = set()
    orga_price_locked = False
    payout_basis_inconsistencies: List[Dict[str, object]] = []

    if selected_period_id:
        prices_map = _load_prices_map(selected_period_id)
        used_price_keys = _used_price_key_tokens(selected_period_id)
        used_vat_codes = _used_vat_status_codes(selected_period_id)
        orga_price_locked = _orga_price_is_used_by_invoices(selected_period_id)
        payout_basis_inconsistencies = _find_inconsistent_ku_payout_basis(selected_period_id, statuses)
        if payout_basis_inconsistencies:
            status_labels = ", ".join(item["label"] for item in payout_basis_inconsistencies)
            flash(
                "Hinweis: Für folgende Status sind innerhalb der Periode unterschiedliche KU-Vergütungsregeln hinterlegt: "
                f"{status_labels}.",
                "warning",
            )


    codes_for_matrix = [c for c in statuses.keys() if not _is_excluded_from_jump_matrix(c)]

    # Sortierung: AFF-Lehrer unter Fallschirmsprunglehrer, Schüler-AFF-2-Lehrer unter Schüler GK 6, Schüler-AFF-1-Lehrer unter Schüler-AFF-2-Lehrer
    def move_after(code_list, code_to_move, after_code):
        move_norm = normalize_status_code(code_to_move)
        after_norm = normalize_status_code(after_code)

        move_code = next((c for c in code_list if normalize_status_code(c) == move_norm), None)
        after_ref = next((c for c in code_list if normalize_status_code(c) == after_norm), None)

        if move_code and after_ref and move_code != after_ref:
            code_list.remove(move_code)
            idx = code_list.index(after_ref) + 1
            code_list.insert(idx, move_code)

    # 1. AFF-Lehrer unter Fallschirmsprunglehrer ("Lehrer")
    move_after(codes_for_matrix, "Aff-Lehrer", "Lehrer")
    # 2. Schüler-AFF-2-Lehrer unter Schüler GK 6
    move_after(codes_for_matrix, "Schueler-Aff-2", "Schüler GK 6")
    # 3. Schüler-AFF-1-Lehrer unter Schüler-AFF-2-Lehrer
    move_after(codes_for_matrix, "Schueler-Aff-1", "Schueler-Aff-2")

    # Partner-Topup immer direkt hinter den letzten Auffüller-Status setzen.
    if PARTNER_TOPUP_CODE in codes_for_matrix:
        codes_for_matrix.remove(PARTNER_TOPUP_CODE)

    if GUEST_TOPUP_CODE in codes_for_matrix:
        idx = codes_for_matrix.index(GUEST_TOPUP_CODE) + 1
        codes_for_matrix.insert(idx, PARTNER_TOPUP_CODE)
    elif MEMBER_TOPUP_CODE in codes_for_matrix:
        idx = codes_for_matrix.index(MEMBER_TOPUP_CODE) + 1
        codes_for_matrix.insert(idx, PARTNER_TOPUP_CODE)
    else:
        codes_for_matrix.append(PARTNER_TOPUP_CODE)

    for code in codes_for_matrix:
        sd = statuses.get(code)

        if sd is not None:
            label = _clean_label(code, sd.label or code)
            vat_rate = sd.vat_rate if sd.vat_rate is not None else Decimal("0.00")
        elif code == PARTNER_TOPUP_CODE:
            label = PARTNER_TOPUP_FALLBACK_LABEL
            fallback_sd = statuses.get(MEMBER_TOPUP_CODE)
            vat_rate = (
                fallback_sd.vat_rate
                if fallback_sd is not None and fallback_sd.vat_rate is not None
                else Decimal("0.00")
            )
        else:
            label = code
            vat_rate = Decimal("0.00")

        row = {
            "code": code,
            "label": label,
            "vat_rate": vat_rate,
            "prices": {},
            "ku_credit_payout_basis": "gross",
            "shows_ku_credit_payout_basis": is_ku_credit_payout_applicable_status(code),
        }
        for h in VALID_HEIGHTS:
            bp = prices_map.get((code, int(h)))
            if bp:
                row["prices"][h] = bp.price_eur
                if row["shows_ku_credit_payout_basis"] and bp.ku_credit_payout_basis in {"gross", "net"}:
                    row["ku_credit_payout_basis"] = bp.ku_credit_payout_basis
            elif code == PARTNER_TOPUP_CODE:
                fallback_bp = prices_map.get((MEMBER_TOPUP_CODE, int(h)))
                row["prices"][h] = fallback_bp.price_eur if fallback_bp else Decimal("0.00")
                if row["shows_ku_credit_payout_basis"] and fallback_bp and fallback_bp.ku_credit_payout_basis in {"gross", "net"}:
                    row["ku_credit_payout_basis"] = fallback_bp.ku_credit_payout_basis
            else:
                row["prices"][h] = Decimal("0.00")
        matrix[code] = row

    orga_rules: Dict[str, bool] = {}
    if selected_period_id:
        rules = BillingOrgaRule.query.filter_by(period_id=selected_period_id).all()
        orga_rules = {r.status_code: bool(r.apply_orga) for r in rules}

    config = BillingConfig.query.first()
    canopy_rent = _build_canopy_rent_config(config)

    orga = {"amount": Decimal("0.00"), "mode": "period", "vat_strategy": "max_status"}
    if selected_period_id:
        orga = _load_orga_for_period(selected_period_id)

    return render_template(
        "billing/index.html",
        periods=periods,
        heights=VALID_HEIGHTS,
        selected_period_id=selected_period_id,
        selected_period=selected_period,
        active_work_period_id=active_work_period_id,
        active_work_period=active_work_period,
        matrix=matrix,
        used_price_keys=used_price_keys,
        used_vat_codes=used_vat_codes,
        orga_price_locked=orga_price_locked,
        canopy_rent=canopy_rent,
        orga=orga,
        orga_rules=orga_rules,
        priced_period_ids=global_priced_period_ids,      # alle Matrizen mit Preisen (für Bearbeitung)
        global_priced_period_ids=global_priced_period_ids,
        valid_today_ids=valid_today_ids,                 # nur aktivierbare Arbeitsmatrizen
        expired_period_ids=expired_ids,
        period_is_expired=period_is_expired,
        today=today,
        expired_warning=False,
        expired_name="",
        expired_on="",
        no_active_matrix=no_active_matrix,
        expired_periods_exist=expired_periods_exist,
    )


@bp_pricing.route("/price-list.pdf", methods=["GET"])
def price_list_pdf():
    periods = BillingPricePeriod.query.order_by(BillingPricePeriod.valid_from.desc()).all()
    global_priced_period_ids = _global_priced_period_ids()

    period_id = request.args.get("period_id", type=int)
    if period_id is None:
        try:
            mid = session.get("active_pricing_model_id")
            period_id = int(mid) if mid is not None else None
        except Exception:
            period_id = None

    if period_id is None and periods:
        for p in periods:
            if p.id in global_priced_period_ids:
                period_id = p.id
                break

    if period_id is None:
        flash("Keine Preismatrix verfuegbar fuer den PDF-Export.", "warning")
        return redirect(url_for("pricing.pricing_matrix"))

    selected_period = BillingPricePeriod.query.get(period_id)
    if not selected_period or period_id not in global_priced_period_ids:
        flash("Die gewaehlte Preismatrix enthaelt keine Preise.", "warning")
        return redirect(url_for("pricing.pricing_matrix"))

    statuses = _active_status_defs_canonical()
    prices_map = _load_prices_map(period_id)

    codes_for_matrix = [c for c in statuses.keys() if not _is_excluded_from_jump_matrix(c)]

    # Gleiche Sortierung wie pricing_matrix()-View
    def move_after(code_list, code_to_move, after_code):
        move_norm = normalize_status_code(code_to_move)
        after_norm = normalize_status_code(after_code)
        move_code = next((c for c in code_list if normalize_status_code(c) == move_norm), None)
        after_ref = next((c for c in code_list if normalize_status_code(c) == after_norm), None)
        if move_code and after_ref and move_code != after_ref:
            code_list.remove(move_code)
            idx = code_list.index(after_ref) + 1
            code_list.insert(idx, move_code)

    move_after(codes_for_matrix, "Aff-Lehrer", "Lehrer")
    move_after(codes_for_matrix, "Schueler-Aff-2", "Schüler GK 6")
    move_after(codes_for_matrix, "Schueler-Aff-1", "Schueler-Aff-2")

    if PARTNER_TOPUP_CODE in codes_for_matrix:
        codes_for_matrix.remove(PARTNER_TOPUP_CODE)
    if GUEST_TOPUP_CODE in codes_for_matrix:
        idx = codes_for_matrix.index(GUEST_TOPUP_CODE) + 1
        codes_for_matrix.insert(idx, PARTNER_TOPUP_CODE)
    elif MEMBER_TOPUP_CODE in codes_for_matrix:
        idx = codes_for_matrix.index(MEMBER_TOPUP_CODE) + 1
        codes_for_matrix.insert(idx, PARTNER_TOPUP_CODE)
    else:
        codes_for_matrix.append(PARTNER_TOPUP_CODE)

    matrix_rows: List[dict] = []
    for code in codes_for_matrix:
        sd = statuses.get(code)
        if sd is not None:
            label = _clean_label(code, sd.label or code)
            vat_rate = sd.vat_rate if sd.vat_rate is not None else Decimal("0.00")
        elif code == PARTNER_TOPUP_CODE:
            label = PARTNER_TOPUP_FALLBACK_LABEL
            fallback_sd = statuses.get(MEMBER_TOPUP_CODE)
            vat_rate = (
                fallback_sd.vat_rate
                if fallback_sd is not None and fallback_sd.vat_rate is not None
                else Decimal("0.00")
            )
        else:
            label = code
            vat_rate = Decimal("0.00")

        prices_by_height: Dict[int, Decimal] = {}
        for h in VALID_HEIGHTS:
            bp = prices_map.get((code, int(h)))
            if bp:
                prices_by_height[h] = Decimal(str(bp.price_eur or "0.00"))
            elif code == PARTNER_TOPUP_CODE:
                fallback_bp = prices_map.get((MEMBER_TOPUP_CODE, int(h)))
                prices_by_height[h] = Decimal(str((fallback_bp.price_eur if fallback_bp else Decimal("0.00")) or "0.00"))
            else:
                prices_by_height[h] = Decimal("0.00")

        matrix_rows.append(
            {
                "code": code,
                "label": label,
                "vat_rate": Decimal(str(vat_rate or "0.00")),
                "prices": prices_by_height,
            }
        )

    orga_rules = {
        r.status_code: bool(r.apply_orga)
        for r in BillingOrgaRule.query.filter_by(period_id=period_id).all()
    }

    config = BillingConfig.query.first()
    canopy_rent = _build_canopy_rent_config(config)
    orga = _load_orga_for_period(period_id)

    static_img_dir = os.path.join(current_app.root_path, "static", "img")
    logo_filename = getattr(config, "logo_filename", None) or "Head_Logo.png"
    logo_data_uri = _image_to_data_uri(os.path.join(static_img_dir, logo_filename))

    generated_at_local = now_local().replace(tzinfo=None)
    html = render_template(
        "billing/pricing_list_pdf.html",
        selected_period=selected_period,
        heights=VALID_HEIGHTS,
        matrix_rows=matrix_rows,
        orga_rules=orga_rules,
        canopy_rent=canopy_rent,
        orga=orga,
        billing_config=config,
        logo_data_uri=logo_data_uri,
        generated_at_local=generated_at_local,
    )

    try:
        from weasyprint import HTML

        pdf_bytes = HTML(string=html, base_url=current_app.root_path).write_pdf()
    except Exception:
        healed, detail = ensure_weasyprint_pdf_runtime()
        if healed:
            try:
                from weasyprint import HTML

                pdf_bytes = HTML(string=html, base_url=current_app.root_path).write_pdf()
            except Exception:
                current_app.logger.exception(
                    "PDF-Export Preisliste fehlgeschlagen trotz Selbstheilung (Detail: %s)",
                    detail,
                )
                flash(
                    "PDF konnte nicht erstellt werden. Die automatische Offline-Nachinstallation der PDF-Runtime hat nicht ausgereicht.",
                    "danger",
                )
                return redirect(url_for("pricing.pricing_matrix", period_id=period_id))
        else:
            current_app.logger.exception(
                "PDF-Export Preisliste fehlgeschlagen, Selbstheilung nicht moeglich (Detail: %s)",
                detail,
            )
            flash(
                "PDF konnte nicht erstellt werden. Die Offline-PDF-Runtime (GTK/Cairo/Pango) fehlt im Projektordner.",
                "danger",
            )
            return redirect(url_for("pricing.pricing_matrix", period_id=period_id))

    filename = (
        f"Abrechnung_Preisliste_{selected_period.name.replace(' ', '_')}_"
        f"{generated_at_local.strftime('%Y_%m_%d_%H_%M')}.pdf"
    )

    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    return response
    
# ---------------------------------------------------------
# POST: Preismatrix speichern
# VARIANTE A (GLOBAL):
# - UI ist flugplatzunabhängig
# - Preise/Regeln/Orga werden global pro Periode gespeichert
# ---------------------------------------------------------
@bp_pricing.route("/save", methods=["POST"])
def save_prices():
    # -----------------------------------------------------
    # 0) Pflichtparameter: Preisperiode
    # -----------------------------------------------------
    period_id = request.form.get("period_id", type=int)
    if not period_id:
        flash("Preisperiode erforderlich.", "danger")
        return redirect(url_for("pricing.pricing_matrix"))

    # -----------------------------------------------------
    # 1) Status-Codes aus dem Formular
    # -----------------------------------------------------
    status_codes = request.form.getlist("status_code")

    used_price_tokens: Set[str] = set()
    used_vat_codes: Set[str] = set()
    orga_is_locked = False
    locked_labels: List[str] = []
    seen_locked_labels: Set[str] = set()

    try:
        used_price_tokens = _used_price_key_tokens(period_id)
        used_vat_codes = _used_vat_status_codes(period_id)
        orga_is_locked = _orga_price_is_used_by_invoices(period_id)
    except Exception:
        # konservativ: Feldsperren nicht blockierend, falls Feld/Join noch nicht existiert
        used_price_tokens = set()
        used_vat_codes = set()
        orga_is_locked = False

    statuses = _active_status_defs_canonical()

    def _remember_locked(label: str) -> None:
        if label in seen_locked_labels:
            return
        seen_locked_labels.add(label)
        locked_labels.append(label)

    try:
        with db.session.begin_nested():

            # =================================================
            # 4) SPRUNGPREISE + MwSt
            # =================================================
            for code_raw in status_codes:
                code = normalize_status_code(code_raw)

                if _is_excluded_from_jump_matrix(code):
                    continue

                # MwSt-Satz aktualisieren (StatusDefinition)
                vat_val = _dec(request.form.get(f"vat_{code}"), default=Decimal("0.00"))
                sd = (
                    StatusDefinition.query
                    .filter_by(code=code, is_active=True)
                    .order_by(StatusDefinition.valid_from.desc())
                    .first()
                )
                old_vat = (
                    Decimal(str(sd.vat_rate))
                    if sd is not None and sd.vat_rate is not None
                    else Decimal("0.00")
                )
                if sd:
                    if vat_val != old_vat and code in used_vat_codes:
                        label = _clean_label(code, sd.label or code)
                        _remember_locked(f"MwSt für {label}")
                    else:
                        sd.vat_rate = vat_val

                # Preise je Höhe
                if is_ku_credit_payout_applicable_status(code):
                    payout_basis = (request.form.get(f"ku_credit_basis_{code}") or "gross").strip().lower()
                    if payout_basis not in {"gross", "net"}:
                        payout_basis = "gross"
                else:
                    payout_basis = "gross"

                for h in VALID_HEIGHTS:
                    price_val = _dec(
                        request.form.get(f"price_{code}_{h}"),
                        default=Decimal("0.00"),
                    )
                    token = f"{code}|{int(h)}"

                    bp = (
                        BillingPrice.query
                        .filter_by(
                            period_id=period_id,
                            status_code=code,
                            height_m=int(h),
                        )
                        .first()
                    )
                    old_price = (
                        Decimal(str(bp.price_eur))
                        if bp is not None and bp.price_eur is not None
                        else Decimal("0.00")
                    )
                    old_basis = (
                        (bp.ku_credit_payout_basis or "gross").strip().lower()
                        if bp is not None
                        else "gross"
                    )

                    is_locked_change = token in used_price_tokens and (
                        price_val != old_price or payout_basis != old_basis
                    )

                    if is_locked_change:
                        _remember_locked(_format_price_conflict_label(code, int(h), statuses))
                        continue

                    if bp:
                        bp.price_eur = price_val
                        bp.ku_credit_payout_basis = payout_basis
                    else:
                        db.session.add(
                            BillingPrice(
                                period_id=period_id,
                                status_code=code,
                                height_m=int(h),
                                price_eur=price_val,
                                ku_credit_payout_basis=payout_basis,
                            )
                        )

            # =================================================
            # 5) ORGA-CHECKBOXEN (BillingOrgaRule)
            # =================================================
            BillingOrgaRule.query.filter_by(
                period_id=period_id
            ).delete(synchronize_session=False)

            for code_raw in status_codes:
                code = normalize_status_code(code_raw)

                if _is_excluded_from_jump_matrix(code):
                    continue

                apply_orga = request.form.get(f"orga_{code}") == "1"
                db.session.add(
                    BillingOrgaRule(
                        period_id=period_id,
                        status_code=code,
                        apply_orga=apply_orga,
                    )
                )

            # =================================================
            # 6) SCHIRMMIETE (BillingConfig – global)
            # =================================================
            config = BillingConfig.query.first()
            if config:
                config.canopy_rent_member_eur = _dec(request.form.get("canopy_rent_verein_eur"))
                config.canopy_rent_member_max_count = _int(request.form.get("canopy_rent_verein_max_count"))
                config.canopy_rent_member_vat_rate = _dec(request.form.get("canopy_rent_verein_vat_rate"))

                config.canopy_rent_partner_member_eur = _dec(request.form.get("canopy_rent_partner_verein_eur"))
                config.canopy_rent_partner_member_max_count = _int(request.form.get("canopy_rent_partner_verein_max_count"))
                config.canopy_rent_partner_member_vat_rate = _dec(request.form.get("canopy_rent_partner_verein_vat_rate"))

                config.canopy_rent_guest_eur = _dec(request.form.get("canopy_rent_gast_eur"))
                config.canopy_rent_guest_max_count = _int(request.form.get("canopy_rent_gast_max_count"))
                config.canopy_rent_guest_vat_rate = _dec(request.form.get("canopy_rent_gast_vat_rate"))

                config.canopy_rent_tm_eur = _dec(request.form.get("canopy_rent_tandemmaster_eur"))
                config.canopy_rent_tm_max_count = _int(request.form.get("canopy_rent_tandemmaster_max_count"))
                config.canopy_rent_tm_vat_rate = _dec(request.form.get("canopy_rent_tandemmaster_vat_rate"))
            else:
                flash(
                    "Hinweis: Keine BillingConfig vorhanden – Schirmmiete wurde nicht gespeichert.",
                    "warning",
                )

            # =================================================
            # 7) ORGA-KONFIGURATION (billing_orga_config)
            # =================================================
            old_orga_amount = Decimal(str(_load_orga_for_period(period_id).get("amount") or "0.00"))
            orga_amount = _dec(request.form.get("orga_fee_eur"), default=Decimal("0.00"))
            orga_mode = (request.form.get("orga_fee_mode") or "period").strip()
            vat_strategy = (request.form.get("orga_fee_vat_strategy") or "max_status").strip()

            if orga_amount != old_orga_amount and orga_is_locked:
                _remember_locked("Orga – Organisationspauschale")
            else:
                _upsert_orga_cfg_db(
                    period_id=period_id,
                    amount=orga_amount,
                    mode=orga_mode,
                    vat_strategy=vat_strategy,
                )

                # Perioden-Default (Fallback)
                period = BillingPricePeriod.query.get(period_id)
                if period:
                    period.orga_fee_eur = orga_amount
                    period.orga_fee_mode = orga_mode
                    period.orga_fee_vat_strategy = vat_strategy

                # Legacy: BillingPrice(status_code="Orga", height_m=0)
                bp_orga = (
                    BillingPrice.query
                    .filter_by(
                        period_id=period_id,
                        status_code="Orga",
                        height_m=0,
                    )
                    .first()
                )
                if bp_orga:
                    bp_orga.price_eur = orga_amount
                else:
                    db.session.add(
                        BillingPrice(
                            period_id=period_id,
                            status_code="Orga",
                            height_m=0,
                            price_eur=orga_amount,
                        )
                    )

            # =================================================
            # 8) COMMIT
            # =================================================
            db.session.commit()
            if locked_labels:
                flash(
                    "Folgende bereits verwendete Felder wurden nicht gespeichert: "
                    + ", ".join(locked_labels),
                    "warning",
                )
            flash("Preismatrix gespeichert.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Fehler beim Speichern: {e}", "danger")

    return redirect(url_for("pricing.pricing_matrix", period_id=period_id))

# ---------------------------------------------------------
# POST: neue Preisperiode
# ---------------------------------------------------------
@bp_pricing.route("/period/new", methods=["POST"])
def period_new():
    name = (request.form.get("name") or "").strip()
    valid_from = (request.form.get("valid_from") or "").strip()
    valid_to = (request.form.get("valid_to") or "").strip() or None
    orga_fee_eur = (request.form.get("orga_fee_eur") or "").strip() or None
    orga_fee_mode = (request.form.get("orga_fee_mode") or "period").strip()
    orga_fee_vat_strategy = (request.form.get("orga_fee_vat_strategy") or "max_status").strip()
    is_homebase_default = bool(request.form.get("is_homebase_default"))

    if not name or not valid_from:
        flash("Name und gültig ab sind Pflicht.", "danger")
        return redirect(url_for("pricing.pricing_matrix"))

    try:
        vf = _parse_date_any(valid_from)
        vt = _parse_date_any(valid_to) if valid_to else None
    except Exception:
        flash("Datum ungültig (Format TT.MM.JJJJ oder YYYY-MM-DD).", "danger")
        return redirect(url_for("pricing.pricing_matrix"))

    try:
        period = BillingPricePeriod(
            name=name,
            valid_from=vf,
            valid_to=vt,
            is_homebase_default=is_homebase_default,
        )
        db.session.add(period)
        db.session.commit()

        # optional: Orga direkt setzen
        if orga_fee_eur is not None:
            amount = _dec(orga_fee_eur, default=Decimal("0.00"))
            _upsert_orga_cfg_db(
                period_id=period.id,
                amount=amount,
                mode=orga_fee_mode,
                vat_strategy=orga_fee_vat_strategy,
            )

        flash("Preisperiode angelegt.", "success")
        return redirect(url_for("pricing.pricing_matrix", period_id=period.id))
    except Exception as e:
        db.session.rollback()
        flash(f"Fehler beim Speichern: {e}", "danger")
        return redirect(url_for("pricing.pricing_matrix"))


# ---------------------------------------------------------
# POST – Preismatrix aus bestehender Preismatrix kopieren
# (GLOBAL: Preismatrix gilt flugplatzunabhängig)
# ---------------------------------------------------------
@bp_pricing.route("/copy-from-matrix", methods=["POST"])
def copy_from_matrix():
    # UI sendet keinen Flugplatz mehr -> target_flugplatz_id wird ignoriert
    source_period_id = request.form.get("source_period_id", type=int)

    name = (request.form.get("name") or "").strip()
    valid_from_raw = (request.form.get("valid_from") or "").strip()
    valid_to_raw = (request.form.get("valid_to") or "").strip() or None

    if not source_period_id:
        flash("Vorlage-Preismatrix fehlt.", "danger")
        return redirect(url_for("pricing.pricing_matrix"))
    if not name or not valid_from_raw:
        flash("Name und gültig ab sind Pflicht.", "danger")
        return redirect(url_for("pricing.pricing_matrix"))

    try:
        vf = _parse_date_any(valid_from_raw)
        vt = _parse_date_any(valid_to_raw) if valid_to_raw else None
    except Exception:
        flash("Datum ungültig (Format TT.MM.JJJJ oder YYYY-MM-DD).", "danger")
        return redirect(url_for("pricing.pricing_matrix"))

    # ✅ GLOBAL-MODUS: Preismatrix gilt flugplatzunabhängig

    source_period = BillingPricePeriod.query.get_or_404(source_period_id)
    _ = source_period  # sicherstellen dass die Periode existiert

    try:
        # ✅ WICHTIG: innerhalb begin_nested() KEIN db.session.commit() aufrufen!
        with db.session.begin_nested():
            new_period = BillingPricePeriod(
                name=name,
                valid_from=vf,
                valid_to=vt,
                is_homebase_default=False,
            )
            db.session.add(new_period)
            db.session.flush()

            # Preise aus der Vorlage-Periode
            src_prices = (
                BillingPrice.query
                .filter_by(period_id=source_period_id)
                .all()
            )

            # Orga-Regeln aus der Vorlage-Periode
            src_rules = (
                BillingOrgaRule.query
                .filter_by(period_id=source_period_id)
                .all()
            )

            # Orga-Config aus der Vorlage-Periode (falls vorhanden)
            src_cfg = _get_orga_cfg_db(source_period_id)

            for p in src_prices:
                db.session.add(
                    BillingPrice(
                        period_id=new_period.id,
                        status_code=p.status_code,
                        height_m=int(p.height_m),
                        price_eur=p.price_eur,
                    )
                )

            for r in src_rules:
                db.session.add(
                    BillingOrgaRule(
                        period_id=new_period.id,
                        status_code=r.status_code,
                        apply_orga=bool(r.apply_orga),
                    )
                )

            if src_cfg:
                _upsert_orga_cfg_db(
                    period_id=new_period.id,
                    amount=Decimal(str(src_cfg["amount"])),
                    mode=src_cfg["mode"],
                    vat_strategy=src_cfg["vat_strategy"],
                )

        # ✅ Erfolgs-Flash/Redirect NACH dem Context-Manager (Transaktion ist sauber abgeschlossen)
        flash("Preismatrix wurde aus Vorlage kopiert.", "success")
        return redirect(url_for("pricing.pricing_matrix", period_id=new_period.id))

    except Exception as e:
        # rollback außerhalb des Context-Managers ist ok
        db.session.rollback()
        flash(f"Fehler beim Kopieren: {e}", "danger")
        return redirect(url_for("pricing.pricing_matrix"))

# ---------------------------------------------------------
# POST: Seed (global tolerant)
# ---------------------------------------------------------
@bp_pricing.route("/seed", methods=["POST"])
def seed_prices():
    period_id = request.form.get("period_id", type=int)
    overwrite = bool(request.form.get("overwrite"))

    if not period_id:
        flash("Bitte Preisperiode auswählen.", "warning")
        return redirect(url_for("pricing.pricing_matrix"))

    period = BillingPricePeriod.query.get_or_404(period_id)

    try:
        res = PriceSeedService.seed_prices_for_period(
            period_name=period.name,
            valid_from=period.valid_from,
            valid_to=period.valid_to,
            orga_fee=period.orga_fee_eur,
            is_homebase_default=period.is_homebase_default,
            overwrite=overwrite,
        )
    except Exception as e:
        flash(f"Seed-Fehler: {e}", "danger")
        return redirect(url_for("pricing.pricing_matrix", period_id=period_id))

    created_total = int(res.get("prices_created", 0) or 0)
    updated_total = int(res.get("prices_updated", 0) or 0)

    flash(f"Seed: +{created_total} / überschrieben {updated_total}", "success")
    return redirect(url_for("pricing.pricing_matrix", period_id=period_id))


# ---------------------------------------------------------
# POST: Reset (global tolerant)
# ---------------------------------------------------------
@bp_pricing.route("/reset", methods=["POST"])
def reset_prices():
    period_id = request.form.get("period_id", type=int)

    if not period_id:
        flash("Bitte Preisperiode auswählen.", "warning")
        return redirect(url_for("pricing.pricing_matrix"))

    deleted_total = int(PriceSeedService.reset_prices_for_period(period_id=period_id) or 0)

    flash(f"{deleted_total} Preiszeilen gelöscht.", "warning")
    return redirect(url_for("pricing.pricing_matrix", period_id=period_id))


# ---------------------------------------------------------
# POST: Normalize (global tolerant)
# ---------------------------------------------------------
@bp_pricing.route("/normalize", methods=["POST"])
def normalize_prices():
    period_id = request.form.get("period_id", type=int)

    if not period_id:
        flash("Bitte Preisperiode auswählen.", "warning")
        return redirect(url_for("pricing.pricing_matrix"))

    deleted_total = 0
    updated_total = 0

    rows = (
        BillingPrice.query
        .filter_by(period_id=period_id)
        .order_by(BillingPrice.id.asc())
        .all()
    )
    groups: Dict[Tuple[str, int], List[BillingPrice]] = {}
    for r in rows:
        canon = normalize_status_code(r.status_code)
        key = (canon, int(r.height_m))
        groups.setdefault(key, []).append(r)

    with db.session.begin_nested():
        for (canon, _h), items in groups.items():
            keeper = items[-1]
            if keeper.status_code != canon:
                keeper.status_code = canon
                updated_total += 1
            for dup in items[:-1]:
                db.session.delete(dup)
                deleted_total += 1
        db.session.commit()

    flash(f"Kanonisiert: {updated_total} geändert, {deleted_total} Duplikate gelöscht.", "success")
    return redirect(url_for("pricing.pricing_matrix", period_id=period_id))


# ---------------------------------------------------------
# POST: Einzelpreis editieren (fallback) – kompatibel
# ---------------------------------------------------------
@bp_pricing.route("/price/<int:price_id>/edit", methods=["POST"])
def edit_price(price_id: int):
    p = BillingPrice.query.get_or_404(price_id)
    raw = request.form.get("price_eur") or ""
    p.price_eur = _dec(raw, default=Decimal(str(p.price_eur or "0.00")))
    try:
        db.session.commit()
        flash("Preis gespeichert.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Fehler beim Speichern: {e}", "danger")
    return redirect(url_for("pricing.pricing_matrix", period_id=p.period_id))


# ---------------------------------------------------------
# POST: Preismatrix löschen (Admin / Dev)
# ---------------------------------------------------------
@bp_pricing.route("/period/delete", methods=["POST"])
def period_delete():
    if not session.get("is_admin"):
        flash("Nur im Admin-Modus erlaubt.", "danger")
        return redirect(url_for("pricing.pricing_matrix"))

    period_id = request.form.get("period_id", type=int)
    if not period_id:
        flash("Keine Preismatrix angegeben.", "danger")
        return redirect(url_for("pricing.pricing_matrix"))

    period = BillingPricePeriod.query.get_or_404(period_id)

    try:
        BillingPrice.query.filter_by(period_id=period_id).delete(synchronize_session=False)
        BillingOrgaRule.query.filter_by(period_id=period_id).delete(synchronize_session=False)
        db.session.execute(text("DELETE FROM billing_orga_config WHERE period_id = :pid"), {"pid": period_id})
        db.session.delete(period)
        db.session.commit()
        flash(f"Preismatrix „{period.name}“ wurde gelöscht.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Fehler beim Löschen der Preismatrix: {e}", "danger")

    return redirect(url_for("pricing.pricing_matrix"))
 
    
