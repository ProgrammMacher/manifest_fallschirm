# C:\manifest_fallschirm\app\routes\aircraft.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from app import db, now_local
from app.models.aircraft import Aircraft
from app.models.load import Load
from app.routes.admin_auth import require_admin

bp_aircraft = Blueprint("aircraft", __name__, url_prefix="/aircraft")


# ---------------------------------------------------------
# Liste aller Flugzeuge
# ---------------------------------------------------------
@bp_aircraft.route("/")
def list_aircraft():
    """Zeigt aktive, inaktive und archivierte Flugzeuge."""

    aircraft_active = (
        Aircraft.query
        .filter(Aircraft.deleted_at.is_(None), Aircraft.active.is_(True))
        .order_by(Aircraft.registration.asc())
        .all()
    )

    aircraft_inactive = (
        Aircraft.query
        .filter(Aircraft.deleted_at.is_(None), Aircraft.active.is_(False))
        .order_by(Aircraft.registration.asc())
        .all()
    )

    aircraft_archived = (
        Aircraft.query
        .filter(Aircraft.deleted_at.is_not(None))
        .order_by(Aircraft.registration.asc())
        .all()
    )

    return render_template(
        "aircraft_list.html",
        aircraft_active=aircraft_active,
        aircraft_inactive=aircraft_inactive,
        aircraft_archived=aircraft_archived,
        now=now_local().replace(tzinfo=None)
    )


# ---------------------------------------------------------
# Neues Flugzeug anlegen
# ---------------------------------------------------------
@bp_aircraft.route("/new", methods=["GET", "POST"])
@require_admin
def new_aircraft():
    """Erstellt ein neues Flugzeug."""

    if request.method == "POST":
        type_ = (request.form.get("type") or "").strip()
        registration = (request.form.get("registration") or "").strip()
        seats_raw = request.form.get("seats") or "0"
        default_height_raw = request.form.get("default_height") or "3000"

        active = "active" in request.form

        try:
            seats_int = int(seats_raw)
        except ValueError:
            seats_int = 0
        seats = max(1, min(130, seats_int))

        try:
            default_height = int(default_height_raw)
        except ValueError:
            default_height = 3000

        if default_height not in (1500, 3000, 4000):
            flash("Ungültige Standardhöhe.", "danger")
            return render_template("aircraft_form.html")

        if not type_ or not registration:
            flash("Typ und Kennung sind Pflichtfelder.", "danger")
            return render_template("aircraft_form.html")

        aircraft = Aircraft(
            type=type_,
            registration=registration,
            seats=seats,
            active=active,
            default_height=default_height
        )

        db.session.add(aircraft)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Ein Flugzeug mit dieser Kennung existiert bereits.", "danger")
            return render_template("aircraft_form.html")
        except Exception as e:
            db.session.rollback()
            flash(f"Fehler beim Speichern: {e}", "danger")
            return render_template("aircraft_form.html")

        flash("Flugzeug erfolgreich angelegt.", "success")
        return redirect(url_for("aircraft.list_aircraft"))

    return render_template("aircraft_form.html")


# ---------------------------------------------------------
# Flugzeug bearbeiten
# ---------------------------------------------------------
@bp_aircraft.route("/<int:aircraft_id>/edit", methods=["GET", "POST"])
@require_admin
def edit_aircraft(aircraft_id):
    """Bearbeitet ein bestehendes Flugzeug."""

    aircraft = Aircraft.query.get_or_404(aircraft_id)

    if request.method == "POST":
        type_ = (request.form.get("type") or "").strip()
        registration = (request.form.get("registration") or "").strip()
        seats_raw = request.form.get("seats") or "0"
        default_height_raw = request.form.get("default_height") or "3000"

        active = "active" in request.form

        try:
            seats_int = int(seats_raw)
        except ValueError:
            seats_int = 0
        seats = max(1, min(130, seats_int))

        try:
            default_height = int(default_height_raw)
        except ValueError:
            default_height = 3000

        if default_height not in (1500, 3000, 4000):
            flash("Ungültige Standardhöhe.", "danger")
            return render_template("aircraft_form.html", aircraft=aircraft)

        if not type_ or not registration:
            flash("Typ und Kennung sind Pflichtfelder.", "danger")
            return render_template("aircraft_form.html", aircraft=aircraft)

        aircraft.type = type_
        aircraft.registration = registration
        aircraft.seats = seats
        aircraft.active = active
        aircraft.default_height = default_height

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Ein Flugzeug mit dieser Kennung existiert bereits.", "danger")
            return render_template("aircraft_form.html", aircraft=aircraft)
        except Exception as e:
            db.session.rollback()
            flash(f"Fehler beim Speichern: {e}", "danger")
            return render_template("aircraft_form.html", aircraft=aircraft)

        flash("Flugzeug gespeichert.", "success")
        return redirect(url_for("aircraft.list_aircraft"))

    return render_template("aircraft_form.html", aircraft=aircraft)
