# app/security/admin.py

from functools import wraps
from urllib.parse import urlsplit

from flask import session, flash, redirect, request, url_for


def is_admin() -> bool:
    """
    Zentrale Admin-Prüfung.
    """
    return bool(session.get("is_admin", False))


# ---------------------------------------------------------
# Einheitliche Benutzerhinweise bei fehlenden Rechten
# (nur Darstellung/Führung – die Prüfungen selbst bleiben unverändert)
# ---------------------------------------------------------
def admin_denied_message(feature: str | None = None, as_db_admin: bool = False) -> str:
    """
    Hinweis für Funktionen, die Voll-Admin-Rechte benötigen.
    feature: optionaler Funktionsname inkl. Artikel, z. B. "Die Preismatrix".
    as_db_admin: True, wenn aktuell als Datenbank-Admin angemeldet.
    """
    subject = f"{feature} ist" if feature else "Diese Funktion ist"
    text = f"{subject} nur im Admin-Modus verfügbar."
    if as_db_admin:
        text += " Aktuell sind Sie als Datenbank-Admin angemeldet."
    return text + " Bitte melden Sie sich als Administrator an."


def db_admin_denied_message(feature: str | None = None) -> str:
    """
    Hinweis für Funktionen, die Admin- oder Datenbank-Admin-Rechte benötigen.
    """
    subject = f"{feature} erfordert" if feature else "Diese Funktion erfordert"
    return (
        f"{subject} Admin- oder Datenbank-Admin-Rechte. "
        "Bitte melden Sie sich mit dem Admin- oder Datenbank-Admin-Passwort an."
    )


def _safe_local_target(target: str | None) -> str | None:
    """
    Liefert nur lokale Pfade (inkl. Query) zurück – nie externe Ziele.
    Login-/Logout-Seiten sind als Rückkehrziel ausgeschlossen.
    """
    if not target:
        return None

    parts = urlsplit(str(target))
    if parts.scheme or parts.netloc:
        if parts.netloc != request.host:
            return None

    path = parts.path or ""
    if not path.startswith("/") or path.startswith("//") or "\\" in path:
        return None
    if path.startswith(("/admin/login", "/admin/logout")):
        return None

    return path + (f"?{parts.query}" if parts.query else "")


def redirect_to_admin_login(
    message: str,
    category: str = "warning",
    fallback_url: str | None = None,
):
    """
    Zentrale Weiterleitung zum bestehenden Admin-Login (/admin/login).

    - zeigt den verständlichen Hinweis (Flash)
    - merkt das Rückkehrziel in session["after_login_redirect"]
      (wird in admin_auth.admin_login ausgewertet):
        * GET:  die angeforderte Seite selbst
        * POST: die Ursprungsseite (Referer), sonst fallback_url
      POST-Pfade werden nie als Ziel gemerkt (nach dem Login wäre es ein GET).
    - AJAX-Requests (XMLHttpRequest) bekommen kein Rückkehrziel gemerkt.
    Es werden keine Rechte vergeben oder geprüft.
    """
    is_xhr = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if not is_xhr:
        if request.method in ("GET", "HEAD"):
            target = _safe_local_target(request.full_path.rstrip("?"))
        else:
            target = _safe_local_target(request.referrer) or _safe_local_target(fallback_url)

        if target:
            session["after_login_redirect"] = target
        else:
            session.pop("after_login_redirect", None)

    flash(message, category)
    return redirect(url_for("admin_auth.admin_login"))


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
            return redirect_to_admin_login(
                admin_denied_message(as_db_admin=bool(session.get("is_db_admin")))
            )
        return func(*args, **kwargs)
    return wrapper