# C:\manifest_fallschirm\app\routes\person.py

import os
import re
from io import BytesIO
import base64
import hashlib
from datetime import timedelta

from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, send_file
from sqlalchemy import or_, and_, case
from datetime import datetime, date
from app import db
from app.models.person import Person  # WICHTIG: Model kommt aus models/, nicht hier definieren!
from app.models.mobile_person_intake_draft import (
    MOBILE_PERSON_INTAKE_MODE_JUMPER,
    MOBILE_PERSON_INTAKE_STATUS_OPEN,
    MOBILE_PERSON_INTAKE_STATUS_SUBMITTED,
    MobilePersonIntakeDraft,
)
from app.models.billing_config import BillingConfig
from app.security.admin import admin_required, is_admin
from app.services.billing_service import _image_to_data_uri
from app.services.display_service import build_local_qr_url, generate_qr_png_buffer
from app.services.mobile_person_intake_service import (
    accept_draft,
    create_draft,
    expire_draft_if_needed,
    generate_submission_token,
    get_draft_by_submission_token,
    list_open_drafts,
    submit_draft,
)

bp_person = Blueprint("person", __name__, url_prefix="/persons")


@bp_person.app_template_filter("b64encode")
def b64encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


# ---------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------
def normalize_phone(phone):
    if not phone:
        return ""
    p = str(phone).strip().replace(" ", "").replace("-", "").replace("/", "")
    if p.startswith("+49"):
        p = "0" + p[3:]
    if p.startswith("0049"):
        p = "0" + p[4:]
    return p


def normalize_email(email):
    return (str(email) if email else "").strip().lower()


def parse_date_flexible(value: str):
    """TT.MM.JJJJ oder YYYY-MM-DD -> date | None"""
    if not value:
        return None
    value = value.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def is_true(v) -> bool:
    return (v or "").lower() == "true"


def _normalize_iban(value: str | None) -> str:
    return Person.normalize_iban(value)


def _is_valid_iban(value: str | None) -> bool:
    iban = _normalize_iban(value)
    if not iban:
        return True
    if len(iban) < 15 or len(iban) > 34:
        return False
    if not re.fullmatch(r"[A-Z0-9]+", iban):
        return False

    rearranged = iban[4:] + iban[:4]
    digits = []
    for char in rearranged:
        if char.isdigit():
            digits.append(char)
        else:
            digits.append(str(ord(char) - 55))

    return int("".join(digits)) % 97 == 1


def _format_iban_for_display(value: str | None) -> str:
    iban = _normalize_iban(value)
    if not iban:
        return ""
    return " ".join(iban[i:i + 4] for i in range(0, len(iban), 4))


def _default_sepa_mandate_reference(person_id: int | None) -> str:
    if not person_id:
        return ""
    return f"DZ-{int(person_id):06d}"


def _ensure_sepa_mandate_reference(person: Person) -> bool:
    """Setzt eine Mandatsreferenz einmalig aus der Personen-ID, falls noch leer."""
    if not person:
        return False

    current = Person.normalize_sepa_mandate_reference(getattr(person, "sepa_mandate_reference", None))
    if current:
        if current != getattr(person, "sepa_mandate_reference", None):
            person.sepa_mandate_reference = current
            return True
        return False

    reference = _default_sepa_mandate_reference(person.id)
    if not reference:
        return False

    person.sepa_mandate_reference = reference
    return True


