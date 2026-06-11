"""
Utility-Funktionen für App (Parse, Validierung, Format).
Extrahiert aus routes/load.py und anderen für Wiederverwendbarkeit.
"""

from app.constants import STUDENT_STATUSES, TANDEM_GUEST_STATUSES, COST_STATUSES

# ============================================================
# Parse-Utilities
# ============================================================

def parse_int(raw) -> int | None:
    """Parst einen Integer aus String/None, robust."""
    s = (str(raw).strip() if raw is not None else "")
    if not s:
        return None
    try:
        return int(s)
    except Exception:
        return None


def parse_float(raw) -> float | None:
    """Parst einen Float aus String/None."""
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "":
        return None
    try:
        return float(s.replace(",", "."))
    except Exception:
        return None


def parse_bool(raw) -> bool:
    """
    Parst Boolean aus String/None.
    True: "yes", "true", "1", "on", True
    False: alles andere (inclusive None/empty)
    """
    if raw is None or raw is False or raw == "":
        return False
    s = str(raw).lower().strip()
    return s in ("yes", "true", "1", "on")


# ============================================================
# Status-Code Utilities
# ============================================================


def _status_text_parts(code: str, label: str) -> tuple[str, str]:
    """Splittet Status-Label in kurz + lang (z.B. 'Schüler (Ek 1)' → 'Schüler', '(Ek 1)')."""
    if "(" not in label:
        return label, ""
    main, rest = label.split("(", 1)
    return main.strip(), "(" + rest


def _is_student_specific_status(code: str, label: str) -> bool:
    """Ist Status spezifisch für Schüler (also NICHT 'Schüler' selbst)?"""
    main, rest = _status_text_parts(code, label)
    return "Ek " in rest or "GK " in rest


def _is_teacher_specific_status(code: str, label: str) -> bool:
    """Ist Status spezifisch für Lehrer (also NICHT 'Lehrer' selbst)?"""
    if code not in ("L", "L2"):
        return False
    main, rest = _status_text_parts(code, label)
    return "Ek " in rest or "GK " in rest


def _is_aff_teacher_status(code: str) -> bool:
    """Ist Status ein AFF-Lehrer?"""
    return code.upper().startswith("AFF")


def _aff_student_level(code: str) -> int:
    """AFF-Level aus Code: 'AFF1' → 1, 'AFF-2' → 2, etc."""
    try:
        for c in str(code).replace("-", ""):
            if c.isdigit():
                return int(c)
    except Exception:
        pass
    return 0


def _is_aff_student_status(code: str) -> bool:
    """Ist Status ein AFF-Schüler (AFF0, AFF1, etc)?"""
    return code.upper().startswith("AFF") and _aff_student_level(code) > 0


def _is_cost_status(code: str, label: str) -> bool:
    """Zählt dieser Status für Kosten-Berechnung? (nicht z.B. Besatzer)."""
    main, _ = _status_text_parts(code, label)
    return main in COST_STATUSES


def _is_gear_rental_forbidden_status(code: str) -> bool:
    """
    Für diese Statuses ist Schirmmiete NICHT erlaubt.
    (Schüler haben Schirme, Tandem-Gäste auch, etc.)
    """
    return code in STUDENT_STATUSES or code in TANDEM_GUEST_STATUSES
