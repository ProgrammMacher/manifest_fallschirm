
# ...existing imports...



from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple, List, Dict, Callable, Any
from collections import defaultdict
import os  # ✅ Punkt 2.1: base_url / Pfade für WeasyPrint
import base64
import io

from flask import render_template  # ✅ Punkt 2.1: Template serverseitig rendern

from sqlalchemy.orm import joinedload
from sqlalchemy import or_, func  # ✅ FIX: für korrekten OR-Filter und case-insensitive Status-Lookups

from app import db
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.load_entry import LoadEntry
from app.models.person import Person  # (bleibt für Kompatibilität/Alt-Imports)
from app.models.load import Load
from app.models.status_definition import StatusDefinition
from app.models.billing_config import (
    BillingConfig,
    BillingPrice,
    BillingPricePeriod,
    BillingOrgaRule,  # ✅ NEU
)
from app.helpers.status_code import normalize_status_code
from app.constants import (
    STUDENT_STATUSES,
    TANDEM_GUEST_STATUSES,
    TM_STATUSES,
    VIDEO_STATUSES,
    GUEST_STATUSES,
    PARTNER_MEMBER_STATUSES,
    MEMBER_STATUSES,
    NO_RENT_STATUSES,
)

# --------------------------------------------------
# Hilfsfunktion für Bilder als Data-URIs (für PDF)
# --------------------------------------------------
def _image_to_data_uri(image_path: str) -> Optional[str]:
    """Konvertiert ein Bild zu einem data:image/...;base64,... URI."""
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        with open(image_path, "rb") as f:
            data = f.read()
        ext = os.path.splitext(image_path)[1].lower()
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(ext, "image/png")
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None


def _invoice_payment_label(payment_method: str | None) -> str:
    """Übersetzt payment_method-Code in lesbaren Label."""
    mapping = {
        "cash": "Bar",
        "card": "Karte",
        "transfer": "Überweisung",
        "wero": "WERO",
        "sepa": "SEPA-Lastschrift",
        "voucher": "Vorkasse / Gutschein",
    }
    return mapping.get((payment_method or "").strip().lower(), "")


