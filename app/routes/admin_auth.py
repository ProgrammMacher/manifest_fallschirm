# C:\manifest_fallschirm\app\routes\admin_auth.py

from __future__ import annotations

from functools import wraps
from flask import (
    Blueprint,
    request,
    session,
    redirect,
    url_for,
    flash,
    current_app,
    render_template,
)
from app.security.credentials import verify_password

bp_admin_auth = Blueprint("admin_auth", __name__, url_prefix="/admin")


# ---------------------------------------------------------
# Rollen prüfen
# ---------------------------------------------------------
def is_admin() -> bool:
    """Voll-Admin (darf alles)."""
    return bool(session.get("is_admin", False))


def is_db_admin() -> bool:
    """DB-Admin (darf nur Datenbank-Funktionen)."""
    return bool(session.get("is_db_admin", False))


# ---------------------------------------------------------
# Decorator: Route nur für Voll-Admins
# ---------------------------------------------------------
def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not is_admin():
            if is_db_admin():
                flash(
                    "Voll-Admin-Rechte erforderlich. Aktuell sind Sie als Datenbank-Admin angemeldet.",
                    "warning",
                )
            else:
                flash("Voll-Admin-Rechte erforderlich. Bitte mit dem Admin-Passwort anmelden.", "danger")
            return redirect(url_for("admin_auth.admin_login"))
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------
# Decorator: Route für Voll-Admin ODER DB-Admin
# (für Datenbankseite geeignet)
# ---------------------------------------------------------
def require_database_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not (is_admin() or is_db_admin()):
            flash("Datenbank-Admin oder Admin-Rechte erforderlich.", "danger")
            return redirect(url_for("admin_auth.admin_login"))
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------
# LOGIN
# - Ein Formular, ein Passwortfeld
# - Passwort entscheidet Rolle:
#   ADMIN_PASSWORD -> Volladmin
#   DB_ADMIN_PASSWORD -> DB-Admin
# ---------------------------------------------------------
@bp_admin_auth.route("/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")

        admin_pw_hash = current_app.config.get("ADMIN_PASSWORD_HASH", "")
        db_admin_pw_hash = current_app.config.get("DB_ADMIN_PASSWORD_HASH", "")
        admin_pw_plain = current_app.config.get("ADMIN_PASSWORD", "")
        db_admin_pw_plain = current_app.config.get("DB_ADMIN_PASSWORD", "")

        if not (admin_pw_hash or db_admin_pw_hash or admin_pw_plain or db_admin_pw_plain):
            flash(
                "Weder Admin- noch DB-Admin-Passwort ist konfiguriert.",
                "danger",
            )
            return redirect(url_for("admin_auth.admin_login"))

        # ---------------------------------------------
        # Zielseite nach Login bestimmen (Priorität):
        # 1. Explizites after_login_redirect (z.B. von require_admin gesetzt)
        # 2. Zuletzt besuchte inhaltliche Seite (last_page, gesetzt in __init__.py)
        #    – ausgeschlossen: Login-Seite selbst
        # 3. Fallback: Startseite /pwa/
        # ---------------------------------------------
        target = session.pop("after_login_redirect", None)
        if not target:
            last = session.get("last_page", "")
            _excluded = ("/admin/login", "/admin/logout")
            if last and not any(last.startswith(e) for e in _excluded):
                target = last
        if not target:
            target = url_for("pwa.pwa_index")

        # Rollen immer sauber zurücksetzen
        session.pop("is_admin", None)
        session.pop("is_db_admin", None)

        # Voll-Admin
        admin_ok = bool(admin_pw_hash and verify_password(password, admin_pw_hash)) or (
            bool(admin_pw_plain) and password == admin_pw_plain
        )
        if admin_ok:
            session["is_admin"] = True
            session["is_db_admin"] = False
            session.modified = True
            flash("Admin-Modus aktiviert.", "success")
            current_app.logger.info("Admin-Login erfolgreich: Voll-Admin")
            return redirect(target)

        # DB-Admin
        db_admin_ok = bool(db_admin_pw_hash and verify_password(password, db_admin_pw_hash)) or (
            bool(db_admin_pw_plain) and password == db_admin_pw_plain
        )
        if db_admin_ok:
            session["is_db_admin"] = True
            session["is_admin"] = False
            session.modified = True
            flash("Datenbank-Admin-Modus aktiviert.", "success")
            current_app.logger.info("Admin-Login erfolgreich: Datenbank-Admin")
            return redirect(target)

        flash("Falsches Passwort.", "danger")

    # ✅ WICHTIG:
    # Kein HTML-String mehr, sondern Template mit base.html
    return render_template("admin/login.html")


# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------
@bp_admin_auth.route("/logout", methods=["GET", "POST"])
def admin_logout():
    """
    Beendet jede Admin-Sitzung.
    POST ist die sichere Methode (kein Browser-Prefetch/Cache).
    GET wird aus Kompatibilität ebenfalls akzeptiert.
    """
    session.clear()

    from flask import make_response
    resp = make_response(redirect(url_for("pwa.pwa_index")))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    flash("Admin-Sitzung beendet.", "info")
    return resp