def _collect_and_validate(form):
    """
    Liest ALLE Felder aus dem Formular, normalisiert und validiert.
    Liefert: (data_dict, field_errors, warnings)
    field_errors ist dict[str,str]
    """
    field_errors = {}
    warnings = []

    # Pflichtfelder / Basis
    first_name = (form.get("first_name") or "").strip()
    last_name = (form.get("last_name") or "").strip()
    phone = normalize_phone((form.get("phone") or "").strip())
    email = normalize_email((form.get("email") or "").strip())

    # E-Mail-Validierung (optional erlaubt, aber wenn angegeben, dann gültig)
    if email:
        try:
            from email_validator import validate_email, EmailNotValidError
            validate_email(email, check_deliverability=True)
        except ImportError:
            field_errors["email"] = "E-Mail-Validierung fehlgeschlagen (Modul fehlt)."
        except EmailNotValidError as e:
            field_errors["email"] = "Ungültige E-Mail-Adresse: {}".format(str(e))

    # Deutliche Markierung, falls keine E-Mail vorhanden
    if not email:
        email = ""

    # zusätzliche Felder aus deinem Formular
    emergency_name = (form.get("emergency_name") or "").strip()
    emergency_relation = (form.get("emergency_relation") or "").strip()
    emergency_phone = (form.get("emergency_phone") or "").strip()
    emergency_email = (form.get("emergency_email") or "").strip()

    iban = _normalize_iban(form.get("iban"))
    bic = (form.get("bic") or "").strip()
    account_holder = (form.get("account_holder") or "").strip()
    sepa_enabled = is_true(form.get("sepa_enabled"))
    sepa_mandate_reference = Person.normalize_sepa_mandate_reference(form.get("sepa_mandate_reference"))
    sepa_mandate_date_raw = (form.get("sepa_mandate_date") or "").strip()
    sepa_mandate_date = None
    sepa_first_collection_done = is_true(form.get("sepa_first_collection_done"))

    if sepa_mandate_date_raw:
        md = parse_date_flexible(sepa_mandate_date_raw)
        if md is None:
            field_errors["sepa_mandate_date"] = "Mandatsdatum muss ein gültiges Datum sein."
        else:
            sepa_mandate_date = md

    street_and_number = (form.get("street_and_number") or "").strip()
    zip_code = (form.get("zip_code") or "").strip()
    city = (form.get("city") or "").strip()

    license_number = (form.get("license_number") or "").strip()
    insurance_provider = (form.get("insurance_provider") or "").strip()
    insurance_number = (form.get("insurance_number") or "").strip()

    comment = (form.get("comment") or "").strip()
    notes = (form.get("notes") or "").strip()

    # Flags
    is_member = is_true(form.get("is_member"))
    is_partner_verein = is_true(form.get("is_partner_verein"))
    is_tandem_guest = is_true(form.get("is_tandem_guest"))
    is_tandemmaster = is_true(form.get("is_tandemmaster"))
    is_tandem_kleinunternehmer = is_true(form.get("is_tandem_kleinunternehmer"))
    is_student = is_true(form.get("is_student"))
    is_video = is_true(form.get("is_video"))
    is_video_kleinunternehmer = is_true(form.get("is_video_kleinunternehmer"))
    is_aff_teacher = is_true(form.get("is_aff_teacher"))
    is_aff_teacher_kleinunternehmer = is_true(form.get("is_aff_teacher_kleinunternehmer"))
    is_aff_student = is_true(form.get("is_aff_student"))

    # Feld ist nur fuer Tandemmaster fachlich relevant.
    if not is_tandemmaster:
        is_tandem_kleinunternehmer = False

    # Feld ist nur fuer Video fachlich relevant.
    if not is_video:
        is_video_kleinunternehmer = False

    # Feld ist nur fuer AFF-Lehrer fachlich relevant.
    if not is_aff_teacher:
        is_aff_teacher_kleinunternehmer = False

    # ---- Validierung (wie bisher, nicht strenger) ----
    if not first_name:
        field_errors["first_name"] = "Vorname darf nicht leer sein."
    if not last_name:
        field_errors["last_name"] = "Nachname darf nicht leer sein."
    if is_tandem_guest:
        if not phone:
            warnings.append("Tandemgast: Telefonnummer fehlt (wichtig, aber Speichern ist erlaubt).")
        elif len(phone) < 5:
            warnings.append("Tandemgast: Telefonnummer wirkt unvollständig (wichtig, aber Speichern ist erlaubt).")
    else:
        if len(phone) < 5:
            field_errors["phone"] = "Telefonnummer ist ungültig."

    # Gewicht
    weight_raw = (form.get("weight_kg") or "").strip()
    weight_kg = None
    if not weight_raw:
        field_errors["weight_kg"] = "Gewicht ist ein Pflichtfeld."
    elif not weight_raw.isdigit():
        field_errors["weight_kg"] = "Gewicht muss eine ganze Zahl sein."
    else:
        weight_kg = int(weight_raw)

    # Größe optional
    height_raw = (form.get("height_cm") or "").strip()
    height_cm = None
    if height_raw:
        if not height_raw.isdigit():
            field_errors["height_cm"] = "Größe muss eine ganze Zahl sein."
        else:
            height_cm = int(height_raw)

    # Geburtstag optional (HTML date liefert YYYY-MM-DD)
    birthdate_raw = (form.get("birthdate") or "").strip()
    birthdate = None
    if birthdate_raw:
        bd = parse_date_flexible(birthdate_raw)
        if bd is None:
            field_errors["birthdate"] = "Geburtstag muss ein gültiges Datum sein."
        else:
            birthdate = bd

    # Exklusivitätsregel:
    # Partner-Verein darf weder Vereinsmitglied noch (Tandem-)Gast sein.
    if is_partner_verein and is_member:
        field_errors["is_partner_verein"] = "Partner-Verein kann nicht gleichzeitig Vereinsmitglied sein."
        field_errors["is_member"] = "Vereinsmitglied kann nicht gleichzeitig Partner-Verein sein."
    if is_partner_verein and is_tandem_guest:
        field_errors["is_partner_verein"] = "Partner-Verein kann nicht gleichzeitig Tandemgast sein."
        field_errors["is_tandem_guest"] = "Tandemgast kann nicht gleichzeitig Partner-Verein sein."

    if sepa_enabled and is_tandem_guest:
        sepa_enabled = False
        sepa_first_collection_done = False
        warnings.append("SEPA-Lastschrift wurde für Tandemgast/Mitflieger deaktiviert.")

    if iban and not _is_valid_iban(iban):
        field_errors["iban"] = "Die eingegebene IBAN ist ungültig."

    if sepa_enabled:
        if not iban:
            field_errors["iban"] = "IBAN ist Pflicht, wenn SEPA-Lastschrift aktiviert ist."
        if not account_holder:
            field_errors["account_holder"] = "Kontoinhaber ist Pflicht, wenn SEPA-Lastschrift aktiviert ist."
        if not sepa_mandate_date:
            field_errors["sepa_mandate_date"] = "Mandatsdatum ist Pflicht, wenn SEPA-Lastschrift aktiviert ist."
    else:
        sepa_first_collection_done = False

    # Lehrer
    is_teacher = is_true(form.get("is_teacher"))
    teacher_license_expires_raw = (form.get("teacher_license_expires") or "").strip()
    teacher_license_expires = None
    if is_teacher:
        if not teacher_license_expires_raw:
            field_errors["teacher_license_expires"] = "Ablaufdatum der Lehrerlizenz ist Pflicht, wenn Lehrer = Ja."
        else:
            tl = parse_date_flexible(teacher_license_expires_raw)
            if tl is None:
                field_errors["teacher_license_expires"] = "Ablaufdatum Lehrerlizenz muss ein gültiges Datum sein."
            else:
                teacher_license_expires = tl

    # Enthaftung
    liability_waiver_given = is_true(form.get("liability_waiver_given"))
    liability_waiver_date_raw = (form.get("liability_waiver_date") or "").strip()
    liability_waiver_date = None
    if liability_waiver_given:
        if liability_waiver_date_raw:
            lw = parse_date_flexible(liability_waiver_date_raw)
            liability_waiver_date = lw if lw else date.today()
        else:
            liability_waiver_date = date.today()

    # Zusätzliche Hinweise für Tandemgast: wichtige, aber nicht blockierende Felder
    if is_tandem_guest:
        if not email:
            warnings.append("Tandemgast: E-Mail fehlt (wichtig, aber Speichern ist erlaubt).")

        if not any([street_and_number, zip_code, city]):
            warnings.append("Tandemgast: Adresse fehlt (wichtig, aber Speichern ist erlaubt).")
        elif not all([street_and_number, zip_code, city]):
            warnings.append("Tandemgast: Adresse ist unvollständig (wichtig, aber Speichern ist erlaubt).")

        if not any([emergency_name, emergency_relation, emergency_phone, emergency_email]):
            warnings.append("Tandemgast: Notfallkontakt fehlt (wichtig, aber Speichern ist erlaubt).")
        elif not emergency_name or not emergency_phone:
            warnings.append("Tandemgast: Notfallkontakt ist unvollständig (Name/Telefon wichtig, aber Speichern ist erlaubt).")

    data = dict(
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        email=email,
        emergency_name=emergency_name,
        emergency_relation=emergency_relation,
        emergency_phone=emergency_phone,
        emergency_email=emergency_email,
        iban=iban,
        bic=bic,
        account_holder=account_holder,
        sepa_enabled=sepa_enabled,
        sepa_mandate_reference=sepa_mandate_reference,
        sepa_mandate_date=sepa_mandate_date,
        sepa_first_collection_done=sepa_first_collection_done,
        street_and_number=street_and_number,
        zip_code=zip_code,
        city=city,
        license_number=license_number,
        insurance_provider=insurance_provider,
        insurance_number=insurance_number,
        comment=comment,
        notes=notes,
        weight_kg=weight_kg,
        height_cm=height_cm,
        birthdate=birthdate,
        is_member=is_member,
        is_partner_verein=is_partner_verein,
        is_tandem_guest=is_tandem_guest,
        is_tandemmaster=is_tandemmaster,
        is_tandem_kleinunternehmer=is_tandem_kleinunternehmer,
        is_student=is_student,
        is_video=is_video,
        is_video_kleinunternehmer=is_video_kleinunternehmer,
        is_aff_teacher=is_aff_teacher,
        is_aff_teacher_kleinunternehmer=is_aff_teacher_kleinunternehmer,
        is_aff_student=is_aff_student,
        is_teacher=is_teacher,
        teacher_license_expires=teacher_license_expires,
        liability_waiver_date=liability_waiver_date,
    )

    return data, field_errors, warnings


