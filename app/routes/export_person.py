# app/routes/export_person.py

from flask import Blueprint, request, flash, redirect, url_for
from sqlalchemy import or_
from datetime import date
from app.services.person_export_service import PersonExportService
from app.models.person import Person

bp_export_person = Blueprint("export_person", __name__, url_prefix="/export/persons")


# ---------------------------------------------------------
# 1) Vertikale Import-Vorlage erzeugen & herunterladen
# ---------------------------------------------------------
@bp_export_person.route("/import-template")
def export_import_template():
    """
    Exportiert die vertikale Import-Vorlage.
    Wichtig: Der Service liefert bereits ein send_file()-Response-Objekt zurück.
    Deshalb darf hier KEIN send_file() mehr aufgerufen werden.
    """
    return PersonExportService.export_vertical_import_template()


# ---------------------------------------------------------
# 2) Personenliste als Excel exportieren
# ---------------------------------------------------------
@bp_export_person.route("/excel")
def export_persons_excel():
    """
    Exportiert Personen als Excel-Datei.
    Berücksichtigt Suche, Filter und Sortierung wie die Personenliste.
    """

    # Parameter aus der Personenliste übernehmen
    search = request.args.get("search", "").strip()
    # Neue Logik: filters=value1,value2,value3
    filters_str = request.args.get("filters", "").strip()
    filters_list = [f.strip() for f in filters_str.split(",") if f.strip()] if filters_str else []
    
    sort = request.args.get("sort", "last_name")
    direction = request.args.get("direction", "asc")

    query = Person.query

    # Standard: aktive; Archiv: nur archivierte
    if "archived" in filters_list:
        query = query.filter(Person.deleted_at.isnot(None))
    else:
        query = query.filter(Person.deleted_at.is_(None))

    # -----------------------------------------------------
    # Suche
    # -----------------------------------------------------
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Person.first_name.ilike(like),
                Person.last_name.ilike(like),
                Person.phone.ilike(like),
                Person.email.ilike(like),
            )
        )

    # -----------------------------------------------------
    # Filter (mehrere mit AND kombiniert)
    # -----------------------------------------------------
    for f in filters_list:
        if f == "members":
            query = query.filter(Person.is_member.is_(True))
        elif f == "partner":
            query = query.filter(Person.is_partner_verein.is_(True))
        elif f == "tandem":
            query = query.filter(Person.is_tandem_guest.is_(True))
        elif f == "teacher":
            query = query.filter(Person.is_teacher.is_(True))
        elif f == "aff_teacher":
            query = query.filter(Person.is_aff_teacher.is_(True))
        elif f == "student":
            query = query.filter(Person.is_student.is_(True))
        elif f == "video":
            query = query.filter(Person.is_video.is_(True))
        elif f == "aff_student":
            query = query.filter(Person.is_aff_student.is_(True))
        elif f == "tandemmaster":
            query = query.filter(Person.is_tandemmaster.is_(True))
        elif f == "guest":
            query = query.filter(
                Person.is_member.is_(False),
                Person.is_tandem_guest.is_(False),
                Person.is_partner_verein.is_(False),
            )
        elif f == "liability_ok":
            query = query.filter(Person.liability_waiver_date.isnot(None))
        elif f == "liability_bad":
            current_year = date.today().year
            query = query.filter(
                or_(
                    Person.liability_waiver_date.is_(None),
                    Person.liability_waiver_date < date(current_year, 1, 1),
                )
            )
        elif f == "weight_bad":
            persons_all = query.all()
            bad_ids = []
            for p in persons_all:
                if p.weight_kg is None:
                    continue
                if p.is_tandem_guest:
                    if p.weight_kg < 40 or p.weight_kg > 90:
                        bad_ids.append(p.id)
                else:
                    if p.weight_kg < 50 or p.weight_kg > 100:
                        bad_ids.append(p.id)
            query = query.filter(Person.id.in_(bad_ids)) if bad_ids else query.filter(False)

    # -----------------------------------------------------
    # Sortierung
    # -----------------------------------------------------
    valid_sort_fields = {
        "last_name": Person.last_name,
        "first_name": Person.first_name,
        "is_member": Person.is_member,
        "is_video": Person.is_video,
        "is_tandem_guest": Person.is_tandem_guest,
        "weight_kg": Person.weight_kg,
        "liability_waiver_date": Person.liability_waiver_date,
    }

    primary = valid_sort_fields.get(sort, Person.last_name)
    if direction == "desc":
        primary = primary.desc()

    persons = query.order_by(primary, Person.last_name.asc(), Person.first_name.asc()).all()

    # -----------------------------------------------------
    # Excel erzeugen
    # -----------------------------------------------------
    try:
        # WICHTIG:
        # Der Service liefert bereits ein send_file()-Response-Objekt zurück.
        return PersonExportService.export_persons_excel(persons)

    except Exception as e:
        flash(f"Fehler beim Erstellen der Excel-Datei: {e}", "danger")
        return redirect(url_for("person.list_persons"))
