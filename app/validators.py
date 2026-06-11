"""
Validierungs-Utilities für App.
Zentralisiert Validierungslogik aus verschiedenen Routes/Services.
"""

from typing import Optional
from app.models.person import Person


def slot_for_person(person: Optional[Person]) -> str:
    """
    Bestimmt den Slot (Kategorie) einer Person.
    Wird für Status-Validierung verwendet.
    """
    if not person:
        return "unknown"
    
    if person.category == "Guest":
        return "guest"
    elif person.category == "Student":
        return "student"
    elif person.category == "Instructor":
        return "instructor"
    elif person.category == "Staff":
        return "staff"
    else:
        return "other"


def status_allowed_for_person_and_slot(
    code: str, label: str, person: Optional[Person], slot: str
) -> bool:
    """
    Validiert, ob ein bestimmter Status für eine Person + Slot zulässig ist.
    
    Regeln (aus load.py):
    - Student: kann nur Schüler-Status, AFF-Status
    - Instructor: kann Lehrer-Status, ggf. AFF-Status
    - Guest/Tandem: kann G-TD, G-TD-Video, Mitflieger
    - Staff: meist keine spezifischen Slots
    """
    from app.utils import (
        _is_student_specific_status,
        _is_teacher_specific_status,
        _is_aff_teacher_status,
        _is_aff_student_status,
        STUDENT_STATUSES,
        TANDEM_GUEST_STATUSES,
    )
    
    if slot == "student":
        # Schüler: nur Schüler-Status oder AFF
        if code in STUDENT_STATUSES:
            return True
        if _is_aff_student_status(code):
            return True
        return False
    
    elif slot == "instructor":
        # Lehrer: Lehrer-Status, AFF-Lehrer, evt. auch Schüler
        if code in ("L", "L2"):
            return True
        if _is_aff_teacher_status(code):
            return True
        return False
    
    elif slot == "guest":
        # Gast: G-TD, G-TD-Video, Mitflieger
        return code in TANDEM_GUEST_STATUSES
    
    else:
        # Staff/Other: meist alles außer sehr spezifischen Status
        return code not in ("", None)


def validate_load_entry_height(height: Optional[int]) -> bool:
    """Validiert, ob eine Höhe erlaubt ist."""
    VALID_HEIGHTS = {1500, 3000, 4000}
    return height in VALID_HEIGHTS if height else False


def validate_email(email: str) -> bool:
    """Basis-Email-Validierung."""
    if not email or "@" not in email:
        return False
    return len(email) > 5 and "." in email.split("@")[1]