# ---------------------------------------------------------
# Personenliste
# Standard: aktive Personen, Archiv über filter=archived
# ---------------------------------------------------------
@bp_person.route("/")
def list_persons():
    search = request.args.get("search", "").strip()
    # Neue Logik: filters=value1,value2,value3
    filters_str = request.args.get("filters", "").strip()
    filters_list = [f.strip() for f in filters_str.split(",") if f.strip()] if filters_str else []
    
    sort = request.args.get("sort", "last_name")
    direction = request.args.get("direction", "asc")

    # Standard: aktive; Archiv: nur archivierte
    if "archived" in filters_list:
        query = Person.query.filter(Person.deleted_at.isnot(None))
    else:
        query = Person.query.filter(Person.deleted_at.is_(None))

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
        if search.lower() == "lehrer":
            query = query.filter(Person.is_teacher.is_(True))
        if search.lower() == "gast":
            query = query.filter(
                Person.is_member.is_(False),
                Person.is_tandem_guest.is_(False),
                Person.is_partner_verein.is_(False),
            )

    # Multiple Filter mit AND kombinieren
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
            query = query.filter(
                or_(
                    Person.liability_waiver_date.is_(None),
                    Person.liability_waiver_date < date(date.today().year, 1, 1),
                )
            )
        elif f == "weight_bad":
            # schneller als Python-Loop: SQL
            query = query.filter(
                or_(
                    and_(Person.is_tandem_guest.is_(True),
                         or_(Person.weight_kg < 40, Person.weight_kg > 90)),
                    and_(Person.is_tandem_guest.is_(False),
                         or_(Person.weight_kg < 50, Person.weight_kg > 100)),
                )
            )

    valid_sort_fields = {
        "last_name": Person.last_name,
        "first_name": Person.first_name,
        "is_member": Person.is_member,
        "is_partner_verein": Person.is_partner_verein,
        "is_tandem_guest": Person.is_tandem_guest,
        "teacher": Person.is_teacher,
        "guest": case(
            (
                and_(
                    Person.is_member.is_(False),
                    Person.is_tandem_guest.is_(False),
                    Person.is_partner_verein.is_(False),
                ),
                1,
            ),
            else_=0,
        ),
        "weight_kg": Person.weight_kg,
        "liability_waiver_date": Person.liability_waiver_date,
        "liability_waiver_valid": Person.liability_waiver_date,  # Template-Link
        "teacher_license_expires": Person.teacher_license_expires,
    }

    primary = valid_sort_fields.get(sort, Person.last_name)
    if direction == "desc":
        primary = primary.desc()

    persons = query.order_by(primary, Person.last_name.asc(), Person.first_name.asc()).all()
    mobile_draft_count = MobilePersonIntakeDraft.query.filter_by(
        status=MOBILE_PERSON_INTAKE_STATUS_SUBMITTED
    ).count()

    return render_template(
        "person/list.html",
        persons=persons,
        search=search,
        filters_str=filters_str,
        filters_list=filters_list,
        sort=sort,
        direction=direction,
        mobile_draft_count=mobile_draft_count,
    )


