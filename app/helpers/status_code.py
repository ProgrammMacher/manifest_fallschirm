# C:\manifest_fallschirm\app\helpers\status_code.py

from typing import Dict


# =========================================================
# Kanonische Statuscodes
# Alle Varianten (technisch, historisch, UI) werden
# auf EINEN fachlichen Code normalisiert.
# =========================================================
CANONICAL: Dict[str, str] = {

    # -------------------------
    # Verein / Gast
    # -------------------------
    "VEREIN": "Verein",
    "VEREINSMITGLIED": "Verein",

    "PARTNER VEREIN": "Partner-Verein",
    "PARTNERVEREIN": "Partner-Verein",
    "PARTNER_VEREIN": "Partner-Verein",
    "PARTNER-VEREIN": "Partner-Verein",

    "GAST": "Gast",

    # -------------------------
    # Schüler
    # -------------------------
    "SCHUELER": "Schüler",
    "SCHÜLER": "Schüler",

    "SCHUELER_EK1": "Schüler Ek 1",
    "SCHUELER EK 1": "Schüler Ek 1",
    "SCHÜLER EK 1": "Schüler Ek 1",

    "SCHUELER_EK2": "Schüler Ek 2",
    "SCHUELER EK 2": "Schüler Ek 2",
    "SCHÜLER EK 2": "Schüler Ek 2",

    "SCHUELER_GK6": "Schüler GK 6",
    "SCHUELER GK 6": "Schüler GK 6",
    "SCHÜLER GK 6": "Schüler GK 6",

    # -------------------------
    # Lehrer
    # -------------------------
    "LEHRER": "Lehrer",
    "AFF LEHRER": "Aff-Lehrer",
    "AFF-LEHRER": "Aff-Lehrer",
    "AFF_LEHRER": "Aff-Lehrer",

    # -------------------------
    # AFF-Schüler
    # -------------------------
    "SCHUELER AFF 1": "Schueler-Aff-1",
    "SCHUELER-AFF-1": "Schueler-Aff-1",
    "SCHUELER_AFF_1": "Schueler-Aff-1",
    "SCHÜLER AFF 1": "Schueler-Aff-1",

    "SCHUELER AFF 2": "Schueler-Aff-2",
    "SCHUELER-AFF-2": "Schueler-Aff-2",
    "SCHUELER_AFF_2": "Schueler-Aff-2",
    "SCHÜLER AFF 2": "Schueler-Aff-2",

    # -------------------------
    # Tandem
    # -------------------------
    "TD": "TD",
    "TANDEMMASTER": "TD",

    "TD_VEREIN_SCHIRM": "TD-Vereins-Schirm",
    "TD-VEREINS-SCHIRM": "TD-Vereins-Schirm",
    "TD VEREIN SCHIRM": "TD-Vereins-Schirm",

    "G-TD": "G-TD",
    "G TD": "G-TD",
    "G_TD": "G-TD",

    "G-TD-VIDEO": "G-TD-Video",
    "G TD VIDEO": "G-TD-Video",
    "G_TD_VIDEO": "G-TD-Video",

    # -------------------------
    # Video
    # -------------------------
    "VIDEO": "Video",
    "VIDEOMANN": "Video",

    # -------------------------
    # Mitflieger
    # -------------------------
    "MITFLIEGER": "Mitflieger",

    # -------------------------
    # Auffüller
    # -------------------------
    "AUFFUELLER VEREIN": "Auffüller Verein",
    "AUFFUELLER_VEREIN": "Auffüller Verein",
    "AUFFÜLLER VEREIN": "Auffüller Verein",

    "AUFFUELLER GAST": "Auffüller Gast",
    "AUFFUELLER_GAST": "Auffüller Gast",
    "AUFFÜLLER GAST": "Auffüller Gast",

    "AUFFUELLER PARTNER VEREIN": "Auffüller Partner-Verein",
    "AUFFUELLER_PARTNER_VEREIN": "Auffüller Partner-Verein",
    "AUFFÜLLER PARTNER VEREIN": "Auffüller Partner-Verein",
    "AUFFÜLLER PARTNER-VEREIN": "Auffüller Partner-Verein",

    # -------------------------
    # Organisation
    # -------------------------
    "ORGA": "Orga",
}


# =========================================================
# Anzeigebezeichnungen (kanonischer Code -> lesbare Anzeige)
# Wird für UI, PDF, Rechnungen verwendet.
# =========================================================
DISPLAY_LABELS: Dict[str, str] = {
    "Aff-Lehrer":    "AFF-Lehrer",
    "Schueler-Aff-1": "Schüler-AFF-1",
    "Schueler-Aff-2": "Schüler-AFF-2",
}


def status_display_label(raw: str | None) -> str:
    """
    Gibt die leserliche Anzeigebezeichnung für einen Statuscode zurück.
    Normalisiert zuerst auf kanonischen Code, dann schlägt es in DISPLAY_LABELS nach.
    Fallback: original (nicht verändert, damit normale Status wie 'Verein' unverändert bleiben).
    """
    if not raw:
        return ""
    canonical = normalize_status_code(raw)
    return DISPLAY_LABELS.get(canonical, canonical)


# =========================================================
# Zentrale Normalisierungsfunktion
# (WIRD IM GANZEN SYSTEM VERWENDET!)
# =========================================================
def normalize_status_code(raw: str | None) -> str:
    """
    Normalisiert beliebige Status-Eingaben auf einen
    kanonischen fachlichen Statuscode.

    - tolerant gegenüber Groß/Kleinschreibung
    - tolerant gegenüber _ / - / Leerzeichen
    - garantiert stabilen Rückgabewert
    """
    if not raw:
        return ""

    s = str(raw).strip()

    # Vereinheitlichung
    s_norm = (
        s.upper()
        .replace("-", " ")
        .replace("_", " ")
        .replace("  ", " ")
        .strip()
    )

    # Direkt-Match
    if s_norm in CANONICAL:
        return CANONICAL[s_norm]

    # Fallback: Original (Titel-Case)
    return s.title()