class BillingService:

    @staticmethod
    def _find_existing_orga_invoice(person_id: int, period_id: int, mode: str, days: list):
        """
        Prüft, ob für die Person und Periode bereits eine Orga-Rechnung existiert.
        Gibt (invoice_nr, abgerechnete_tage) zurück.
        """
        from app.models.invoice import Invoice, InvoiceItem
        from sqlalchemy import and_, or_
        abgerechnete_tage = set()
        invoice_nr = None
        # Nur wirklich gespeicherte (seq_number gesetzt) und nicht stornierte Rechnungen
        invoices = Invoice.query.filter_by(person_id=person_id).filter(
            Invoice.is_deleted.is_(False),
            Invoice.seq_number.isnot(None),
        ).all()
        for inv in invoices:
            for item in inv.items:
                desc = (item.description or "")
                if desc.startswith("Organisationspauschale"):
                    # Prüfe auf Periode/Tag im Text
                    if mode == "period":
                        invoice_nr = inv.id
                        break
                    elif mode == "day":
                        for d in days:
                            tag_str = d.strftime('%d.%m.%Y')
                            if tag_str in desc:
                                abgerechnete_tage.add(tag_str)
        return invoice_nr, abgerechnete_tage

    @staticmethod
    def _get_orga_config(period_id: int):
        """
        Liefert (Betrag, Modus, Fallback-VAT) für die Orga-Pauschale einer Periode.
        """
        from app.models.billing_config import BillingPricePeriod
        period = BillingPricePeriod.query.filter_by(id=period_id).first()
        if period is None:
            # Fallback: keine Periode gefunden
            return (0, "period", 19)
        amount = float(period.orga_fee_eur or 0)
        mode = period.orga_fee_mode or "period"
        # VAT-Strategie: max_status (Standard) → 19%, sonst 7%
        vat_rate = 19 if (period.orga_fee_vat_strategy or "max_status") == "max_status" else 7
        return (amount, mode, vat_rate)

    """
    Zentrale Abrechnungslogik.

    WICHTIG (Template-Kopplung):
    - InvoiceItem.description für Sprünge MUSS mit "Sprung" beginnen
    - Schirmmiete MUSS mit "Schirmmiete" beginnen
    - Orga MUSS mit "Organisationspauschale" beginnen
    """

    MONEY = Decimal("0.01")

    # Status-Sets aus app.constants (zentral gepflegt)
    TM_STATUSES = TM_STATUSES
    VIDEO_STATUSES = VIDEO_STATUSES
    GUEST_STATUSES = GUEST_STATUSES
    PARTNER_MEMBER_STATUSES = PARTNER_MEMBER_STATUSES
    MEMBER_STATUSES = MEMBER_STATUSES
    NO_RENT_STATUSES = NO_RENT_STATUSES

    # ---------------------------------------------------------
    # Helper: Rundung
    # ---------------------------------------------------------
    @staticmethod
    def _q2(x: Decimal) -> Decimal:
        return Decimal(str(x or "0.00")).quantize(
            BillingService.MONEY, rounding=ROUND_HALF_UP
        )

    @staticmethod
    def _is_tandemmaster_jump_entry(entry: LoadEntry | None) -> bool:
        if not entry:
            return False
        code = normalize_status_code(getattr(entry, "status_code", "") or "")
        return code in BillingService.TM_STATUSES

    @staticmethod
    def _is_video_jump_entry(entry: LoadEntry | None) -> bool:
        if not entry:
            return False
        code = normalize_status_code(getattr(entry, "status_code", "") or "")
        return code in BillingService.VIDEO_STATUSES

    @staticmethod
    def _is_ku_eligible_jump_entry(entry: LoadEntry | None) -> bool:
        return (
            BillingService._is_tandemmaster_jump_entry(entry)
            or BillingService._is_video_jump_entry(entry)
        )

    @staticmethod
    def _is_tandemmaster_jump_item(item: InvoiceItem | None) -> bool:
        if not item:
            return False
        desc = (getattr(item, "description", "") or "").strip()
        if not desc.startswith("Sprung"):
            return False
        return BillingService._is_tandemmaster_jump_entry(getattr(item, "load_entry", None))

    @staticmethod
    def _is_video_jump_item(item: InvoiceItem | None) -> bool:
        if not item:
            return False
        desc = (getattr(item, "description", "") or "").strip()
        if not desc.startswith("Sprung"):
            return False
        return BillingService._is_video_jump_entry(getattr(item, "load_entry", None))

    @staticmethod
    def _is_aff_teacher_jump_entry(entry: LoadEntry | None) -> bool:
        if not entry:
            return False
        return normalize_status_code(getattr(entry, "status_code", "") or "") == "Aff-Lehrer"

    @staticmethod
    def _is_aff_teacher_jump_item(item: InvoiceItem | None) -> bool:
        if not item:
            return False
        desc = (getattr(item, "description", "") or "").strip()
        if not desc.startswith("Sprung"):
            return False
        return BillingService._is_aff_teacher_jump_entry(getattr(item, "load_entry", None))

    @staticmethod
    def _is_ku_eligible_jump_item(item: InvoiceItem | None) -> bool:
        return (
            BillingService._is_tandemmaster_jump_item(item)
            or BillingService._is_video_jump_item(item)
            or BillingService._is_aff_teacher_jump_item(item)
        )

    @staticmethod
    def get_jump_item_calculation(
        *,
        entry: LoadEntry | None,
        ku_active_for_entry: bool,
        fallback_gross: Decimal | None = None,
    ) -> Dict[str, Any]:
        """Berechnet den effektiven Betrag, MwSt und KU-Gutschriftsdaten für eine Sprungposition."""
        gross = BillingService._q2(BillingService.calculate_price_for_entry(entry)) if entry else Decimal("0.00")
        if gross == 0 and fallback_gross is not None:
            gross = BillingService._q2(fallback_gross)

        if ku_active_for_entry:
            vat_rate = Decimal("0.00")
            payout_basis = BillingService.get_ku_credit_payout_basis_for_entry(entry=entry)
            payout_amount = BillingService.get_ku_credit_payout_amount_for_entry(
                entry=entry,
                fallback_gross=gross,
            )
            effective_amount = BillingService._q2(payout_amount if payout_amount is not None else gross)
            price_source_eur = BillingService._q2(BillingService.calculate_price_for_entry(entry)) if entry else Decimal("0.00")
            price_source_vat_rate = BillingService._q2(BillingService.get_entry_vat_rate(entry)) if entry else Decimal("0.00")
        else:
            vat_rate = BillingService._q2(BillingService.get_entry_vat_rate(entry)) if entry else Decimal("0.00")
            payout_basis = None
            payout_amount = None
            effective_amount = gross
            price_source_eur = None
            price_source_vat_rate = None

        net, vat = BillingService.split_gross_into_net_and_vat(gross=effective_amount, vat_rate=vat_rate)
        return {
            "gross": gross,
            "effective_amount": effective_amount,
            "vat_rate": vat_rate,
            "net": net,
            "vat": vat,
            "payout_basis": payout_basis,
            "payout_amount": payout_amount,
            "price_source_eur": price_source_eur,
            "price_source_vat_rate": price_source_vat_rate,
        }

    @staticmethod
    def recalculate_invoice_tandemmaster_tax(invoice: Invoice) -> None:
        """
        Wendet §19 UStG ausschließlich auf Tandemmaster-Sprungpositionen an.
        Alle anderen Positionen bleiben unverändert.
        """
        is_kleinunternehmer = bool(getattr(invoice, "is_tandem_kleinunternehmer", False))

        for item in list(getattr(invoice, "items", []) or []):
            if not BillingService._is_tandemmaster_jump_item(item):
                continue

            gross = BillingService._q2(Decimal(str(getattr(item, "amount", 0) or "0.00")))
            if is_kleinunternehmer:
                vat_rate = Decimal("0.00")
            else:
                vat_rate = BillingService._q2(
                    BillingService.get_entry_vat_rate(getattr(item, "load_entry", None))
                )

            net, vat = BillingService.split_gross_into_net_and_vat(gross=gross, vat_rate=vat_rate)
            item.vat_rate = vat_rate
            item.net_amount = net
            item.vat_amount = vat

        invoice.calculate_total()

    @staticmethod
    def recalculate_invoice_ku_tax(invoice: Invoice) -> None:
        """
        Wendet §19 UStG ausschließlich auf ku-fähige Sprungpositionen an
        (Tandemmaster + Video). Alle anderen Positionen bleiben unverändert.
        """
        is_tandem_ku = bool(getattr(invoice, "is_tandem_kleinunternehmer", False))
        is_video_ku = bool(getattr(invoice, "is_video_kleinunternehmer", False))
        is_aff_teacher_ku = bool(getattr(invoice, "is_aff_teacher_kleinunternehmer", False))

        for item in list(getattr(invoice, "items", []) or []):
            if not BillingService._is_ku_eligible_jump_item(item):
                continue

            entry = getattr(item, "load_entry", None)
            is_tandem_item = BillingService._is_tandemmaster_jump_entry(entry)
            is_video_item = BillingService._is_video_jump_entry(entry)
            is_aff_teacher_item = BillingService._is_aff_teacher_jump_entry(entry)
            ku_active_for_item = (
                (is_tandem_item and is_tandem_ku)
                or (is_video_item and is_video_ku)
                or (is_aff_teacher_item and is_aff_teacher_ku)
            )

            gross = BillingService._q2(Decimal(str(getattr(item, "amount", 0) or "0.00")))
            calc = BillingService.get_jump_item_calculation(
                entry=entry,
                ku_active_for_entry=ku_active_for_item,
                fallback_gross=gross,
            )
            if ku_active_for_item:
                item.amount = calc["effective_amount"]
                item.ku_credit_payout_basis = calc["payout_basis"]
                item.ku_credit_payout_amount = calc["payout_amount"]
                item.price_source_eur = calc["price_source_eur"]
                item.price_source_vat_rate = calc["price_source_vat_rate"]
            else:
                item.amount = calc["effective_amount"]
                item.ku_credit_payout_basis = None
                item.ku_credit_payout_amount = None
                item.price_source_eur = None
                item.price_source_vat_rate = None

            item.vat_rate = calc["vat_rate"]
            item.net_amount = calc["net"]
            item.vat_amount = calc["vat"]

        invoice.calculate_total()

    # ---------------------------------------------------------
    # Helper: Brutto -> Netto/MwSt
    # ---------------------------------------------------------
    @staticmethod
    def split_gross_into_net_and_vat(
        *, gross: Decimal, vat_rate: Decimal
    ) -> Tuple[Decimal, Decimal]:
        gross = Decimal(str(gross or "0.00"))
        vat_rate = Decimal(str(vat_rate or "0.00"))

        if vat_rate <= 0:
            net = BillingService._q2(gross)
            vat = BillingService._q2(Decimal("0.00"))
            return net, vat

        factor = Decimal("1.00") + (vat_rate / Decimal("100.00"))
        net = BillingService._q2(gross / factor)
        vat = BillingService._q2(gross - net)
        return net, vat

    # ---------------------------------------------------------
    # MwSt-Satz für einen Entry bestimmen
    # ---------------------------------------------------------
    @staticmethod
    def get_entry_vat_rate(entry: LoadEntry) -> Decimal:
        # 1) Prefer eager-loaded relationship if present
        if getattr(entry, "status_definition", None) and entry.status_definition.vat_rate is not None:
            return Decimal(str(entry.status_definition.vat_rate))

        # 2) Fallback: query active status definition by canonical code first
        code = normalize_status_code(getattr(entry, "status_code", "") or "")
        sd = None
        if code:
            sd = (
                StatusDefinition.query
                .filter_by(code=code, is_active=True)
                .order_by(StatusDefinition.valid_from.desc())
                .first()
            )

        # 3) Fallback: also resolve case-insensitive / variant matches
        if not sd and code:
            sd = (
                StatusDefinition.query
                .filter(StatusDefinition.code.is_not(None), StatusDefinition.code != "")
                .filter(StatusDefinition.is_active.is_(True))
                .filter(func.upper(StatusDefinition.code) == func.upper(code))
                .order_by(StatusDefinition.valid_from.desc())
                .first()
            )

        # 4) Fallback: direct raw-code lookup for legacy rows
        if not sd:
            raw_code = getattr(entry, "status_code", "") or ""
            if raw_code:
                sd = (
                    StatusDefinition.query
                    .filter(StatusDefinition.code.is_not(None), StatusDefinition.code != "")
                    .filter(StatusDefinition.is_active.is_(True))
                    .filter(func.upper(StatusDefinition.code) == func.upper(raw_code))
                    .order_by(StatusDefinition.valid_from.desc())
                    .first()
                )

        if sd and sd.vat_rate is not None:
            return Decimal(str(sd.vat_rate))

        return Decimal("0.00")

    # ---------------------------------------------------------
    # Globale Konfiguration
    # ---------------------------------------------------------
    @staticmethod
    def get_global_config() -> BillingConfig:
        config = BillingConfig.query.first()
        if not config:
            raise RuntimeError("Keine BillingConfig vorhanden.")
        return config

    # ---------------------------------------------------------
    # Aktive Preisperiode (FIX: korrektes ODER)
    # ---------------------------------------------------------
    @staticmethod
    def get_active_price_period(
        *, day: date
    ) -> Optional[BillingPricePeriod]:
        """Liefert die zeitlich passende Preisperiode, die Preise enthält."""
        periods = (
            BillingPricePeriod.query
            .filter(BillingPricePeriod.valid_from <= day)
            .filter(or_(
                BillingPricePeriod.valid_to.is_(None),
                BillingPricePeriod.valid_to >= day
            ))
            .order_by(BillingPricePeriod.valid_from.desc())
            .all()
        )

        for period in periods:
            exists = BillingPrice.query.filter_by(period_id=period.id).first()
            if exists:
                return period

        return None

    # ---------------------------------------------------------
    # Preis für einen Sprung
    # ---------------------------------------------------------
    @staticmethod
    def get_price_for_jump(
        *, period: BillingPricePeriod, status_code: str, height_m: int
    ) -> Decimal:
        """Liefert den Bruttopreis für einen Sprung aus der globalen Preismatrix."""
        price = (
            BillingPrice.query
            .filter_by(
                period_id=period.id,
                status_code=status_code,
                height_m=height_m,
            )
            .first()
        )
        return Decimal(str(price.price_eur)) if price else Decimal("0.00")

    @staticmethod
    def get_ku_credit_payout_basis_for_entry(
        *, entry: LoadEntry, period: Optional[BillingPricePeriod] = None
    ) -> str:
        """Liefert die für Kleinunternehmer-Gutschriften verwendete Basis für einen Entry."""
        if not entry:
            return "gross"

        code = normalize_status_code(getattr(entry, "status_code", "") or "")
        if code not in {"TD", "TD-Vereins-Schirm", "Video", "Aff-Lehrer"}:
            return "gross"

        period_obj = period
        if period_obj is None:
            load = getattr(entry, "load", None)
            if not load:
                return "gross"
            model_id = getattr(load, "pricing_model_id", None)
            if model_id:
                period_obj = BillingPricePeriod.query.get(int(model_id))
            else:
                dt = (
                    getattr(load, "actual_time", None)
                    or getattr(load, "scheduled_time", None)
                    or getattr(load, "created_at", None)
                    or getattr(entry, "created_at", None)
                    or datetime.utcnow()
                )
                period_obj = BillingService.get_active_price_period(day=dt.date())

        if not period_obj:
            return "gross"

        price_row = (
            BillingPrice.query
            .filter_by(
                period_id=period_obj.id,
                status_code=code,
                height_m=int(getattr(entry, "height_m", 0) or 0),
            )
            .first()
        )
        basis = getattr(price_row, "ku_credit_payout_basis", None) or "gross"
        return str(basis).strip().lower() if str(basis).strip().lower() in {"gross", "net"} else "gross"

    @staticmethod
    def get_ku_credit_payout_amount_for_entry(
        *, entry: LoadEntry, period: Optional[BillingPricePeriod] = None, fallback_gross: Decimal | None = None
    ) -> Decimal:
        """Liefert den für eine Kleinunternehmer-Gutschrift auszuzahlenden Betrag."""
        gross = BillingService._q2(BillingService.calculate_price_for_entry(entry))
        if gross == 0 and fallback_gross is not None:
            gross = BillingService._q2(fallback_gross)
        vat_rate = BillingService._q2(BillingService.get_entry_vat_rate(entry))
        basis = BillingService.get_ku_credit_payout_basis_for_entry(entry=entry, period=period)
        if basis == "net":
            if vat_rate <= 0:
                return gross
            factor = Decimal("1.00") + (vat_rate / Decimal("100.00"))
            return BillingService._q2(gross / factor)
        return gross

    # ---------------------------------------------------------
    # Preisermittlung für LoadEntry
    # ---------------------------------------------------------
    @staticmethod
    def calculate_price_for_entry(entry: LoadEntry) -> Decimal:
        """
        Preisermittlung für einen einzelnen LoadEntry.

        - Primär: über fest am Load gespeichertes Preismodell (pricing_model_id).
        - Fallback: zeitlich gültige Periode am Tag des Loads (Legacy-Altbestände).
        """
        load = getattr(entry, "load", None)
        if not load:
            return Decimal("0.00")

        # Tag aus Load-Zeit ableiten (Fachregel: actual_time primär)
        dt = (
            getattr(load, "actual_time", None)
            or getattr(load, "scheduled_time", None)
            or getattr(load, "created_at", None)
            or getattr(entry, "created_at", None)
            or datetime.utcnow()
        )
        day = dt.date()

        # ✅ Primär: fest gebundenes Preismodell am Load
        model_id = getattr(load, "pricing_model_id", None)
        if model_id:
            period = BillingPricePeriod.query.get(int(model_id))
        else:
            # ✅ Fallback für Altbestände
            period = BillingService.get_active_price_period(day=day)

        if not period:
            return Decimal("0.00")

        # ✅ Statuscode kanonisieren (Preismatrix speichert canonical codes)
        code = normalize_status_code(getattr(entry, "status_code", "") or "")

        return BillingService.get_price_for_jump(
            period=period,
            status_code=code,
            height_m=int(getattr(entry, "height_m", 0) or 0),
        )

    # ---------------------------------------------------------
    # Offene Entries
    # ---------------------------------------------------------
    @staticmethod
    def get_open_entries_for_person(person_id: int):
        return (
            LoadEntry.query
            .join(LoadEntry.load)  # ✅ verbindet LoadEntry -> Load
            .options(
                joinedload(LoadEntry.load),
                joinedload(LoadEntry.person),
                joinedload(LoadEntry.status_definition),
            )
            .filter(
                LoadEntry.person_id == person_id,
                LoadEntry.billed.is_(False),
                Load.status == "completed",  # ✅ Fachregel
            )
            .order_by(LoadEntry.created_at.asc())
            .all()
        )

    # =========================================================
    # Schirmmiete (unverändert)
    # =========================================================
    @staticmethod
    def _entry_day(entry: LoadEntry) -> date:
        # Fachregel: actual_time primär, scheduled_time nur Legacy-Fallback
        ld = getattr(entry, "load", None)
        dt = None
        if ld:
            dt = getattr(ld, "actual_time", None) or getattr(ld, "scheduled_time", None) or getattr(ld, "created_at", None)
        return (dt or getattr(entry, "created_at", None) or datetime.utcnow()).date()

    @staticmethod
    def _rent_category_from_status(status_code: str) -> Optional[str]:
        status = normalize_status_code(status_code or "")
        if status in BillingService.TM_STATUSES:
            return "tm"
        if status in BillingService.GUEST_STATUSES:
            return "guest"
        if status in BillingService.PARTNER_MEMBER_STATUSES:
            return "partner_member"
        if status in BillingService.MEMBER_STATUSES:
            return "member"
        return None

    @staticmethod
    def _rent_category_label(
        category: str,
        *,
        has_partner_member: bool = False,
        has_non_partner_member: bool = False,
    ) -> str:
        if category == "tm":
            return "Tandemmaster"
        if category == "guest":
            return "Gast"
        if category == "partner_member":
            return "Partner-Verein"
        if category == "member":
            if has_partner_member and not has_non_partner_member:
                return "Partner-Verein"
            if has_non_partner_member and not has_partner_member:
                return "Verein"
            return "Verein/Partner-Verein"
        return category

    @staticmethod
    def _is_rent_eligible(entry: LoadEntry) -> bool:
        if not getattr(entry, "gear_rental", False):
            return False
        status = normalize_status_code(getattr(entry, "status_code", "") or "")
        if status in BillingService.NO_RENT_STATUSES:
            return False
        return BillingService._rent_category_from_status(status) is not None

    @staticmethod
    def _rent_params(category: str, config: BillingConfig) -> Tuple[Decimal, int, Decimal]:
        if category == "member":
            return (
                Decimal(str(config.canopy_rent_member_eur)),
                int(config.canopy_rent_member_max_count or 0),
                Decimal(str(config.canopy_rent_member_vat_rate)),
            )
        if category == "partner_member":
            return (
                Decimal(str(getattr(config, "canopy_rent_partner_member_eur", config.canopy_rent_member_eur))),
                int(getattr(config, "canopy_rent_partner_member_max_count", config.canopy_rent_member_max_count) or 0),
                Decimal(str(getattr(config, "canopy_rent_partner_member_vat_rate", config.canopy_rent_member_vat_rate))),
            )
        if category == "guest":
            return (
                Decimal(str(config.canopy_rent_guest_eur)),
                int(config.canopy_rent_guest_max_count or 0),
                Decimal(str(config.canopy_rent_guest_vat_rate)),
            )
        if category == "tm":
            return (
                Decimal(str(config.canopy_rent_tm_eur)),
                int(config.canopy_rent_tm_max_count or 0),
                Decimal(str(config.canopy_rent_tm_vat_rate)),
            )
        return Decimal("0.00"), 0, Decimal("0.00")

    @staticmethod
    def compute_extras_for_entries(
        entries: List[LoadEntry],
        *,
        entry_matches: Optional[Callable[[LoadEntry], bool]] = None,
        include_rental_items: bool = False,
        include_orga_items: bool = False,
    ) -> Dict[str, Any]:
        """
        Zentrale Berechnung für Zusatzpositionen (Schirmmiete + Orga).
        Kann von Abrechnung und Statistik mit unterschiedlicher Datenbasis genutzt werden.
        """
        def _money(v) -> Decimal:
            try:
                return BillingService._q2(Decimal(str(v or "0.00")))
            except Exception:
                return Decimal("0.00")

        filtered_entries: List[LoadEntry] = []
        for e in (entries or []):
            if not e:
                continue
            if entry_matches is not None:
                try:
                    if not entry_matches(e):
                        continue
                except Exception:
                    continue
            filtered_entries.append(e)

        rental_items: List[Dict[str, Any]] = []
        orga_items: List[Dict[str, Any]] = []

        rental_sum_gross = Decimal("0.00")
        rental_sum_net = Decimal("0.00")
        rental_sum_vat = Decimal("0.00")

        orga_sum_gross = Decimal("0.00")
        orga_sum_net = Decimal("0.00")
        orga_sum_vat = Decimal("0.00")

        try:
            config = BillingService.get_global_config()
        except Exception:
            config = None

        # --- Schirmmiete: pro Tag/Kategorie mit max_count-Cap ---
        if config:
            rent_counts: Dict[Tuple[date, str], int] = defaultdict(int)
            for e in filtered_entries:
                try:
                    if not BillingService._is_rent_eligible(e):
                        continue
                    cat = BillingService._rent_category_from_status(getattr(e, "status_code", None))
                    if not cat:
                        continue
                    day_key = BillingService._entry_day(e)
                    rent_counts[(day_key, cat)] += 1
                except Exception:
                    continue

            for (day_key, cat), count in rent_counts.items():
                try:
                    price, max_count, vat_rate = BillingService._rent_params(cat, config)
                except Exception:
                    continue

                max_count_int = None
                try:
                    max_count_int = int(max_count) if max_count is not None else None
                except Exception:
                    max_count_int = None

                charged = min(count, max_count_int) if max_count_int and max_count_int > 0 else count
                if charged <= 0:
                    continue

                try:
                    gross = BillingService._q2(_money(price) * Decimal(charged))
                    net, vat = BillingService.split_gross_into_net_and_vat(
                        gross=gross,
                        vat_rate=_money(vat_rate),
                    )
                except Exception:
                    gross = net = vat = Decimal("0.00")

                rental_sum_gross += gross
                rental_sum_net += net
                rental_sum_vat += vat

                if include_rental_items:
                    price_str = (
                        "{:,.2f}".format(_money(price))
                        .replace(",", "X")
                        .replace(".", ",")
                        .replace("X", ".")
                    )
                    day_label = day_key.strftime("%Y-%m-%d")
                    # Personen für diese Schirmmiete-Position sammeln
                    person_names = []
                    for e in filtered_entries:
                        try:
                            cat_e = BillingService._rent_category_from_status(getattr(e, "status_code", None))
                            day_e = BillingService._entry_day(e)
                            if cat_e == cat and day_e == day_key:
                                person = getattr(e, "person", None)
                                if person:
                                    name = f"{getattr(person, 'last_name', '')} {getattr(person, 'first_name', '')}".strip()
                                else:
                                    name = f"Person #{getattr(e, 'person_id', '')}"
                                if name and name not in person_names:
                                    person_names.append(name)
                        except Exception:
                            continue
                    person_str = ", ".join(person_names)
                    desc = f"Schirmmiete {cat} am {day_label} ({charged} × {price_str})"
                    if person_str:
                        desc += f" — {person_str}"
                    # Datum und Flugplatz aus den zugehörigen Einträgen bestimmen (erster Treffer)
                    date_val = None
                    airfield_val = ""
                    person_id_val = None
                    for e in filtered_entries:
                        try:
                            cat_e = BillingService._rent_category_from_status(getattr(e, "status_code", None))
                            day_e = BillingService._entry_day(e)
                            if cat_e == cat and day_e == day_key:
                                if not date_val:
                                    date_val = day_e
                                ld = getattr(e, "load", None)
                                if ld and not airfield_val:
                                    airfield_val = getattr(getattr(ld, "airfield", None), "name", "")
                                if person_id_val is None:
                                    person_id_val = getattr(e, "person_id", None)
                        except Exception:
                            continue
                    rental_items.append({
                        "date": date_val,
                        "time": "",  # Uhrzeit entfällt
                        "load_id": None,
                        "load_number": "",
                        "airfield": airfield_val,
                        "person_id": person_id_val,
                        "person_name": person_str,
                        "desc": desc,
                        "gross": gross,
                        "net": net,
                        "vat": vat,
                        "vat_rate": _money(vat_rate),
                        "item_type": "Schirmmiete",
                    })

        # --- Orga: pro Person + Periode, mit Merge identischer Konfiguration ---
        by_person: Dict[int, List[LoadEntry]] = defaultdict(list)
        for e in filtered_entries:
            person_id = getattr(e, "person_id", None)
            if not person_id:
                continue
            by_person[int(person_id)].append(e)

        for person_id, entries_for_person in by_person.items():
            if not entries_for_person:
                continue

            ctx_map: Dict[int, List[LoadEntry]] = defaultdict(list)
            for e in entries_for_person:
                ld = getattr(e, "load", None)
                if not ld:
                    continue

                model_id = getattr(ld, "pricing_model_id", None)
                try:
                    pid = int(model_id) if model_id else None
                except Exception:
                    pid = None

                if pid is None:
                    try:
                        d0 = BillingService._entry_day(e)
                        p0 = BillingService.get_active_price_period(day=d0)
                        pid = p0.id if p0 else None
                    except Exception:
                        pid = None

                if pid is None:
                    continue

                ctx_map[int(pid)].append(e)

            orga_merged: Dict[Tuple[Decimal, str], List[Any]] = {}
            for pid, entries_ctx in ctx_map.items():
                try:
                    amount_raw, mode_raw, _ = BillingService._get_orga_config(period_id=pid)
                except Exception:
                    continue

                merge_key = (_money(amount_raw), str(mode_raw or "period"))
                if merge_key not in orga_merged:
                    orga_merged[merge_key] = [pid, list(entries_ctx)]
                else:
                    orga_merged[merge_key][1].extend(entries_ctx)
                    if pid > orga_merged[merge_key][0]:
                        orga_merged[merge_key][0] = pid

            for (amount_gross, mode_raw), orga_data in orga_merged.items():
                pid = int(orga_data[0])
                entries_ctx = list(orga_data[1] or [])
                if amount_gross <= 0 or not entries_ctx:
                    continue

                try:
                    _, _, fallback_vat_rate = BillingService._get_orga_config(period_id=pid)
                except Exception:
                    fallback_vat_rate = Decimal("0.00")

                try:
                    rules = BillingOrgaRule.query.filter_by(period_id=pid).all()
                    rules_map = {r.status_code: bool(r.apply_orga) for r in rules}
                except Exception:
                    rules_map = {}

                relevant: List[LoadEntry] = []
                for x in entries_ctx:
                    code = normalize_status_code(getattr(x, "status_code", "") or "")
                    if rules_map.get(code, True):
                        relevant.append(x)
                if not relevant:
                    continue

                mode_s = str(mode_raw or "period").lower()
                if mode_s == "day":
                    days = {BillingService._entry_day(x) for x in relevant}
                    count = len(days)
                    orga_calc_label = "Pauschale pro Tag"
                else:
                    count = 1
                    orga_calc_label = "Pauschale pro Periode"

                if count <= 0:
                    continue

                vat_rates = []
                for x in relevant:
                    try:
                        vat_rates.append(_money(BillingService.get_entry_vat_rate(x)))
                    except Exception:
                        pass

                vat_rate = max(vat_rates) if vat_rates else _money(fallback_vat_rate)
                net_single, vat_single = BillingService.split_gross_into_net_and_vat(
                    gross=amount_gross,
                    vat_rate=vat_rate,
                )

                orga_gross_total = amount_gross * Decimal(count)
                orga_net_total = net_single * Decimal(count)
                orga_vat_total = vat_single * Decimal(count)

                orga_sum_gross += orga_gross_total
                orga_sum_net += orga_net_total
                orga_sum_vat += orga_vat_total

                if include_orga_items:
                    person = relevant[0].person if relevant else None
                    person_name = (
                        f"{getattr(person, 'last_name', '')} {getattr(person, 'first_name', '')}"
                        if person
                        else f"Person #{person_id}"
                    )

                    # Datum und Flugplatz aus erstem relevanten Eintrag bestimmen
                    date_val = None
                    airfield_val = ""
                    for e in relevant:
                        try:
                            date_val = BillingService._entry_day(e)
                            ld = getattr(e, "load", None)
                            if ld:
                                airfield_val = getattr(getattr(ld, "airfield", None), "name", "")
                            break
                        except Exception:
                            continue
                    orga_items.append({
                        "date": date_val,
                        "time": "",  # Uhrzeit entfällt
                        "load_number": "",
                        "airfield": airfield_val,
                        "person_id": person_id,
                        "person_name": person_name,
                        "desc": f"Organisationspauschale ({orga_calc_label}) — {person_name}",
                        "gross": orga_gross_total,
                        "net": orga_net_total,
                        "vat": orga_vat_total,
                        "vat_rate": vat_rate,
                        "item_type": "Orga",
                    })

        rental_items.sort(key=lambda r: (r.get("date") or datetime.min, r.get("time") or ""))
        orga_items.sort(key=lambda r: (r.get("date") or datetime.min, r.get("time") or ""))

        return {
            "rental_items": rental_items,
            "orga_items": orga_items,
            "rental_sum_net": rental_sum_net,
            "rental_sum_vat": rental_sum_vat,
            "rental_sum_gross": rental_sum_gross,
            "orga_sum_net": orga_sum_net,
            "orga_sum_vat": orga_sum_vat,
            "orga_sum_gross": orga_sum_gross,
        }

    # =========================================================
    # ORGA (statusbasierte MwSt, ohne Funktionsverlust)
    # =========================================================
    @staticmethod

    def _add_orga_items(*, invoice: Invoice, entries: list, period_id: int):
        """
        Orga als eigene InvoiceItem-Zeile(n). Gilt global pro Periode.
        """
        amount, mode, fallback_vat_rate = BillingService._get_orga_config(period_id=period_id)
        if amount <= 0:
            return

        # Orga-Regeln laden
        rules = (
            BillingOrgaRule.query
            .filter_by(period_id=period_id)
            .all()
        )
        rules_map = {r.status_code: bool(r.apply_orga) for r in rules}

        def _is_orga_relevant(e: LoadEntry) -> bool:
            code = normalize_status_code(getattr(e, "status_code", "") or "")
            return rules_map.get(code, True)

        relevant_entries = [e for e in entries if _is_orga_relevant(e)]
        if not relevant_entries:
            return

        rep_entry_id = relevant_entries[0].id if relevant_entries else None
        if not rep_entry_id:
            return

        vat_rates = [BillingService.get_entry_vat_rate(e) for e in relevant_entries]
        vat_rate = max(vat_rates) if vat_rates else fallback_vat_rate
        days = sorted({BillingService._entry_day(e) for e in relevant_entries})

        person_id = relevant_entries[0].person_id if relevant_entries else None
        if not person_id:
            return

        # --- NEU: Prüfen, ob Orga schon abgerechnet wurde ---
        invoice_nr, abgerechnete_tage = BillingService._find_existing_orga_invoice(person_id, period_id, mode, days)

        def _add(desc: str, betrag: float = None, note: str = None):
            betrag = amount if betrag is None else betrag
            net, vat = BillingService.split_gross_into_net_and_vat(gross=betrag, vat_rate=vat_rate)
            db.session.add(
                InvoiceItem(
                    invoice_id=invoice.id,
                    load_entry_id=rep_entry_id,
                    amount=betrag,
                    vat_rate=vat_rate,
                    net_amount=net,
                    vat_amount=vat,
                    description=desc if not note else f"{desc} – bereits in Rechnung #{invoice_nr} enthalten",
                )
            )


        if mode == "period":
            if invoice_nr:
                # Orga wurde schon abgerechnet: Nur eine Hinweiszeile mit 0 € erzeugen, keine Duplikate
                day_count = len(days)
                if day_count > 1:
                    detail = f"(Zeitraum über {day_count} Tage)"
                elif day_count == 1:
                    detail = "(Zeitraum über 1 Tag)"
                else:
                    detail = "(Zeitraum)"
                # Prüfe, ob schon eine Hinweiszeile für diesen Zeitraum existiert
                existing_hints = [item for item in invoice.items if item.description and f"Organisationspauschale {detail}" in item.description and "bereits in Rechnung" in item.description]
                if not existing_hints:
                    _add(f"Organisationspauschale {detail}", betrag=0, note="hinweis")
                return  # KEINE weitere Orga-Position mit Betrag!
            else:
                # Orga normal abrechnen
                day_count = len(days)
                if day_count > 1:
                    detail = f"(Zeitraum über {day_count} Tage)"
                elif day_count == 1:
                    detail = "(Zeitraum über 1 Tag)"
                else:
                    detail = "(Zeitraum)"
                _add(f"Organisationspauschale {detail}")

        elif mode == "day":
            amount_str = (
                "{:,.2f}".format(amount)
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
            for d in days:
                tag_str = d.strftime('%d.%m.%Y')
                if tag_str in abgerechnete_tage:
                    _add(f"Organisationspauschale {tag_str} (1 × {amount_str})", betrag=0, note="hinweis")
                else:
                    _add(f"Organisationspauschale {tag_str} (1 × {amount_str})")
        else:
            # Fallback auf period
            if invoice_nr:
                day_count = len(days)
                if day_count > 1:
                    detail = f"(Zeitraum über {day_count} Tage)"
                elif day_count == 1:
                    detail = "(Zeitraum über 1 Tag)"
                else:
                    detail = "(Zeitraum)"
                _add(f"Organisationspauschale {detail}", betrag=0, note="hinweis")
            else:
                day_count = len(days)
                if day_count > 1:
                    detail = f"(Zeitraum über {day_count} Tage)"
                elif day_count == 1:
                    detail = "(Zeitraum über 1 Tag)"
                else:
                    detail = "(Zeitraum)"
                _add(f"Organisationspauschale {detail}")



    # =========================================================
    # INTERNAL REFACTOR HELPERS
    # =========================================================
    @staticmethod
    def _mark_entry_billed(entry: LoadEntry, gross: Decimal) -> None:
        """
        Kompatibler billed-Marker:
        - bevorzugt entry.mark_billed(price=...)
        - Fallback: entry.billed = True
        """
        try:
            if hasattr(entry, "mark_billed"):
                entry.mark_billed(price=float(gross))
            elif hasattr(entry, "billed"):
                entry.billed = True
        except Exception:
            # Billing darf nicht crashen; billed-Flag ist sekundär.
            pass

    @staticmethod
    def _add_jump_items(
        invoice: Invoice,
        entries: List[LoadEntry],
        *,
        mark_billed: bool
    ) -> None:
        """
        Sprungpositionen (1:1 Logik, zentralisiert).
        """
        for entry in entries:
            gross = BillingService._q2(
                BillingService.calculate_price_for_entry(entry)
            )
            ku_active_for_entry = (
                (bool(getattr(invoice, "is_tandem_kleinunternehmer", False)) and BillingService._is_tandemmaster_jump_entry(entry))
                or (bool(getattr(invoice, "is_video_kleinunternehmer", False)) and BillingService._is_video_jump_entry(entry))
                or (bool(getattr(invoice, "is_aff_teacher_kleinunternehmer", False)) and BillingService._is_aff_teacher_jump_entry(entry))
            )
            calc = BillingService.get_jump_item_calculation(
                entry=entry,
                ku_active_for_entry=ku_active_for_entry,
                fallback_gross=gross,
            )
            vat_rate = calc["vat_rate"]
            payout_basis = calc["payout_basis"]
            payout_amount = calc["payout_amount"]
            price_source_eur = calc["price_source_eur"]
            price_source_vat_rate = calc["price_source_vat_rate"]
            effective_amount = calc["effective_amount"]
            net, vat = calc["net"], calc["vat"]

            db.session.add(
                InvoiceItem(
                    invoice_id=invoice.id,
                    load_entry_id=entry.id,
                    amount=effective_amount,
                    vat_rate=vat_rate,
                    net_amount=net,
                    vat_amount=vat,
                    description=f"Sprung {entry.height_m} m – {entry.status_code}",
                    price_source_eur=price_source_eur,
                    price_source_vat_rate=price_source_vat_rate,
                    ku_credit_payout_basis=payout_basis,
                    ku_credit_payout_amount=payout_amount,
                )
            )

            # ✅ NUR bei finaler Rechnung abrechnen
            if mark_billed:
                BillingService._mark_entry_billed(entry, gross)

    @staticmethod
    def _add_rent_items(
        invoice: Invoice,
        entries: List[LoadEntry],
        config: Optional[BillingConfig]
    ) -> None:
        """
        Schirmmiete-Positionen (1:1 Logik, zentralisiert).
        """
        if not config:
            return

        counts: Dict[Tuple[date, str], Dict[str, Optional[int]]] = defaultdict(
            lambda: {
                "count": 0,
                "rep": None,
                "has_partner_member": 0,
                "has_non_partner_member": 0,
            }
        )

        for e in entries:
            if not BillingService._is_rent_eligible(e):
                continue
            cat = BillingService._rent_category_from_status(e.status_code)
            if not cat:
                continue
            key = (BillingService._entry_day(e), cat)
            counts[key]["count"] += 1
            counts[key]["rep"] = counts[key]["rep"] or e.id
            if cat == "member":
                status = normalize_status_code(getattr(e, "status_code", "") or "")
                if status in BillingService.PARTNER_MEMBER_STATUSES:
                    counts[key]["has_partner_member"] = 1
                else:
                    counts[key]["has_non_partner_member"] = 1

        for (day, cat), info in counts.items():
            price, max_count, vat_rate = BillingService._rent_params(cat, config)

            # max_count == 0 bedeutet "unbegrenzt"
            if max_count and max_count > 0:
                charged = min(int(info["count"] or 0), int(max_count))
            else:
                charged = int(info["count"] or 0)

            if charged <= 0:
                continue

            gross = BillingService._q2(
                Decimal(str(price or "0.00")) * Decimal(charged)
            )
            net, vat = BillingService.split_gross_into_net_and_vat(
                gross=gross,
                vat_rate=vat_rate
            )

            price_str = (
                "{:,.2f}".format(price)
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
            label = BillingService._rent_category_label(
                cat,
                has_partner_member=bool(info.get("has_partner_member")),
                has_non_partner_member=bool(info.get("has_non_partner_member")),
            )
            description = (
                f"Schirmmiete {label} am {day.strftime('%d.%m.%Y')} "
                f"({charged} × {price_str})"
            )

            db.session.add(
                InvoiceItem(
                    invoice_id=invoice.id,
                    load_entry_id=info["rep"],
                    amount=gross,
                    vat_rate=vat_rate,
                    net_amount=net,
                    vat_amount=vat,
                    description=description,
                )
            )

    @staticmethod
    def _group_entries_for_orga(
        entries: List[LoadEntry]
    ) -> Dict[int, List[LoadEntry]]:
        """
        Gruppiert Entries nach period_id (global, ohne Flugplatz-Bezug).
        """
        ctx_map: Dict[int, List[LoadEntry]] = defaultdict(list)

        for e in entries:
            ld = getattr(e, "load", None)
            if not ld:
                continue

            model_id = getattr(ld, "pricing_model_id", None)
            if model_id:
                pid = int(model_id)
            else:
                d0 = BillingService._entry_day(e)
                p0 = BillingService.get_active_price_period(day=d0)
                pid = p0.id if p0 else None

            if pid is None:
                continue

            ctx_map[int(pid)].append(e)

        return ctx_map

    @staticmethod
    def _build_invoice_items(
        invoice: Invoice,
        entries: List[LoadEntry],
        config: Optional[BillingConfig],
        *,
        mark_billed: bool
    ) -> None:
        """
        Zentrale Rechnungslogik: Sprünge + Schirmmiete + Orga + Total.
        """
        BillingService._add_jump_items(
            invoice,
            entries,
            mark_billed=mark_billed
        )

        BillingService._add_rent_items(
            invoice,
            entries,
            config
        )

        ctx_map = BillingService._group_entries_for_orga(entries)

        # Perioden-Gruppen mit identischer Orga-Konfiguration (gleicher Betrag + Modus)
        # zusammenführen, damit die gleiche Pauschale nicht mehrfach berechnet wird,
        # wenn Entries Loads mit unterschiedlichen pricing_model_id-Werten umfassen,
        # die aber dieselbe Orga-Config teilen (z.B. alte vs. neue Periode bei gleichem Tarif).
        orga_merged: dict = {}
        for pid, entries_ctx in ctx_map.items():
            _amt, _mode, _ = BillingService._get_orga_config(period_id=pid)
            _merge_key = (Decimal(str(_amt or "0.00")), _mode or "period")
            if _merge_key not in orga_merged:
                orga_merged[_merge_key] = [pid, list(entries_ctx)]
            else:
                orga_merged[_merge_key][1].extend(entries_ctx)
                if pid > orga_merged[_merge_key][0]:
                    orga_merged[_merge_key][0] = pid

        for orga_data in orga_merged.values():
            BillingService._add_orga_items(
                invoice=invoice,
                entries=orga_data[1],
                period_id=orga_data[0],
            )

        invoice.calculate_total()


    # =========================================================
    # Rechnung erzeugen
    # =========================================================
    @staticmethod
    def _split_entries_for_invoice_output(
        entries: List[LoadEntry] | None,
        *,
        is_tandem_kleinunternehmer: bool = False,
        is_video_kleinunternehmer: bool = False,
        is_aff_teacher_kleinunternehmer: bool = False,
    ) -> Dict[str, List[LoadEntry]]:
        negative_entries: List[LoadEntry] = []
        positive_entries: List[LoadEntry] = []

        for entry in list(entries or []):
            try:
                is_tandemmaster_jump = BillingService._is_tandemmaster_jump_entry(entry)
                is_video_jump = BillingService._is_video_jump_entry(entry)
                is_aff_teacher_jump = BillingService._is_aff_teacher_jump_entry(entry)
                ku_active_for_entry = (
                    (is_tandem_kleinunternehmer and is_tandemmaster_jump)
                    or (is_video_kleinunternehmer and is_video_jump)
                    or (is_aff_teacher_kleinunternehmer and is_aff_teacher_jump)
                )
                calc = BillingService.get_jump_item_calculation(
                    entry=entry,
                    ku_active_for_entry=ku_active_for_entry,
                    fallback_gross=Decimal(str(BillingService.calculate_price_for_entry(entry) or "0.00")),
                )
                amount = Decimal(str(calc.get("effective_amount") or "0.00"))
            except Exception:
                amount = Decimal("0.00")

            if amount < Decimal("0.00"):
                negative_entries.append(entry)
            else:
                positive_entries.append(entry)

        return {
            "negative": negative_entries,
            "positive": positive_entries,
        }

    @staticmethod
    def create_invoice_for_person(
        person_id: int,
        billing_address_name: str = None,
        billing_address_street: str = None,
        billing_address_zip: str = None,
        billing_address_city: str = None,
        billing_address_email: str = None,
        prepaid_voucher_amount: Decimal | None = None,
        is_tandem_kleinunternehmer: bool | None = None,
        is_video_kleinunternehmer: bool | None = None,
        is_aff_teacher_kleinunternehmer: bool | None = None,
        entries_override: Optional[List[LoadEntry]] = None,
        clear_existing_drafts: bool = True,
    ) -> Optional[Invoice]:
        # 1) Offene Sprünge prüfen (VOR Transaktion)
        open_entries = list(entries_override or BillingService.get_open_entries_for_person(person_id))
        if not open_entries:
            return None

        try:
            config = BillingService.get_global_config()
        except Exception:
            config = None


        # 2) ALLE DB-Änderungen IN EINER Transaktion
        with db.session.begin_nested():
            person = db.session.get(Person, person_id)
            person_ku_default = bool(getattr(person, "is_tandem_kleinunternehmer", False)) if person else False
            person_video_ku_default = bool(getattr(person, "is_video_kleinunternehmer", False)) if person else False
            person_aff_teacher_ku_default = bool(getattr(person, "is_aff_teacher_kleinunternehmer", False)) if person else False
            invoice_ku_flag = person_ku_default if is_tandem_kleinunternehmer is None else bool(is_tandem_kleinunternehmer)
            invoice_video_ku_flag = person_video_ku_default if is_video_kleinunternehmer is None else bool(is_video_kleinunternehmer)
            invoice_aff_teacher_ku_flag = person_aff_teacher_ku_default if is_aff_teacher_kleinunternehmer is None else bool(is_aff_teacher_kleinunternehmer)

            if clear_existing_drafts:
                # ✅ SCHUTZ: Alte Entwurfs-Rechnungen der Person entfernen (inkl. Items)
                old_drafts = Invoice.query.filter_by(
                    person_id=person_id,
                    stage="draft"
                ).all()
                for draft in old_drafts:
                    # Alle zugehörigen InvoiceItems löschen
                    for item in getattr(draft, "items", []):
                        db.session.delete(item)
                    db.session.delete(draft)

            # ✅ Neue Entwurfs-Rechnung erzeugen
            invoice = Invoice(
                person_id=person_id,
                created_at=datetime.utcnow(),
                total_amount=Decimal("0.00"),
                stage="draft",  # ✅ Entwurf
                billing_address_name=billing_address_name,
                billing_address_street=billing_address_street,
                billing_address_zip=billing_address_zip,
                billing_address_city=billing_address_city,
                billing_address_email=billing_address_email,
                is_tandem_kleinunternehmer=invoice_ku_flag,
                is_video_kleinunternehmer=invoice_video_ku_flag,
                is_aff_teacher_kleinunternehmer=invoice_aff_teacher_ku_flag,
            )
            db.session.add(invoice)

            # ✅ Flush erzwingt ID-Zuweisung jetzt
            db.session.flush()

            # ✅ Rechnungspositionen erzeugen
            BillingService._build_invoice_items(
                invoice,
                open_entries,
                config,
                mark_billed=False,  # ✅ ENTWURF blockiert nichts
            )

            # Optionaler Brutto-Teilbetrag "Vorkasse / Gutschein".
            # Gesamtbetrag der Rechnung bleibt unverändert; der Betrag darf nur ein Teil sein.
            prepaid = Decimal(str(prepaid_voucher_amount or "0.00"))
            if prepaid < Decimal("0.00"):
                prepaid = Decimal("0.00")
            total = Decimal(str(invoice.total_amount or "0.00"))
            if prepaid >= total:
                prepaid = Decimal("0.00")
            invoice.prepaid_voucher_amount = prepaid

            return invoice

    @staticmethod
    def create_manual_invoice(
        *,
        person_id: int,
        service_date: date,
        manual_title: str = "Manuelle Positionen",
        manual_lines: List[Dict[str, Any]],
        billing_address_name: str = None,
        billing_address_street: str = None,
        billing_address_zip: str = None,
        billing_address_city: str = None,
        billing_address_email: str = None,
        prepaid_voucher_amount: Decimal | None = None,
    ) -> Optional[Invoice]:
        """
        Erstellt eine manuelle Entwurfsrechnung mit frei erfassbaren Positionen.

        Erwartete manual_lines Struktur je Position:
        {
            "description": str,
            "quantity": Decimal,
            "manual_unit": str,
            "unit_price_gross": Decimal,
            "vat_rate": Decimal,
            "manual_position_code": Optional[str],
        }
        """
        valid_lines: List[Dict[str, Any]] = []
        for line in list(manual_lines or []):
            desc = str((line or {}).get("description") or "").strip()
            if not desc:
                continue

            qty = Decimal(str((line or {}).get("quantity") or "0"))
            unit = Decimal(str((line or {}).get("unit_price_gross") or "0"))
            vat_rate = Decimal(str((line or {}).get("vat_rate") or "0"))

            if qty == 0:
                continue

            gross = BillingService._q2(qty * unit)
            if gross == Decimal("0.00"):
                continue

            valid_lines.append(
                {
                    "description": desc,
                    "quantity": BillingService._q2(qty),
                    "manual_unit": str((line or {}).get("manual_unit") or "").strip() or None,
                    "unit_price_gross": BillingService._q2(unit),
                    "vat_rate": BillingService._q2(vat_rate),
                    "gross": gross,
                    "manual_position_code": (line or {}).get("manual_position_code") or "manual",
                }
            )

        if not valid_lines:
            return None

        with db.session.begin_nested():
            # Alte Entwürfe der Person entfernen, damit es konsistent nur einen aktuellen Entwurf gibt.
            old_drafts = Invoice.query.filter_by(
                person_id=person_id,
                stage="draft"
            ).all()
            for draft in old_drafts:
                for item in getattr(draft, "items", []):
                    db.session.delete(item)
                db.session.delete(draft)

            invoice = Invoice(
                person_id=person_id,
                created_at=datetime.utcnow(),
                service_date=service_date,
                manual_title=(manual_title or "").strip() or "Manuelle Positionen",
                total_amount=Decimal("0.00"),
                stage="draft",
                billing_address_name=billing_address_name,
                billing_address_street=billing_address_street,
                billing_address_zip=billing_address_zip,
                billing_address_city=billing_address_city,
                billing_address_email=billing_address_email,
            )
            db.session.add(invoice)
            db.session.flush()

            for line in valid_lines:
                net, vat = BillingService.split_gross_into_net_and_vat(
                    gross=line["gross"],
                    vat_rate=line["vat_rate"],
                )
                db.session.add(
                    InvoiceItem(
                        invoice_id=invoice.id,
                        load_entry_id=None,
                        amount=line["gross"],
                        vat_rate=line["vat_rate"],
                        net_amount=net,
                        vat_amount=vat,
                        description=line["description"],
                        item_source="manual",
                        quantity=line["quantity"],
                        manual_unit=line["manual_unit"],
                        unit_price_gross=line["unit_price_gross"],
                        manual_position_code=line["manual_position_code"],
                    )
                )

            invoice.calculate_total()

            prepaid = Decimal(str(prepaid_voucher_amount or "0.00"))
            if prepaid < Decimal("0.00"):
                prepaid = Decimal("0.00")
            invoice.prepaid_voucher_amount = prepaid

            return invoice

    # ---------------------------------------------------------
    # Rechnung als bezahlt markieren
    # ---------------------------------------------------------
    @staticmethod
    def mark_invoice_paid(invoice_id: int, payment_method: Optional[str] = None) -> bool:
        """
        Markiert die Rechnung als bezahlt und speichert optional die Zahlungsart.
        payment_method: "cash" | "card" | "transfer" | "wero" | None
        """
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            return False

        allowed = {"cash", "card", "transfer", "wero"}

        if payment_method is not None:
            pm = (payment_method or "").strip().lower()
            if pm not in allowed:
                return False
        else:
            pm = None

        with db.session.begin_nested():
            if not getattr(invoice, "is_paid", False):
                invoice.mark_paid()
                for item in invoice.items:
                    if item.load_entry:
                        item.load_entry.mark_paid()

            invoice.payment_method = pm
            return True

    # ---------------------------------------------------------
    # DEV: Rechnung neu berechnen (Snapshot aktualisieren)
    # ---------------------------------------------------------
    @staticmethod
    def recalculate_invoice(invoice_id: int) -> bool:
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            return False

        if getattr(invoice, "is_deleted", False):
            return False

        old_entries: List[LoadEntry] = []
        for it in list(invoice.items):
            le = getattr(it, "load_entry", None)
            if le:
                old_entries.append(le)

        try:
            config = BillingService.get_global_config()
        except Exception:
            config = None

        with db.session.begin_nested():
            # Items löschen (DEV-Recalc)
            for it in list(invoice.items):
                db.session.delete(it)
            db.session.flush()

            # Flags zurücksetzen (wie vorher)
            for e in old_entries:
                if hasattr(e, "billed"):
                    e.billed = False
                if hasattr(e, "paid"):
                    e.paid = False
                if hasattr(e, "paid_at"):
                    e.paid_at = None

            if getattr(invoice, "is_paid", False):
                invoice.is_paid = False
                invoice.paid_at = None

            open_entries = BillingService.get_open_entries_for_person(invoice.person_id)
            if not open_entries:
                invoice.total_amount = Decimal("0.00")
                return True

            BillingService._build_invoice_items(invoice, open_entries, config)
            return True
            
    # =========================================================
    # PDF: Rechnung aus invoice_detail.html rendern (für E-Mail)
    # =========================================================
    @staticmethod
    def render_invoice_pdf(
        invoice: Invoice,
        *,
        billing_config: Optional[BillingConfig] = None,
        epc_qr_data_uri: Optional[str] = None,
        invoice_purpose: Optional[str] = None,
    ) -> bytes:
        """
        Rendert die Rechnung serverseitig als PDF basierend auf dem bestehenden Template
        billing/invoice_detail.html und liefert PDF-Bytes für E-Mail Anhänge.
        """
        if billing_config is None:
            try:
                billing_config = BillingService.get_global_config()
            except Exception:
                billing_config = None

        # Import lokal, um zyklische Modulimporte beim App-Start zu vermeiden.
        from app.routes.billing import (
            _invoice_allows_prepaid_voucher,
            _invoice_onsite_amount,
            _invoice_prepaid_amount,
            _invoice_split_payment_label,
        )

        prepaid_voucher_amount = _invoice_prepaid_amount(invoice)
        onsite_amount = _invoice_onsite_amount(invoice)
        prepaid_allowed = _invoice_allows_prepaid_voucher(invoice)

        # --------------------------------------------------
        # Bilder als Data-URIs laden (für PDF-Kompatibilität)
        # --------------------------------------------------
        static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
        logo_data_uri = None
        if billing_config and billing_config.logo_filename:
            logo_path = os.path.join(static_dir, "img", billing_config.logo_filename)
            logo_data_uri = _image_to_data_uri(logo_path)

        qr_instagram_data_uri = None
        if billing_config and billing_config.qr_instagram_filename:
            qr_path = os.path.join(static_dir, "img", "qr", billing_config.qr_instagram_filename)
            qr_instagram_data_uri = _image_to_data_uri(qr_path)

        qr_facebook_data_uri = None
        if billing_config and billing_config.qr_facebook_filename:
            qr_path = os.path.join(static_dir, "img", "qr", billing_config.qr_facebook_filename)
            qr_facebook_data_uri = _image_to_data_uri(qr_path)

        qr_website_data_uri = None
        if billing_config and billing_config.qr_website_filename:
            qr_path = os.path.join(static_dir, "img", "qr", billing_config.qr_website_filename)
            qr_website_data_uri = _image_to_data_uri(qr_path)

        invoice_ku_regular_vat_rates: dict[int, Decimal] = {}
        invoice_dynamic_fixed_net = Decimal("0.00")
        invoice_dynamic_fixed_vat = Decimal("0.00")
        has_tandem_ku_rows = False
        has_video_ku_rows = False
        for _item in list(getattr(invoice, "items", []) or []):
            _desc = (getattr(_item, "description", "") or "").strip()
            _is_jump_item = _desc.startswith("Sprung") and bool(getattr(_item, "load_entry", None))

            if BillingService._is_tandemmaster_jump_item(_item):
                has_tandem_ku_rows = True
            if BillingService._is_video_jump_item(_item):
                has_video_ku_rows = True

            if _is_jump_item:
                _entry = getattr(_item, "load_entry", None)
                _base_rate = BillingService.get_entry_vat_rate(_entry) if _entry else Decimal("0.00")
                if getattr(_item, "id", None) is not None:
                    invoice_ku_regular_vat_rates[int(_item.id)] = Decimal(str(_base_rate or "0.00"))
                continue

            invoice_dynamic_fixed_net += Decimal(str(getattr(_item, "net_amount", 0) or 0))
            invoice_dynamic_fixed_vat += Decimal(str(getattr(_item, "vat_amount", 0) or 0))

        invoice_dynamic_fixed_net = invoice_dynamic_fixed_net.quantize(Decimal("0.01"))
        invoice_dynamic_fixed_vat = invoice_dynamic_fixed_vat.quantize(Decimal("0.01"))

        # HTML exakt aus deinem bestehenden Template erzeugen
        html = render_template(
            "billing/invoice_detail.html",
            invoice=invoice,
            invoice_purpose=invoice_purpose,
            billing_config=billing_config,
            epc_qr_data_uri=epc_qr_data_uri,
            logo_data_uri=logo_data_uri,
            qr_instagram_data_uri=qr_instagram_data_uri,
            qr_facebook_data_uri=qr_facebook_data_uri,
            qr_website_data_uri=qr_website_data_uri,
            prepaid_voucher_amount=prepaid_voucher_amount,
            onsite_amount=onsite_amount,
            prepaid_allowed=prepaid_allowed,
            invoice_split_payment_label=_invoice_split_payment_label,
            invoice_has_tandem_jump_positions=has_tandem_ku_rows,
            invoice_has_video_jump_positions=has_video_ku_rows,
            invoice_has_ku_jump_positions=(has_tandem_ku_rows or has_video_ku_rows),
            invoice_ku_regular_vat_rates=invoice_ku_regular_vat_rates,
            invoice_dynamic_fixed_net=invoice_dynamic_fixed_net,
            invoice_dynamic_fixed_vat=invoice_dynamic_fixed_vat,
            is_pdf_render=True,
            is_dev_mode=False,   # im PDF keine Dev/UI-Elemente
        )

        # base_url: app-Ordner als Basis, damit static/img/... zuverlässig gefunden wird
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        # WeasyPrint nur bei echtem PDF-Render laden, damit der App-Start nicht
        # unnötig GTK/GIO initialisiert.
        from weasyprint import HTML

        # WeasyPrint: HTML+CSS -> PDF Bytes
        pdf_bytes = HTML(string=html, base_url=base_dir).write_pdf(
            stylesheets=None,  # Use default styles
            presentational_hints=True,
            optimize_size=('fonts', 'images'),  # Optimize for size
        )
        return pdf_bytes