@bp_person.route("/mobile-drafts")
def mobile_drafts():
    return render_template(
        "person/mobile_drafts.html",
        drafts=list_open_drafts(),
    )


@bp_person.route("/mobile-drafts/count")
def mobile_draft_count():
    count = MobilePersonIntakeDraft.query.filter_by(
        status=MOBILE_PERSON_INTAKE_STATUS_SUBMITTED
    ).count()
    return jsonify({"count": count})


@bp_person.route("/mobile-intake", methods=["GET", "POST"])
def mobile_intake_new():
    if request.method == "GET":
        return render_template("person/mobile_intake_new.html")

    mode = (request.form.get("mode") or "").strip()
    if mode not in {"tandem_guest", "jumper"}:
        flash("Bitte wählen Sie Tandemgast oder Springer aus.", "danger")
        return render_template("person/mobile_intake_new.html"), 400

    token, token_hash = generate_submission_token()
    draft = create_draft(
        mode=mode,
        submission_token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(minutes=60),
    )
    qr_available, mobile_url = build_local_qr_url(
        f"persons/mobile-intake/{token}"
    )
    if not qr_available:
        flash("Keine lokale Netzwerkadresse für den QR-Code verfügbar.", "danger")
        return redirect(url_for("person.mobile_drafts"))

    return render_template(
        "person/mobile_intake_qr.html",
        draft=draft,
        mobile_url=mobile_url,
        qr_image=generate_qr_png_buffer(mobile_url, size=320).getvalue(),
    )


