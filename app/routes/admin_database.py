from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    session,
    send_file,
    current_app,
)
import os
from datetime import datetime

from app.helpers.db_operations import (
    create_database_backup,
    create_new_working_database,
    create_year_archive,
)
from app.helpers.app_settings import (
    get_last_backup,
    get_last_archive,
    get_last_import,
)

# ✅ Blueprint-Name MUSS exakt so heißen
bp = Blueprint(
    "admin_database",
    __name__,
    url_prefix="/admin/database",
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _runtime_data_dir() -> str:
    db_uri = str(current_app.config.get("SQLALCHEMY_DATABASE_URI", ""))
    if db_uri.startswith("sqlite:///"):
        return os.path.dirname(db_uri[len("sqlite:///"):])
    return os.path.join(PROJECT_ROOT, "data")


def _runtime_db_path() -> str:
    return os.path.join(_runtime_data_dir(), "manifest.db")


def _database_admin_required():
    """
    Zugriff nur für Admins oder DB-Admins.
    Merkt sich die Zielseite und leitet ggf. zum Login weiter.
    """
    if session.get("is_admin") or session.get("is_db_admin"):
        return None  # ✅ Zugriff erlaubt

    # ✅ HIER: Zielseite merken, damit nach Login zurück zur Datenbank geleitet wird
    session["after_login_redirect"] = request.path

    flash(
        "Für den Zugriff auf die Datenbank ist ein Admin- oder "
        "Datenbank-Admin-Passwort erforderlich.",
        "warning",
    )
    return redirect(url_for("admin_auth.admin_login"))


# -------------------------------------------------
# ✅ Public Backup (UNKritisch)
# -------------------------------------------------
@bp.route("/backup-public", methods=["POST"])
def backup_public():
    """
    Öffentliche Datensicherung (UNKritisch):
    - ohne Admin / DB-Admin möglich
    - erstellt eine Sicherungskopie unter data/backup
    - zeigt Erfolgsmeldung
    - bleibt auf der aktuellen Seite (Redirect auf Referrer)
    """
    try:
        # create_database_backup legt in eurem Setup im Ordner data/backup ab
        # (siehe Projektstruktur und bestehende Backups). [2](https://onedrive.live.com/?id=1b4017a3-1a1a-40e8-9457-5706e18f1c70&cid=222cf049bc54ff98&web=1)
        backup_path = create_database_backup(created_by="user")

        # Optional: Dateiname für die Meldung hübsch machen
        filename = os.path.basename(str(backup_path)) if backup_path else "Backup erstellt"

        flash(f"✅ Datensicherung erfolgreich erstellt: {filename}", "success")

    except Exception as e:
        # Falls doch etwas schiefgeht (z.B. Dateisperre), bekommt der User Feedback.
        flash(f"❌ Datensicherung fehlgeschlagen: {e}", "danger")

    # Zurück zur Seite, von der der Button geklickt wurde
    return redirect(request.referrer or url_for("pwa.pwa_index"))


# -------------------------------------------------
# Übersicht
# -------------------------------------------------
@bp.route("/")
def index():
    resp = _database_admin_required()
    if resp:
        return resp

    return render_template(
        "admin/database.html",
        last_backup=get_last_backup(),
        last_archive=get_last_archive(),
        last_import=get_last_import(),
    )


# -------------------------------------------------
# Backup
# -------------------------------------------------
@bp.route("/backup", methods=["POST"])
def backup():
    resp = _database_admin_required()
    if resp:
        return resp

    try:
        create_database_backup(created_by="admin")
        flash("Backup erfolgreich erstellt.", "success")
    except Exception as e:
        flash(f"Backup fehlgeschlagen: {e}", "danger")
    return redirect(url_for("admin_database.index"))


# -------------------------------------------------
# Neue Arbeitsdatenbank
# -------------------------------------------------
@bp.route("/new-db", methods=["POST"])
def new_db():
    resp = _database_admin_required()
    if resp:
        return resp

    create_new_working_database(created_by="admin")
    flash("Neue Arbeitsdatenbank erstellt.", "success")
    return redirect(url_for("admin_database.index"))


# -------------------------------------------------
# Jahresarchiv
# -------------------------------------------------
@bp.route("/archive", methods=["POST"])
def archive():
    resp = _database_admin_required()
    if resp:
        return resp

    try:
        year = int(request.form["year"])
    except (KeyError, ValueError):
        flash("Ungültiges Jahr.", "danger")
        return redirect(url_for("admin_database.index"))

    create_year_archive(year, created_by="admin")
    flash(f"Jahresarchiv {year} erstellt.", "success")
    return redirect(url_for("admin_database.index"))


# -------------------------------------------------
# ✅ Export: komplette DB herunterladen
# -------------------------------------------------
@bp.route("/export")
def export_db():
    resp = _database_admin_required()
    if resp:
        return resp

    db_path = _runtime_db_path()

    if not os.path.exists(db_path):
        flash("Keine aktive Datenbank gefunden.", "danger")
        return redirect(url_for("admin_database.index"))

    from app import now_local
    ts = now_local().strftime("%Y-%m-%d")
    filename = f"manifest_export_{ts}.db"

    return send_file(
        db_path,
        as_attachment=True,
        download_name=filename,
    )


# -------------------------------------------------
# ✅ Import: DB ersetzen
# -------------------------------------------------
@bp.route("/import", methods=["POST"])
def import_db():
    resp = _database_admin_required()
    if resp:
        return resp

    if "db_file" not in request.files:
        flash("Keine Datei ausgewählt.", "danger")
        return redirect(url_for("admin_database.index"))

    file = request.files["db_file"]
    if not file.filename.lower().endswith(".db"):
        flash("Bitte eine .db-Datei auswählen.", "danger")
        return redirect(url_for("admin_database.index"))

    data_dir = _runtime_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    target_db = _runtime_db_path()

    # ✅ Sicherheits-Backup vor Überschreiben
    try:
        if os.path.exists(target_db):
            create_database_backup(created_by="admin")

        file.save(target_db)
        flash("Datenbank erfolgreich geladen.", "success")
    except Exception as e:
        flash(f"Datenbank laden fehlgeschlagen: {e}", "danger")
    return redirect(url_for("admin_database.index"))