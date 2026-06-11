"""
PDF-Service für WeasyPrint-Rendering mit Fehlerbehandlung.
"""

import os
from typing import Optional, Tuple
from flask import current_app
from app.helpers.pdf_runtime import ensure_weasyprint_pdf_runtime


def generate_pdf_from_html(
    html_string: str,
    base_dir: Optional[str] = None,
    auto_heal: bool = True,
    presentational_hints: bool = False,
    optimize_size: Optional[tuple] = None,
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Generiert PDF aus HTML-String mit WeasyPrint.
    
    Args:
        html_string: HTML-Content als String
        base_dir: Base-URL für Ressourcen (default: app dir)
        auto_heal: Versuche PDF-Runtime zu reparieren, wenn fehler
        presentational_hints: WeasyPrint presentational_hints Option
        optimize_size: WeasyPrint optimize_size Option (z.B. ("fonts", "images"))
    
    Returns:
        (pdf_bytes, error_message)
        - Bei Erfolg: (bytes, None)
        - Bei Fehler: (None, error_message_de)
    """
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    write_kwargs = {}
    if presentational_hints:
        write_kwargs["presentational_hints"] = True
    if optimize_size:
        write_kwargs["optimize_size"] = optimize_size

    def _render():
        from weasyprint import HTML
        return HTML(string=html_string, base_url=base_dir).write_pdf(**write_kwargs)

    try:
        return _render(), None
    except Exception as ex:
        if not auto_heal:
            current_app.logger.exception("PDF-Error (no auto-heal)", exc_info=ex)
            return None, f"PDF-Generierung fehlgeschlagen: {str(ex)}"
        
        healed, detail = ensure_weasyprint_pdf_runtime()
        
        if not healed:
            current_app.logger.exception(f"PDF-Runtime nicht heilbar (Detail: {detail})", exc_info=ex)
            return None, (
                "PDF konnte nicht erstellt werden. "
                "Die Offline-PDF-Runtime (GTK/Cairo/Pango) fehlt im Projektordner."
            )
        
        try:
            return _render(), None
        except Exception as second_ex:
            current_app.logger.exception(f"PDF trotz Heilung fehlgeschlagen (Detail: {detail})", exc_info=second_ex)
            return None, (
                "PDF konnte nicht erstellt werden. "
                "Die automatische Offline-Nachinstallation der PDF-Runtime hat nicht ausgereicht."
            )