def _mobile_intake_values(form, mode: str) -> tuple[dict, dict]:
    values = {
        "first_name": (form.get("first_name") or "").strip(),
        "last_name": (form.get("last_name") or "").strip(),
        "phone": normalize_phone(form.get("phone")),
        "email": normalize_email(form.get("email")),
        "street_and_number": (form.get("street_and_number") or "").strip(),
        "zip_code": (form.get("zip_code") or "").strip(),
        "city": (form.get("city") or "").strip(),
        "emergency_name": (form.get("emergency_name") or "").strip(),
        "emergency_relation": (form.get("emergency_relation") or "").strip(),
        "emergency_phone": normalize_phone(form.get("emergency_phone")),
    }
    errors = {}
    for field_name, label in (("first_name", "Vorname"), ("last_name", "Nachname")):
        if not values[field_name]:
            errors[field_name] = f"{label} ist erforderlich."
    if len(values["phone"]) < 5:
        errors["phone"] = "Bitte geben Sie eine gültige Telefonnummer ein."

    for field_name, label, minimum, maximum in (
        ("weight_kg", "Gewicht", 20, 200),
        ("height_cm", "Größe", 140, 220),
    ):
        raw_value = (form.get(field_name) or "").strip()
        if not raw_value:
            values[field_name] = None
            if field_name == "weight_kg":
                errors[field_name] = "Gewicht ist erforderlich."
        elif not raw_value.isdigit() or not minimum <= int(raw_value) <= maximum:
            errors[field_name] = f"{label} muss zwischen {minimum} und {maximum} liegen."
        else:
            values[field_name] = int(raw_value)

    for field_name in ("birthdate", "license_valid_until"):
        raw_value = (form.get(field_name) or "").strip()
        values[field_name] = None
        if raw_value:
            parsed_value = parse_date_flexible(raw_value)
            if parsed_value is None:
                errors[field_name] = "Bitte geben Sie ein gültiges Datum ein."
            else:
                values[field_name] = parsed_value

    if values["email"] and "@" not in values["email"]:
        errors["email"] = "Bitte geben Sie eine gültige E-Mail-Adresse ein."

    if mode == MOBILE_PERSON_INTAKE_MODE_JUMPER:
        values.update(
            {
                "license_number": (form.get("license_number") or "").strip(),
                "insurance_provider": (form.get("insurance_provider") or "").strip(),
                "insurance_number": (form.get("insurance_number") or "").strip(),
                "is_member": is_true(form.get("is_member")),
                "is_partner_verein": is_true(form.get("is_partner_verein")),
            }
        )
    return values, errors


