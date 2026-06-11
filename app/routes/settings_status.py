# C:\manifest_fallschirm\app\routes\settings_status.py

from decimal import Decimal, InvalidOperation
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from app import db, now_local
from app.models.status_definition import StatusDefinition
from app.models.price_audit_log import PriceAuditLog

bp_settings_status = Blueprint(
    "settings_status",
    __name__,
    url_prefix="/settings/status"
)


def parse_decimal(form, field_name):
    """
    Liest ein Dezimalfeld aus dem Formular.
    Erlaubt leere Eingaben -> None.
    Erlaubt Komma oder Punkt als Dezimaltrenner.
    """
    raw = (form.get(field_name) or "").strip()
    if not raw:
        return None
    raw = raw.replace(",", ".")
    try:
        return Decimal(raw)
    except InvalidOperation:
        raise ValueError(f"Ungültiger Zahlenwert in Feld '{field_name}': {raw}")


@bp_settings_status.route("/")
def list_status():
    # Nur aktive Versionen anzeigen, sortiert nach Code + sort_order
    statuses = (
        StatusDefinition.query
        .filter_by(is_active=True)
        .order_by(StatusDefinition.code.asc(), StatusDefinition.sort_order.asc())
        .all()
    )
    return render_template("settings/status_list.html", statuses=statuses)


@bp_settings_status.route("/new", methods=["GET", "POST"])
def new_status():
    if request.method == "POST":
        code = (request.form.get("code") or "").strip()
        label = (request.form.get("label") or "").strip()
        beschreibung = (request.form.get("beschreibung") or "").strip() or None

        if not code or not label:
            flash("Code und Bezeichnung sind Pflichtfelder.", "danger")
            return redirect(request.url)

        try:
            sort_order_raw = (request.form.get("sort_order") or "").strip()
            sort_order = int(sort_order_raw) if sort_order_raw else 100
        except ValueError:
            flash("Sortierreihenfolge muss eine ganze Zahl sein.", "danger")
            return redirect(request.url)

        try:
            preis_1500 = parse_decimal(request.form, "preis_1500")
            preis_3000 = parse_decimal(request.form, "preis_3000")
            preis_4000 = parse_decimal(request.form, "preis_4000")
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(request.url)

        new_def = StatusDefinition(
            code=code,
            label=label,
            beschreibung=beschreibung,
            sort_order=sort_order,
            preis_1500=preis_1500,
            preis_3000=preis_3000,
            preis_4000=preis_4000,
            valid_from=now_local().replace(tzinfo=None),
            is_active=True
        )

        db.session.add(new_def)
        db.session.commit()

        flash("Neuer Status erfolgreich angelegt.", "success")
        return redirect(url_for("settings_status.list_status"))

    return render_template("settings/status_edit.html", status=None)


@bp_settings_status.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_status(id):
    status = StatusDefinition.query.get_or_404(id)

    if request.method == "POST":
        reason = (request.form.get("reason") or "").strip()
        if not reason:
            flash("Bitte Grund für die Änderung angeben.", "danger")
            return redirect(request.url)

        try:
            sort_order_raw = (request.form.get("sort_order") or "").strip()
            sort_order = int(sort_order_raw) if sort_order_raw else status.sort_order
        except ValueError:
            flash("Sortierreihenfolge muss eine ganze Zahl sein.", "danger")
            return redirect(request.url)

        try:
            preis_1500 = parse_decimal(request.form, "preis_1500")
            preis_3000 = parse_decimal(request.form, "preis_3000")
            preis_4000 = parse_decimal(request.form, "preis_4000")
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(request.url)

        # Alte Version schließen
        status.valid_to = now_local().replace(tzinfo=None)
        status.is_active = False

        # Neue Version anlegen (gleicher Code, neue Werte)
        new_def = StatusDefinition(
            code=status.code,
            label=(request.form.get("label") or "").strip() or status.label,
            beschreibung=(request.form.get("beschreibung") or "").strip() or None,
            sort_order=sort_order,
            preis_1500=preis_1500,
            preis_3000=preis_3000,
            preis_4000=preis_4000,
            valid_from=now_local().replace(tzinfo=None),
            is_active=True
        )

        db.session.add(new_def)

        # Audit-Log
        log = PriceAuditLog(
            user="admin",  # später ersetzen durch echten User
            action=f"Status '{status.code}' geändert",
            old_value=str({
                "preis_1500": str(status.preis_1500) if status.preis_1500 is not None else None,
                "preis_3000": str(status.preis_3000) if status.preis_3000 is not None else None,
                "preis_4000": str(status.preis_4000) if status.preis_4000 is not None else None,
            }),
            new_value=str({
                "preis_1500": str(new_def.preis_1500) if new_def.preis_1500 is not None else None,
                "preis_3000": str(new_def.preis_3000) if new_def.preis_3000 is not None else None,
                "preis_4000": str(new_def.preis_4000) if new_def.preis_4000 is not None else None,
            }),
            reason=reason
        )
        db.session.add(log)

        db.session.commit()

        flash("Status erfolgreich aktualisiert.", "success")
        return redirect(url_for("settings_status.list_status"))

    return render_template("settings/status_edit.html", status=status)
