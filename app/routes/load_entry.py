# C:\manifest_fallschirm\app\routes\load_entry.py

from flask import Blueprint, redirect, url_for, flash, session
from app import db
from app.models.load_entry import LoadEntry
from app.models.load import Load

bp_load_entry = Blueprint("load_entry", __name__, url_prefix="/load_entry")


def is_admin() -> bool:
    return bool(session.get("is_admin"))


@bp_load_entry.route("/delete/<int:id>")
def delete(id):
    """
    Löscht einen einzelnen LoadEntry.

    ✅ Sicherheitsregeln (konsistent zum Load-Backend):
      - bezahlte Einträge (paid=True) dürfen niemals gelöscht werden
      - wenn Load completed oder billed ist: nur Admin darf löschen
    """
    entry = LoadEntry.query.get_or_404(id)
    load = Load.query.get_or_404(entry.load_id)

    # paid-entry niemals löschen
    if getattr(entry, "paid", False):
        flash("Dieser Eintrag ist bezahlt und kann nicht gelöscht werden.", "danger")
        return redirect(url_for("load.detail", id=load.id))

    # completed/billed -> nur Admin
    if (load.status == "completed" or load.has_billed_entries) and not is_admin():
        flash("Änderungen an durchgeführten/abgerechneten Loads sind nur im Admin-Bereich möglich.", "danger")
        return redirect(url_for("load.detail", id=load.id))

    db.session.delete(entry)
    db.session.commit()
    flash("Eintrag gelöscht.", "info")
    return redirect(url_for("load.detail", id=load.id))


"""
Hinweis:
Die gesamte Logik zum Hinzufügen, Validieren und Bearbeiten von LoadEntries
bleibt im Load‑Editor:

  /loads/<id>/edit
  /loads/<id>/save

Diese Datei bleibt bewusst minimal.
"""