@bp_person.route("/mobile-intake/<token>", methods=["GET", "POST"])
def mobile_intake_form(token):
    draft = get_draft_by_submission_token(token)
    if draft is None:
        return render_template("person/mobile_intake_unavailable.html"), 404
    if expire_draft_if_needed(draft):
        return render_template("person/mobile_intake_unavailable.html", expired=True), 410
    if draft.status != MOBILE_PERSON_INTAKE_STATUS_OPEN:
        return render_template("person/mobile_intake_unavailable.html"), 410

    if request.method == "POST":
        values, field_errors = _mobile_intake_values(request.form, draft.mode)
        if field_errors:
            return render_template(
                "person/mobile_intake_form.html",
                draft=draft,
                field_errors=field_errors,
                form_data=request.form,
            ), 400
        try:
            submit_draft(
                draft,
                values=values,
                idempotency_key_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
            )
        except ValueError:
            return render_template("person/mobile_intake_unavailable.html", expired=True), 410
        return render_template("person/mobile_intake_success.html")

    return render_template(
        "person/mobile_intake_form.html",
        draft=draft,
        field_errors={},
        form_data=None,
    )


# ---------------------------------------------------------
# CRUD – Neue Person anlegen
# ---------------------------------------------------------
def _mobile_draft_form_data(draft: MobilePersonIntakeDraft) -> dict:
    def date_value(value):
        return value.strftime("%Y-%m-%d") if value else ""

    return {
        "mobile_draft_id": str(draft.id),
        "first_name": draft.first_name or "",
        "last_name": draft.last_name or "",
        "phone": draft.phone or "",
        "email": draft.email or "",
        "weight_kg": str(draft.weight_kg) if draft.weight_kg is not None else "",
        "height_cm": str(draft.height_cm) if draft.height_cm is not None else "",
        "birthdate": date_value(draft.birthdate),
        "street_and_number": draft.street_and_number or "",
        "zip_code": draft.zip_code or "",
        "city": draft.city or "",
        "emergency_name": draft.emergency_name or "",
        "emergency_relation": draft.emergency_relation or "",
        "emergency_phone": draft.emergency_phone or "",
        "license_number": draft.license_number or "",
        "insurance_provider": draft.insurance_provider or "",
        "insurance_number": draft.insurance_number or "",
        "is_member": "true" if draft.is_member else "false",
        "is_partner_verein": "true" if draft.is_partner_verein else "false",
        "is_tandem_guest": "true" if draft.mode == "tandem_guest" else "false",
    }


def _submitted_mobile_draft(draft_id: str | None) -> MobilePersonIntakeDraft | None:
    try:
        draft_id_int = int(draft_id or "")
    except (TypeError, ValueError):
        return None
    draft = db.session.get(MobilePersonIntakeDraft, draft_id_int)
    if draft and draft.status == MOBILE_PERSON_INTAKE_STATUS_SUBMITTED:
        return draft
    return None


@bp_person.route("/new", methods=["GET", "POST"])
def new_person():
    if request.method == "POST":
        mobile_draft = _submitted_mobile_draft(request.form.get("mobile_draft_id"))
        if request.form.get("mobile_draft_id") and mobile_draft is None:
            flash("Dieser mobile Entwurf kann nicht mehr übernommen werden.", "warning")
            return redirect(url_for("person.mobile_drafts"))

        data, field_errors, warnings = _collect_and_validate(request.form)

        if field_errors:
            person = Person(**data)
            return render_template(
                "person/form.html",
                person=person,
                field_errors=field_errors,
                form_data=request.form,
                format_iban_for_display=_format_iban_for_display,
            )

        p = Person(**data)
        try:
            db.session.add(p)
            db.session.flush()
            _ensure_sepa_mandate_reference(p)
            if mobile_draft is not None:
                accept_draft(
                    mobile_draft,
                    reviewed_by="Manifest-Benutzer",
                    person_id=p.id,
                    commit=False,
                )
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Person konnte nicht angelegt werden.", "danger")
            return render_template(
                "person/form.html",
                person=Person(**data),
                field_errors={},
                form_data=request.form,
                format_iban_for_display=_format_iban_for_display,
            ), 500
        for warning in warnings:
            flash(warning, "warning")
        flash("Person erfolgreich angelegt.", "success")
        return redirect(url_for("person.list_persons"))

    mobile_draft = _submitted_mobile_draft(request.args.get("mobile_draft_id"))
    if request.args.get("mobile_draft_id") and mobile_draft is None:
        flash("Dieser mobile Entwurf kann nicht mehr übernommen werden.", "warning")
        return redirect(url_for("person.mobile_drafts"))

    return render_template(
        "person/form.html",
        person=None,
        field_errors={},
        form_data=_mobile_draft_form_data(mobile_draft) if mobile_draft else None,
        format_iban_for_display=_format_iban_for_display,
    )


