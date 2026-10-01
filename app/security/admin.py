# app/security/admin.py

from functools import wraps
from flask import session, flash, redirect, request, url_for


def is_admin() -> bool:
    """
    Zentrale Admin-Prüfung.
    """
    return bool(session.get("is_admin", False))


def admin_required(func):
    """
    Decorator für Admin-only-Routen (normale UI-Aktionen).
    Statt eines stillen 403 wird verständlich erklärt, warum der Zugriff
    fehlt, und zum zentralen Admin-Login weitergeleitet (bestehende
    after_login_redirect-Architektur, siehe admin_auth.admin_login).
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_admin():
            flash(
                "Diese Funktion ist nur im Admin-Modus verfügbar. "
                "Bitte melden Sie sich als Administrator an.",
                "warning",
            )
            session["after_login_redirect"] = request.referrer or url_for("pwa.pwa_index")
            return redirect(url_for("admin_auth.admin_login"))
        return func(*args, **kwargs)
    return wrapper