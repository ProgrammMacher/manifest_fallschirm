# C:\manifest_fallschirm\app\services\load_service.py
"""
Load-Service: Reine Business-Logik für Load-Objekte.
Keine Flask-Abhängigkeiten (kein request/session/url_for/current_app).
"""
from __future__ import annotations

from datetime import datetime, date, time as dtime
from decimal import Decimal
from typing import Optional

from sqlalchemy import or_

from app import db
from app.models.load import Load
from app.models.billing_config import BillingPrice
from app.helpers.status_code import normalize_status_code
from app.constants import STUDENT_STATUSES, TANDEM_GUEST_STATUSES


# ============================================================
# Betriebstag-Logik
# ============================================================

def operation_date_from_times(
    actual_time: Optional[datetime],
    scheduled_time: Optional[datetime],  # bleibt nur aus Kompatibilität in der Signatur
    created_at: datetime,
) -> date:
    """
    Ermittelt den fachlichen Betriebstag eines Loads.

    Fachregel: Es gibt nur EIN Zeitfeld.
    Priorität:
    1) actual_time
    2) created_at (Fallback, falls actual_time fehlt)
    """
    dt = actual_time or created_at
    return dt.date()


def next_load_number_for_day(
    airfield_id: int,
    op_date: date,
    exclude_load_id: Optional[int] = None,
) -> int:
    """
    Ermittelt die nächste freie Load-Nummer pro Flugplatz + Betriebstag.

    Fachregel: Betriebstag basiert NUR auf actual_time (Fallback: created_at).
    scheduled_time wird NICHT berücksichtigt.
    """
    q = (
        Load.query
        .filter(Load.airfield_id == airfield_id)
        .filter(
            or_(
                db.func.date(Load.actual_time) == op_date,
                (
                    Load.actual_time.is_(None) &
                    (db.func.date(Load.created_at) == op_date)
                ),
            )
        )
    )

    if exclude_load_id is not None:
        q = q.filter(Load.id != exclude_load_id)

    last_for_day = q.order_by(Load.load_number.desc()).first()
    if last_for_day is None:
        return 1

    return int(last_for_day.load_number or 0) + 1


# ============================================================
# Folgeload-Warnung
# ============================================================

def apply_follow_load_warnings(loads: list[Load]) -> None:
    """Markiert Einträge als Folgeload (nur Anzeige, keine DB-Änderung)."""
    if not loads:
        return
    sorted_loads = sorted(loads, key=lambda l: l.created_at or datetime.min)
    prev_person_ids: set[int] = set()
    for load in sorted_loads:
        for e in getattr(load, "entries", []) or []:
            setattr(e, "follow_load_warning", False)

        for e in getattr(load, "entries", []) or []:
            pid = getattr(e, "person_id", None)
            if pid is not None and pid in prev_person_ids:
                setattr(e, "follow_load_warning", True)

        prev_person_ids = {
            getattr(e, "person_id", None)
            for e in (getattr(load, "entries", []) or [])
            if getattr(e, "person_id", None) is not None
        }


def apply_follow_load_warning_single(load: Load) -> None:
    """Markiert Einträge eines einzelnen Loads als Folgeload."""
    for e in getattr(load, "entries", []) or []:
        setattr(e, "follow_load_warning", False)

    if not getattr(load, "airfield_id", None):
        return

    prev = (
        Load.query
        .filter(Load.airfield_id == load.airfield_id, Load.created_at < load.created_at)
        .order_by(Load.created_at.desc())
        .first()
    )
    if not prev:
        return

    prev_ids = {
        getattr(e, "person_id", None)
        for e in (prev.entries or [])
        if getattr(e, "person_id", None) is not None
    }

    for e in getattr(load, "entries", []) or []:
        pid = getattr(e, "person_id", None)
        if pid is not None and pid in prev_ids:
            setattr(e, "follow_load_warning", True)


# ============================================================
# Preismodell-Absicherung
# ============================================================

def ensure_pricing_model_available_for_load(pricing_model_id: int) -> None:
    """
    Prüft ob für das gewählte Preismodell Preise existieren.
    Wirft ValueError wenn nicht.
    """
    row = (
        db.session.query(BillingPrice.id)
        .filter(BillingPrice.period_id == pricing_model_id)
        .limit(1)
        .first()
    )
    if not row:
        raise ValueError(
            "Für das aktuell aktive Preismodell existieren keine Preise. "
            "Bitte unter 'Preismatrix' Preise pflegen oder ein anderes Preismodell aktiv setzen."
        )


# ============================================================
# Archiv-Datum-Helpers (pure, keine Flask-Abhängigkeit)
# ============================================================

def archive_effective_datetime_expr():
    """SQLAlchemy-Ausdruck: COALESCE(actual_time, created_at)."""
    return db.func.coalesce(Load.actual_time, Load.created_at)


def archive_effective_datetime(load: Load) -> Optional[datetime]:
    """Effektives Archiv-Datum eines Loads."""
    return getattr(load, "actual_time", None) or getattr(load, "created_at", None)


# ============================================================
# Status-Klassifikations-Helfer
# ============================================================

def _status_text_parts(code: str, label: str) -> tuple[str, str]:
    c = (code or "").strip()
    l = (label or "").strip()
    return c.upper(), l.upper()


def _is_student_specific_status(code: str, label: str) -> bool:
    cu, lu = _status_text_parts(code, label)
    return (
        "SCHUELER" in cu
        or "SCHUELER" in lu
        or "SCHÜLER" in cu
        or "SCHÜLER" in lu
    )


def _is_teacher_specific_status(code: str, label: str) -> bool:
    if _is_aff_student_status(code):
        return False
    cu, lu = _status_text_parts(code, label)
    return "LEHRER" in cu or "LEHRER" in lu


def _is_aff_teacher_status(code: str) -> bool:
    return (code or "").strip().upper() == "AFF-LEHRER"


def _aff_student_level(code: str) -> int:
    raw = (code or "").strip().upper().replace("Ü", "UE")
    compact = (
        raw
        .replace("_", "")
        .replace("-", "")
        .replace(" ", "")
        .replace(".", "")
    )
    if "SCHUELERAFF2" in compact:
        return 2
    if "SCHUELERAFF1" in compact:
        return 1
    return 0


def _is_aff_student_status(code: str) -> bool:
    return _aff_student_level(code) > 0


def _is_cost_status(code: str, label: str) -> bool:
    cu, lu = _status_text_parts(code, label)
    keywords = ("MIETE", "SCHIRMMIETE", "ORGA")
    return any(k in cu or k in lu for k in keywords)


def _is_gear_rental_forbidden_status(code: str) -> bool:
    norm = normalize_status_code(code)
    if _is_aff_student_status(code):
        return True
    if norm in STUDENT_STATUSES:
        return True
    if norm in TANDEM_GUEST_STATUSES:
        return True
    return False


# ============================================================
# Parse- und Berechnungs-Helfer
# ============================================================

def _truthy(v: str) -> bool:
    return (v or "").strip().lower() in ("1", "true", "on", "ja", "yes")


def _parse_date_ymd(s: str) -> Optional[date]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _dt_range(
    from_d: Optional[date], to_d: Optional[date]
) -> tuple[Optional[datetime], Optional[datetime]]:
    start = datetime.combine(from_d, dtime.min) if from_d else None
    end = datetime.combine(to_d, dtime.max) if to_d else None
    return start, end


def _money(x) -> Decimal:
    try:
        return Decimal(str(x if x is not None else "0.00"))
    except Exception:
        return Decimal("0.00")