# ---------------------------------------------------------
# CRUD – Person anzeigen
# ---------------------------------------------------------
@bp_person.route("/detail/<int:id>")
def detail(id):
    person = Person.query.get_or_404(id)
    return render_template("person/detail.html", person=person)


# ---------------------------------------------------------
# CRUD – Person bearbeiten
# ---------------------------------------------------------
@bp_person.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_person(id):
    person = Person.query.get_or_404(id)

    if request.method == "GET" and _ensure_sepa_mandate_reference(person):
        db.session.commit()

    if request.method == "POST":
        data, field_errors, warnings = _collect_and_validate(request.form)

        if field_errors:
            return render_template(
                "person/form.html",
                person=person,
                field_errors=field_errors,
                form_data=request.form,
                format_iban_for_display=_format_iban_for_display,
            )

        previous_name = person.current_name
        for k, v in data.items():
            setattr(person, k, v)
        _ensure_sepa_mandate_reference(person)
        person.remember_original_name(previous_name)

        # Newsletter-Status nur bei expliziter manueller Aktion aendern.
        newsletter_action = (request.form.get("newsletter_opt_out_action") or "").strip()
        if newsletter_action == "set_opt_out":
            person.newsletter_opt_out = True
        elif newsletter_action == "clear_opt_out":
            person.newsletter_opt_out = False
            person.newsletter_unsubscribe_token = None

        db.session.commit()
        for warning in warnings:
            flash(warning, "warning")
        flash("Person erfolgreich aktualisiert.", "success")
        return redirect(url_for("person.list_persons"))

    return render_template(
        "person/form.html",
        person=person,
        field_errors={},
        form_data=None,
        format_iban_for_display=_format_iban_for_display,
    )


# ---------------------------------------------------------
# Newsletter-Abmeldung zurücksetzen (Admin/DB-Admin)
# ---------------------------------------------------------
@bp_person.route("/reset_newsletter_optout/<int:id>", methods=["POST"])
def reset_newsletter_optout(id):
    from flask import session as fsession
    if not (fsession.get("is_admin") or fsession.get("is_db_admin")):
        flash("Zugriff verweigert.", "danger")
        return redirect(url_for("person.detail", id=id))
    person = Person.query.get_or_404(id)
    person.newsletter_opt_out = False
    person.newsletter_unsubscribe_token = None
    db.session.commit()
    flash(f"{person.full_name}: Newsletter-Abmeldung zurückgesetzt.", "success")
    return redirect(url_for("person.detail", id=id))


# ---------------------------------------------------------
# SOFTDELETE – Person ins Archiv verschieben
# (explizite Route, für UI-Buttons)
# ---------------------------------------------------------
@bp_person.route("/archive/<int:id>", methods=["POST"])
def archive_person(id):
    person = Person.query.get_or_404(id)

    if person.is_archived:
        flash("Person ist bereits archiviert.", "info")
        return redirect(url_for("person.list_persons"))

    try:
        person.archive(reason="archived_via_ui")
        db.session.commit()
        flash("Person ins Archiv verschoben.", "success")
    except Exception:
        db.session.rollback()
        flash("Archivierung fehlgeschlagen. Bitte erneut versuchen.", "danger")

    return redirect(url_for("person.list_persons"))


# ---------------------------------------------------------
# Restore aus dem Archiv
# ---------------------------------------------------------
@bp_person.route("/restore/<int:id>", methods=["POST"])
def restore_person(id):
    person = Person.query.get_or_404(id)

    if person.is_active:
        flash("Person ist bereits aktiv.", "info")
        return redirect(url_for("person.list_persons"))

    try:
        person.restore()
        db.session.commit()
        flash("Person wiederhergestellt.", "success")
    except Exception:
        db.session.rollback()
        flash("Wiederherstellung fehlgeschlagen.", "danger")

    return redirect(url_for("person.list_persons", filter="archived"))


