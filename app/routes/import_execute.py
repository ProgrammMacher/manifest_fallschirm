# C:\manifest_fallschirm\app\routes\import_execute.py

import os
import json
from datetime import datetime, date
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app
from app.models.person import Person
from app import db
from app.services.person_import_service import PersonImportService

bp = Blueprint("import_execute", __name__, url_prefix="/import")

def _session_data_folder() -> str:
    configured = current_app.config.get("SESSION_FILE_DIR")
    if configured:
        return str(configured)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "session_data"))


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
# DATUMS-FIX: Strings wieder in echte date-Objekte wandeln
# ---------------------------------------------------------
def parse_date_from_string(value):
    if not value:
        return None

    # Bereits ein echtes date-Objekt?
    if isinstance(value, date):
        return value

    s = str(value).strip()

    # ISO: 1987-03-14
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        pass

    # Deutsch: 14.03.1987
    try:
        return datetime.strptime(s, "%d.%m.%Y").date()
    except Exception:
        pass

    # Deutsch kurz: 14.3.87
    try:
        return datetime.strptime(s, "%d.%m.%y").date()
    except Exception:
        pass

    return None


@bp.route("/execute", methods=["POST"])
def execute():
    """
    Führt den finalen Import aus.
    - Erkannte Doppelungen werden immer in den bestehenden Datensatz gemerged.
    - Die Feldwahl kommt aus der Vorschau (Alt/Neu pro Feld).
    - Namensänderungen speichern den bisherigen Namen als Ursprungsname.
    """

    sid = session.get("import_sid")
    import_mode = session.get("import_mode", "vertical")
    preview_rows = load_session_data(sid)
    match_indexes = PersonImportService.build_match_indexes(Person.query.all())

    if not preview_rows:
        flash("Keine Daten zum Import vorhanden.", "danger")
        return redirect(url_for("import_preview.index"))

    imported = 0
    updated = 0
    skipped = 0
    errors = []

    for entry in preview_rows:
        cleaned = entry.get("cleaned_data") or {}
        field_errors = entry.get("field_errors") or {}
        notes = entry.get("notes") or []
        is_valid = entry.get("is_valid", True)

        # Nicht-blockierende Fehler aus Alt-Sessions tolerieren.
        # Beispiel: unplausible IBAN wurde bereits geleert und soll Import nicht stoppen.
        non_blocking_error_fields = {"iban"}
        blocking_field_errors = {
            key: value for key, value in field_errors.items()
            if key not in non_blocking_error_fields
        }

        # Harte Fehler → überspringen
        if blocking_field_errors or (not is_valid and not field_errors):
            skipped += 1
            errors.append({
                "column": entry.get("column"),
                "notes": notes,
                "data": cleaned
            })
            continue

        # ---------------------------------------------------------
        # Prüfen, ob Person existiert
        # ---------------------------------------------------------
        existing, _duplicate_reason = PersonImportService.find_existing_person(
            cleaned,
            match_indexes,
            import_mode=import_mode,
        )

        # ---------------------------------------------------------
        # 1) Neue Person → vollständig anlegen
        # ---------------------------------------------------------
        if not existing:
            person = Person()

            for field, value in cleaned.items():

                # Datumskonvertierung
                if field in ("birthdate", "liability_waiver_date", "teacher_license_expires"):
                    value = parse_date_from_string(value)

                if hasattr(Person, field):
                    setattr(person, field, value)

            db.session.add(person)
            db.session.flush()
            PersonImportService.register_person_in_match_indexes(person, match_indexes)
            imported += 1
            continue

        # ---------------------------------------------------------
        # 2) Bestehende Person
        # - Auswahl pro Feld kommt aus der Vorschau
        # - Eine zweite Person wird in diesem Fall nie angelegt
        # ---------------------------------------------------------
        person = existing
        previous_name = person.current_name
        conflict_notes = []
        merge_candidates = {
            candidate.get("field"): candidate
            for candidate in (entry.get("merge_candidates") or [])
            if candidate.get("field")
        }
        applied_fields = []

        for field, new_value in cleaned.items():

            if not hasattr(Person, field):
                continue

            if field in {"id", "original_name"}:
                continue

            # Datumskonvertierung
            if field in ("birthdate", "liability_waiver_date", "teacher_license_expires"):
                new_value = parse_date_from_string(new_value)

            old_value = getattr(person, field, None)
            candidate = merge_candidates.get(field)

            if candidate:
                choice_key = f"merge_choice__{entry.get('entry_key')}__{field}"
                selected_choice = request.form.get(choice_key) or candidate.get("default_choice") or "existing"

                if selected_choice == "import" and candidate.get("import_allowed", True):
                    chosen_value = new_value
                else:
                    chosen_value = old_value
                    if selected_choice == "import" and not candidate.get("import_allowed", True):
                        conflict_notes.append(f"{candidate.get('label', field)}: Importwert leer, bisheriger Wert bleibt erhalten")
                    else:
                        conflict_notes.append(f"{candidate.get('label', field)}: bisheriger Wert bleibt erhalten")
            else:
                if PersonImportService.values_equal(field, old_value, new_value):
                    continue
                if old_value in (None, "") and new_value not in (None, ""):
                    chosen_value = new_value
                else:
                    chosen_value = old_value

            if PersonImportService.values_equal(field, old_value, chosen_value):
                continue

            setattr(person, field, chosen_value)
            applied_fields.append(field)

        person.remember_original_name(previous_name)
        if person.original_name and person.current_name.casefold() != previous_name.casefold():
            conflict_notes.append(f"Ursprungsname gespeichert: {person.original_name}")

        if applied_fields:
            updated += 1
        elif entry.get("is_duplicate") and not conflict_notes:
            conflict_notes.append("Kein Feld wurde geändert; bestehender Datensatz bleibt unverändert")

        if conflict_notes:
            errors.append({
                "column": entry.get("column"),
                "notes": conflict_notes,
                "data": cleaned
            })

        db.session.add(person)
        db.session.flush()
        PersonImportService.register_person_in_match_indexes(person, match_indexes)

    db.session.commit()

    # Session leeren
    session.pop("import_sid", None)
    session.pop("import_mode", None)

    return render_template(
        "import/execute.html",
        imported=imported,
        updated=updated,
        skipped=skipped,
        errors=errors,
        import_mode=import_mode,
    )
