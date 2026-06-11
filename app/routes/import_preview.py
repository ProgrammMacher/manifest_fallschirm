# C:\manifest_fallschirm\app\routes\import_preview.py

import os
import json
import uuid
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
)
from werkzeug.utils import secure_filename

from app.services.person_import_service import PersonImportService
from app.services.person_export_service import PersonExportService


bp = Blueprint("import_preview", __name__, url_prefix="/import")

def _upload_folder() -> str:
    configured = current_app.config.get("UPLOAD_FOLDER")
    if configured:
        return str(configured)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))


def _session_data_folder() -> str:
    configured = current_app.config.get("SESSION_FILE_DIR")
    if configured:
        return str(configured)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "session_data"))

ALLOWED_EXTENSIONS = {"xlsx"}


def allowed_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def save_session_data(data: list) -> str:
    """
    Speichert große Datenmengen in einer Datei statt im Cookie.
    Wandelt nicht-serialisierbare Objekte (z.B. datetime/date)
    automatisch in Strings um.
    """

    def convert(obj):
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        return str(obj)

    session_data_folder = _session_data_folder()
    os.makedirs(session_data_folder, exist_ok=True)
    sid = uuid.uuid4().hex
    path = os.path.join(session_data_folder, sid)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, default=convert)

    return sid


def load_session_data(sid: str) -> list:
    """
    Lädt Session-Daten aus Datei.
    """
    if not sid:
        return []

    path = os.path.join(_session_data_folder(), sid)
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# ---------------------------------------------------------
# 0) DOWNLOAD DER VORLAGE
# ---------------------------------------------------------
@bp.route("/vorlage")
def download_template():
    """
    Liefert die vertikale Import-Vorlage.
    """
    return PersonExportService.export_vertical_import_template()


# ---------------------------------------------------------
# 1) UPLOAD-SEITE
# ---------------------------------------------------------
@bp.route("/", methods=["GET"])
def index():
    return render_template("import/index.html")


# ---------------------------------------------------------
# 2) VORSCHAU-SEITE
# ---------------------------------------------------------
@bp.route("/preview", methods=["GET", "POST"])
def preview():

    # -----------------------------------------------------
    # GET → Vorschau anzeigen (mit Filter)
    # -----------------------------------------------------
    if request.method == "GET":
        sid = session.get("import_sid")
        rows = load_session_data(sid)
        import_mode = session.get("import_mode", "vertical")

        filter_mode = request.args.get("filter", "all")

        if filter_mode == "errors":
            rows = [r for r in rows if r.get("field_errors")]
        elif filter_mode == "warnings":
            rows = [r for r in rows if r.get("field_warnings")]
        elif filter_mode == "duplicates":
            rows = [r for r in rows if r.get("is_duplicate")]
        elif filter_mode == "valid":
            rows = [
                r for r in rows
                if not r.get("field_errors") and not r.get("is_duplicate")
            ]

        return render_template(
            "import/preview.html",
            rows=rows,
            filter_mode=filter_mode,
            import_mode=import_mode,
        )

    # -----------------------------------------------------
    # POST → Datei wurde hochgeladen
    # -----------------------------------------------------
    file = request.files.get("file")
    import_mode = (request.form.get("import_mode") or "vertical").strip().lower()
    if import_mode not in {"vertical", "horizontal"}:
        import_mode = "vertical"

    if not file or not file.filename:
        flash("Keine Datei ausgewählt.", "danger")
        return redirect(url_for("import_preview.index"))

    if not allowed_file(file.filename):
        flash("Nur .xlsx-Dateien sind erlaubt.", "danger")
        return redirect(url_for("import_preview.index"))

    # Datei speichern
    upload_folder = _upload_folder()
    os.makedirs(upload_folder, exist_ok=True)
    safe_name = secure_filename(file.filename)
    filepath = os.path.join(upload_folder, safe_name)
    file.save(filepath)

    # Datei einlesen
    try:
        if import_mode == "horizontal":
            preview_rows, error = PersonImportService.load_preview_horizontal(filepath)
        else:
            preview_rows, error = PersonImportService.load_preview(filepath)
    except Exception as e:
        flash(f"Fehler beim Einlesen der Datei: {e}", "danger")
        return redirect(url_for("import_preview.index"))

    if error:
        flash(error, "danger")
        return redirect(url_for("import_preview.index"))

    # Session-Daten speichern
    sid = save_session_data(preview_rows)
    session["import_sid"] = sid
    session["import_mode"] = import_mode

    return render_template(
        "import/preview.html",
        rows=preview_rows,
        filter_mode="all",
        import_mode=import_mode,
    )
