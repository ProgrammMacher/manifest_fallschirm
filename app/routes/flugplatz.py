# C:\manifest_fallschirm\app\routes\flugplatz.py

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)
from functools import wraps
from app import db
from app.models.flugplatz import Flugplatz

bp = Blueprint("flugplatz", __name__, url_prefix="/flugplatz")


# =========================================================
# Admin-Decorator
# =========================================================
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Diese Aktion ist nur für Administratoren erlaubt.", "danger")
            return redirect(url_for("flugplatz.list_flugplaetze"))
        return fn(*args, **kwargs)
    return wrapper


# =========================================================
# Liste aller Flugplätze (READ-ONLY für Nicht-Admins)
# =========================================================
@bp.route("/")
def list_flugplaetze():
    plaetze = Flugplatz.query.order_by(Flugplatz.name.asc()).all()
    return render_template("flugplatz/list.html", plaetze=plaetze)


# =========================================================
# Archivierte Flugplätze anzeigen (READ-ONLY für Nicht-Admins)
# =========================================================
@bp.route("/archiv")
def archiv():
    plaetze = (
        Flugplatz.query
        .filter(Flugplatz.deleted_at.isnot(None))
        .order_by(Flugplatz.name.asc())
        .all()
    )
    return render_template("flugplatz/archiv.html", plaetze=plaetze)


# =========================================================
# Neuen Flugplatz anlegen (ADMIN ONLY)
# =========================================================
@bp.route("/new", methods=["GET", "POST"])
@admin_required
def new_flugplatz():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Name ist erforderlich.", "danger")
            return redirect(url_for("flugplatz.new_flugplatz"))

        platz = Flugplatz(
            name=name,
            is_home_airfield=bool(request.form.get("is_home")),
            active=bool(request.form.get("active", True)),
        )
        db.session.add(platz)
        db.session.commit()

        flash("Flugplatz wurde angelegt.", "success")
        return redirect(url_for("flugplatz.list_flugplaetze"))

    return render_template("flugplatz/edit.html", platz=Flugplatz())


# =========================================================
# Flugplatz bearbeiten
# - GET: sichtbar für alle (READ-ONLY für Nicht-Admins)
# - POST: ADMIN ONLY
# =========================================================
@bp.route("/<int:id>/edit", methods=["GET", "POST"])
def edit_flugplatz(id):
    platz = Flugplatz.query.get_or_404(id)

    if request.method == "POST":
        if not session.get("is_admin"):
            flash("Keine Berechtigung zum Speichern.", "danger")
            return redirect(url_for("flugplatz.edit_flugplatz", id=id))

        platz.name = request.form.get("name", platz.name).strip()
        platz.is_home_airfield = bool(request.form.get("is_home"))
        platz.active = bool(request.form.get("active"))

        db.session.commit()
        flash("Flugplatz gespeichert.", "success")
        return redirect(url_for("flugplatz.list_flugplaetze"))

    return render_template("flugplatz/edit.html", platz=platz)


# =========================================================
# Flugplatz archivieren (SOFT DELETE – ADMIN ONLY)
# =========================================================
@bp.route("/<int:id>/delete", methods=["POST"])
@admin_required
def delete_flugplatz(id):
    platz = Flugplatz.query.get_or_404(id)

    if platz.is_home_airfield:
        flash("Der Heimatflugplatz kann nicht archiviert werden.", "warning")
        return redirect(url_for("flugplatz.list_flugplaetze"))

    platz.archive(reason="archived_via_ui")
    db.session.commit()

    flash("Flugplatz wurde archiviert.", "success")
    return redirect(url_for("flugplatz.list_flugplaetze"))


# =========================================================
# Flugplatz wiederherstellen (ADMIN ONLY)
# =========================================================
@bp.route("/<int:id>/restore", methods=["POST"])
@admin_required
def restore(id):
    platz = Flugplatz.query.get_or_404(id)
    platz.restore()
    db.session.commit()

    flash("Flugplatz wurde wiederhergestellt.", "success")
    return redirect(url_for("flugplatz.archiv"))


# =========================================================
# Flugplatz endgültig löschen (HARD DELETE – ADMIN ONLY)
# =========================================================
@bp.route("/<int:id>/hard_delete", methods=["POST"])
@admin_required
def hard_delete(id):
    platz = Flugplatz.query.get_or_404(id)

    if not platz.can_hard_delete():
        flash(
            "Endgültiges Löschen nicht möglich – es existieren noch zugehörige Daten.",
            "danger",
        )
        return redirect(url_for("flugplatz.archiv"))

    if platz.is_home_airfield:
        flash("Der Heimatflugplatz kann nicht gelöscht werden.", "danger")
        return redirect(url_for("flugplatz.archiv"))

    db.session.delete(platz)
    db.session.commit()

    flash("Flugplatz wurde endgültig gelöscht.", "warning")
    return redirect(url_for("flugplatz.archiv"))