# ---------------------------------------------------------
# HARDDELETE – Nur für Admins und nur ohne Loads/Rechnungen
# ---------------------------------------------------------
@bp_person.route("/hard_delete/<int:id>", methods=["POST"])
@admin_required
def hard_delete_person(id):
    person = Person.query.get_or_404(id)

    if not person.can_hard_delete():
        flash("Endgültiges Löschen nicht möglich: Es existieren Sprünge oder Rechnungen.", "danger")
        return redirect(url_for("person.detail", id=person.id))

    try:
        db.session.delete(person)
        db.session.commit()
        flash("Person endgültig gelöscht (keine Loads/Rechnungen vorhanden).", "success")
    except Exception:
        db.session.rollback()
        flash("Endgültiges Löschen fehlgeschlagen. Bitte erneut versuchen.", "danger")

    return redirect(url_for("person.list_persons"))


# ---------------------------------------------------------
# ALT: /delete – abwärtskompatibel, jetzt nur noch Softdelete
# ---------------------------------------------------------
@bp_person.route("/delete/<int:id>", methods=["POST"])
def delete_person(id):
    """
    Alte Route: wird aus Kompatibilitätsgründen beibehalten,
    führt aber nur noch eine Archivierung durch.
    """
    person = Person.query.get_or_404(id)

    try:
        person.archive(reason="archived_via_legacy_delete")
        db.session.commit()
        flash("Person ins Archiv verschoben.", "success")
    except Exception:
        db.session.rollback()
        flash("Aktion fehlgeschlagen. Bitte erneut versuchen.", "danger")

    return redirect(url_for("person.list_persons"))


# ---------------------------------------------------------
# Template-Helfer: is_admin() in Templates verfügbar machen
# ---------------------------------------------------------
@bp_person.app_context_processor
def inject_is_admin():
    """
    Stellt is_admin() in allen Templates dieses Blueprints zur Verfügung.
    Nutzung in Jinja: {% if is_admin() %}...{% endif %}
    """
    return {"is_admin": is_admin}


@bp_person.route("/<int:id>/waiver.pdf")
def waiver_pdf(id):
    person = Person.query.get_or_404(id)
    billing_config = BillingConfig.query.first()

    # Robust gegen Alt-/Importfälle: bool, "ja", "true", "1", "yes" gelten als Tandemgast.
    raw_tandem = getattr(person, "is_tandem_guest", False)
    if isinstance(raw_tandem, str):
        is_tandem_guest = raw_tandem.strip().lower() in {"ja", "true", "1", "yes"}
    else:
        is_tandem_guest = bool(raw_tandem)

    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
    logo_data_uri = None
    if billing_config and getattr(billing_config, "logo_filename", None):
        logo_path = os.path.join(static_dir, "img", billing_config.logo_filename)
        logo_data_uri = _image_to_data_uri(logo_path)

    waiver_text = ""
    if billing_config:
        waiver_text = (
            billing_config.waiver_text_tandem if is_tandem_guest else billing_config.waiver_text_skydiver
        ) or ""

    place = ""
    if billing_config:
        place = (getattr(billing_config, "city", "") or "").strip()

    waiver_date_label = person.liability_waiver_date.strftime("%d.%m.%Y") if person.liability_waiver_date else ""

    html = render_template(
        "person/waiver_pdf.html",
        person=person,
        billing_config=billing_config,
        logo_data_uri=logo_data_uri,
        is_tandem_guest=is_tandem_guest,
        waiver_text=waiver_text,
        waiver_place=place,
        waiver_date_label=waiver_date_label,
    )

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    from weasyprint import HTML

    pdf_bytes = HTML(string=html, base_url=base_dir).write_pdf(
        presentational_hints=True,
        optimize_size=("fonts", "images"),
    )

    filename = f"Enthaftung_{person.id}_{(person.last_name or '').strip()}_{(person.first_name or '').strip()}.pdf"
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        download_name=filename,
        as_attachment=False,
    )