# ---------------------------------------------------------
# Flugzeug archivieren (Softdelete)
# ---------------------------------------------------------
@bp_aircraft.route("/<int:aircraft_id>/archive", methods=["POST"])
@require_admin
def archive_aircraft(aircraft_id):
    aircraft = Aircraft.query.get_or_404(aircraft_id)

    if aircraft.is_archived:
        flash("Flugzeug ist bereits archiviert.", "info")
        return redirect(url_for("aircraft.list_aircraft"))

    aircraft.archive(reason="archived_via_ui")
    db.session.commit()

    flash(f"Flugzeug '{aircraft.registration}' wurde archiviert.", "warning")
    return redirect(url_for("aircraft.list_aircraft"))


# ---------------------------------------------------------
# Flugzeug wiederherstellen
# ---------------------------------------------------------
@bp_aircraft.route("/<int:aircraft_id>/restore", methods=["POST"])
@require_admin
def restore_aircraft(aircraft_id):
    aircraft = Aircraft.query.get_or_404(aircraft_id)

    if aircraft.is_active:
        flash("Flugzeug ist bereits aktiv.", "info")
        return redirect(url_for("aircraft.list_aircraft"))

    aircraft.restore()
    db.session.commit()

    flash(f"Flugzeug '{aircraft.registration}' wurde wiederhergestellt.", "success")
    return redirect(url_for("aircraft.list_aircraft"))


# ---------------------------------------------------------
# Flugzeug ersetzen – Auswahlseite
# ---------------------------------------------------------
@bp_aircraft.route("/<int:aircraft_id>/replace", methods=["GET"])
@require_admin
def replace_aircraft(aircraft_id):
    aircraft = Aircraft.query.get_or_404(aircraft_id)

    loads = (
        Load.query
        .filter_by(aircraft_id=aircraft_id)
        .order_by(Load.created_at.desc())
        .all()
    )

    other_aircraft = (
        Aircraft.query
        .filter(
            Aircraft.id != aircraft_id,
            Aircraft.deleted_at.is_(None),
        )
        .order_by(Aircraft.registration.asc())
        .all()
    )

    return render_template(
        "aircraft_replace.html",
        aircraft=aircraft,
        loads=loads,
        other_aircraft=other_aircraft,
    )


# ---------------------------------------------------------
# Flugzeug ersetzen – Aktion
# ---------------------------------------------------------
@bp_aircraft.route("/<int:aircraft_id>/replace_execute", methods=["POST"])
@require_admin
def replace_aircraft_execute(aircraft_id):
    aircraft = Aircraft.query.get_or_404(aircraft_id)

    new_aircraft_id_raw = request.form.get("new_aircraft_id")
    if not new_aircraft_id_raw:
        flash("Bitte ein Ersatzflugzeug auswählen.", "danger")
        return redirect(url_for("aircraft.replace_aircraft", aircraft_id=aircraft_id))

    try:
        new_aircraft_id = int(new_aircraft_id_raw)
    except ValueError:
        flash("Ungültige Auswahl für Ersatzflugzeug.", "danger")
        return redirect(url_for("aircraft.replace_aircraft", aircraft_id=aircraft_id))

    new_aircraft = Aircraft.query.get_or_404(new_aircraft_id)

    loads = Load.query.filter_by(aircraft_id=aircraft_id).all()
    for load in loads:
        load.aircraft_id = new_aircraft.id

    db.session.commit()

    flash(
        f"Flugzeug '{aircraft.registration}' wurde in allen Loads durch "
        f"'{new_aircraft.registration}' ersetzt.",
        "success",
    )
    return redirect(url_for("aircraft.list_aircraft"))


# ---------------------------------------------------------
# Flugzeug HARDDELETE (nur Admin + wenn nie verwendet)
# ---------------------------------------------------------
@bp_aircraft.route("/<int:aircraft_id>/hard_delete", methods=["POST"])
@require_admin
def hard_delete_aircraft(aircraft_id):
    aircraft = Aircraft.query.get_or_404(aircraft_id)

    if not aircraft.can_hard_delete():
        flash(
            f"Harddelete nicht möglich: Flugzeug '{aircraft.registration}' "
            f"wird in Loads verwendet.",
            "danger",
        )
        return redirect(url_for("aircraft.list_aircraft"))

    db.session.delete(aircraft)
    db.session.commit()

    flash(f"Flugzeug '{aircraft.registration}' wurde endgültig gelöscht.", "success")
    return redirect(url_for("aircraft.list_aircraft"))
