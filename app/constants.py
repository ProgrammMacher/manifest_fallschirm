"""
Zentrale Konstanten für Status-Codes, Validierung, etc.
"""

# ============================================================
# Status-Kategorien (aus load.py + billing_service.py konsolidiert)
# ============================================================

# Schüler-Status (inkl. AFF-Schüler)
STUDENT_STATUSES = {
    "Schüler",
    "Schüler Ek 1",
    "Schüler Ek 2",
    "Schüler GK 6",
    "Schueler-Aff-1",
    "Schueler-Aff-2",
}

# Tandem-Gast-Status
TANDEM_GUEST_STATUSES = {
    "G-TD",
    "G-TD-Video",
    "Mitflieger",
}

# Status die keine Schirmmiete erlauben
NO_RENT_STATUSES = STUDENT_STATUSES | TANDEM_GUEST_STATUSES

# Tandemmaster
TM_STATUSES = {
    "TD",
    "TD-Vereins-Schirm",
}

# Video-Personal
VIDEO_STATUSES = {
    "Video",
}

# Gäste
GUEST_STATUSES = {
    "Gast",
    "Auffüller Gast",
}

# Partner-Verein
PARTNER_MEMBER_STATUSES = {
    "Partner-Verein",
    "Auffüller Partner-Verein",
}

# Vereinsmitglieder
MEMBER_STATUSES = {
    "Verein",
    "Auffüller Verein",
    "Lehrer",
    "Aff-Lehrer",
    "Lehrer Ek 1",
    "Lehrer Ek 2",
    "Lehrer GK 6",
    "Auffüller Lehrer",
}

# Kosten-relevante Status
COST_STATUSES = STUDENT_STATUSES | TANDEM_GUEST_STATUSES | {"Schirmmiete", "Orga", "Miete"}

# Gültige Höhen für Flüge
VALID_HEIGHTS = {1500, 3000, 4000}

# ============================================================
# Billing-spezifische Konstanten
# ============================================================

# Zahlungsstatus fuer Rechnungen
INVOICE_PAYMENT_STATE_OPEN = "open"
INVOICE_PAYMENT_STATE_SEPA_PENDING = "sepa_pending"
INVOICE_PAYMENT_STATE_SEPA_EXPORTED = "sepa_exported"
INVOICE_PAYMENT_STATE_PAID = "paid"
INVOICE_PAYMENT_STATE_SEPA_RETURNED = "sepa_returned"

INVOICE_PAYMENT_STATES = {
    INVOICE_PAYMENT_STATE_OPEN,
    INVOICE_PAYMENT_STATE_SEPA_PENDING,
    INVOICE_PAYMENT_STATE_SEPA_EXPORTED,
    INVOICE_PAYMENT_STATE_PAID,
    INVOICE_PAYMENT_STATE_SEPA_RETURNED,
}

# Lehrer-Status
TEACHER_STATUSES = {
    "Lehrer",
    "Aff-Lehrer",
    "Lehrer Ek 1",
    "Lehrer Ek 2",
    "Lehrer GK 6",
    "Auffüller Lehrer",
}

# Alle "echten" Statuses (nicht Besatzer/Gast)
PERSON_STATUSES = (
    STUDENT_STATUSES
    | TEACHER_STATUSES
    | TM_STATUSES
    | GUEST_STATUSES
    | PARTNER_MEMBER_STATUSES
    | MEMBER_STATUSES
)
