"""
Blueprint: E-Mail / Newsletter-Versand
URL-Prefix: /email

Zugriff: nur is_admin oder is_db_admin
"""
from __future__ import annotations

import html
import json
import os
import uuid
from datetime import datetime

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app import db, now_local
from app.models.email_config import EmailConfig
from app.models.email_send_log import EmailSendLog
from app.models.person import Person
from app.services.mailer_service import MailerService

bp = Blueprint("email_nl", __name__, url_prefix="/email")


DEFAULT_MAIL_BODY_TEMPLATE = (
    "Liebe/r {first_name}, {last_name},\n\n"
    "viele Grüße aus Dessau"
)


# ------------------------------------------------------------------
# Berechtigungsprüfung (Admin oder DB-Admin)
# ------------------------------------------------------------------
def _require_admin():
    """Gibt Redirect zurück, falls kein Admin-Zugang besteht."""
    if session.get("is_admin") or session.get("is_db_admin"):
        return None
    flash("Zugriff verweigert. Nur für Admins und DB-Admins.", "danger")
    return redirect(url_for("pwa.home"))


def _is_dev_mode() -> bool:
    from flask import current_app

    env_name = str(current_app.config.get("MANIFEST_ENV", "development")).strip().lower()
    return env_name != "production"


def _get_or_create_cfg() -> EmailConfig:
    cfg = EmailConfig.query.first()
    if cfg is None:
        cfg = EmailConfig()
        db.session.add(cfg)
        db.session.flush()
    return cfg


# ------------------------------------------------------------------
# Hilfsfunktion: Personen nach Filter-Keys laden
# ------------------------------------------------------------------
def _persons_for_filter(filter_key: str):
    from sqlalchemy import or_, and_
    from datetime import date

    q = Person.query.filter(Person.deleted_at.is_(None))

    if filter_key == "members":
        return q.filter(Person.is_member.is_(True)).all()
    if filter_key == "partner":
        return q.filter(Person.is_partner_verein.is_(True)).all()
    if filter_key == "tandem":
        return q.filter(Person.is_tandem_guest.is_(True)).all()
    if filter_key == "student":
        return q.filter(Person.is_student.is_(True)).all()
    if filter_key == "aff_student":
        return q.filter(Person.is_aff_student.is_(True)).all()
    if filter_key == "tandemmaster":
        return q.filter(Person.is_tandemmaster.is_(True)).all()
    if filter_key == "teacher":
        return q.filter(Person.is_teacher.is_(True)).all()
    if filter_key == "aff_teacher":
        return q.filter(Person.is_aff_teacher.is_(True)).all()
    if filter_key == "guest":
        return q.filter(
            Person.is_member.is_(False),
            Person.is_tandem_guest.is_(False),
            Person.is_partner_verein.is_(False),
        ).all()
    if filter_key == "liability_ok":
        return q.filter(Person.liability_waiver_date.isnot(None)).all()
    if filter_key == "liability_bad":
        return q.filter(
            or_(
                Person.liability_waiver_date.is_(None),
                Person.liability_waiver_date < date(date.today().year, 1, 1),
            )
        ).all()
    if filter_key == "weight_bad":
        from sqlalchemy import or_, and_
        return q.filter(
            or_(
                and_(Person.is_tandem_guest.is_(True),
                     or_(Person.weight_kg < 40, Person.weight_kg > 90)),
                and_(Person.is_tandem_guest.is_(False),
                     or_(Person.weight_kg < 50, Person.weight_kg > 100)),
            )
        ).all()
    if filter_key == "newsletter":
        return q.filter(
            or_(
                Person.newsletter_opt_out.is_(None),
                Person.newsletter_opt_out.is_(False),
            )
        ).filter(Person.email.isnot(None)).filter(Person.email != "").all()
    if filter_key == "archived":
        return Person.query.filter(Person.deleted_at.isnot(None)).all()
    # "all" oder unbekannt: alle aktiven
    return q.all()


# ------------------------------------------------------------------
# GET /email/config   – Konfiguration anzeigen
# POST /email/config  – Konfiguration speichern (Blöcke A, C, E, F)
# ------------------------------------------------------------------
@bp.route("/config", methods=["GET", "POST"])
def config_edit():
    deny = _require_admin()
    if deny:
        return deny

    cfg = _get_or_create_cfg()
    config_mail_body_template = (cfg.mail_body_template or "").strip() or DEFAULT_MAIL_BODY_TEMPLATE

    smtp_test_to_email = ""

    if request.method == "POST":
        form = request.form

        # Block A: Sprungplatzbetreiber
        cfg.company_name = form.get("company_name") or None
        cfg.logo_filename = (form.get("logo_filename") or "").strip() or None
        cfg.street = form.get("street") or None
        cfg.zip_code = (form.get("zip_code") or "").strip() or None
        cfg.city = (form.get("city") or "").strip() or None

        # Block C: Online-Präsenz
        cfg.website = (form.get("website") or "").strip() or None
        cfg.email = (form.get("email") or "").strip() or None
        cfg.tax_number = (form.get("tax_number") or "").strip() or None
        cfg.instagram_url = (form.get("instagram_url") or "").strip() or None
        cfg.facebook_url = (form.get("facebook_url") or "").strip() or None

        # Block D: Standard-E-Mail-Vorlage
        cfg.mail_sender_address = (form.get("mail_sender_address") or "").strip() or None
        cfg.mail_sender_name = (form.get("mail_sender_name") or "").strip() or None
        cfg.mail_subject_template = (form.get("mail_subject_template") or "").strip() or None
        cfg.mail_body_template = form.get("mail_body_template") or None

        # Block E: SMTP
        cfg.smtp_server = (form.get("smtp_server") or "").strip() or None
        cfg.smtp_fallback_host = (form.get("smtp_fallback_host") or "").strip() or None
        raw_port = (form.get("smtp_port") or "").strip()
        cfg.smtp_port = int(raw_port) if raw_port.isdigit() else None
        cfg.smtp_username = (form.get("smtp_username") or "").strip() or None
        smtp_pwd = form.get("smtp_password")
        if smtp_pwd:
            cfg.smtp_password = smtp_pwd
        cfg.smtp_use_tls = bool(form.get("smtp_use_tls"))
        cfg.smtp_use_ssl = bool(form.get("smtp_use_ssl"))

        # Block F: QR-Codes
        cfg.qr_instagram_filename = (form.get("qr_instagram_filename") or "").strip() or None
        cfg.qr_facebook_filename = (form.get("qr_facebook_filename") or "").strip() or None
        cfg.qr_website_filename = (form.get("qr_website_filename") or "").strip() or None

        db.session.commit()
        flash("E-Mail-Konfiguration gespeichert.", "success")
        return redirect(url_for("email_nl.config_edit"))

    return render_template(
        "email_newsletter/config_edit.html",
        cfg=cfg,
        config_mail_body_template=config_mail_body_template,
        smtp_test_to_email=smtp_test_to_email,
    )


# ------------------------------------------------------------------
# POST /email/config/test_email  – Test-Mail mit aktuellen Formularwerten
# ------------------------------------------------------------------
@bp.route("/config/test_email", methods=["POST"])
def config_test_email():
    deny = _require_admin()
    if deny:
        return deny

    form = request.form
    test_to = (form.get("smtp_test_to_email") or "").strip()
    if not test_to:
        flash("Bitte Test-Empfänger-Adresse eingeben.", "warning")
        return redirect(url_for("email_nl.config_edit"))

    # Temporäres cfg-Objekt aus Formularwerten (nicht gespeichert!)
    class _TmpCfg:
        pass

    tmp = _TmpCfg()
    tmp.smtp_server = (form.get("smtp_server") or "").strip()
    tmp.smtp_fallback_host = (form.get("smtp_fallback_host") or "").strip() or None
    raw_port = (form.get("smtp_port") or "").strip()
    tmp.smtp_port = int(raw_port) if raw_port.isdigit() else 587
    tmp.smtp_username = (form.get("smtp_username") or "").strip() or None
    tmp.smtp_password = form.get("smtp_password") or None
    # Falls kein PW im Formular, aus DB laden
    if not tmp.smtp_password:
        cfg_db = EmailConfig.query.first()
        if cfg_db:
            tmp.smtp_password = cfg_db.smtp_password
    tmp.smtp_use_tls = bool(form.get("smtp_use_tls"))
    tmp.smtp_use_ssl = bool(form.get("smtp_use_ssl"))
    tmp.company_name = (form.get("company_name") or "").strip() or None
    tmp.street = (form.get("street") or "").strip() or None
    tmp.zip_code = (form.get("zip_code") or "").strip() or None
    tmp.city = (form.get("city") or "").strip() or None
    tmp.website = (form.get("website") or "").strip() or None
    tmp.email = (form.get("email") or "").strip() or None
    tmp.tax_number = (form.get("tax_number") or "").strip() or None
    tmp.logo_filename = (form.get("logo_filename") or "").strip() or None

    sender = (form.get("mail_sender_address") or "").strip()
    if not sender:
        flash("Absender-Adresse fehlt – Testmail kann nicht gesendet werden.", "warning")
        return redirect(url_for("email_nl.config_edit"))

    try:
        result = MailerService.send_custom_email(
            to_email=test_to,
            subject="Manifest E-Mail – Testmail",
            body=(
                "Dies ist eine Testmail vom Manifest-Fallschirm-System.\n\n"
                "Wenn Sie diese E-Mail erhalten, funktioniert der E-Mail-Versand korrekt."
            ),
            cfg=tmp,
            sender_address=sender,
        )
        msg_id = result.get("message_id") or ""
        flash(
            f"Testmail erfolgreich an {test_to} gesendet."
            + (f" | Message-ID: {msg_id}" if msg_id else ""),
            "success",
        )
    except Exception as exc:
        flash(f"Testmail fehlgeschlagen: {exc}", "danger")

    return redirect(url_for("email_nl.config_edit"))


# ------------------------------------------------------------------
# GET  /email/send  – Compose-Seite (Empfänger + Inhalt)
# POST /email/send  – E-Mail / Newsletter versenden
# ------------------------------------------------------------------
@bp.route("/send", methods=["GET", "POST"])
def send():
    deny = _require_admin()
    if deny:
        return deny

    cfg = _get_or_create_cfg()

    # Alle aktiven Personen für Empfänger-Auswahl
    all_persons = (
        Person.query
        .filter(Person.deleted_at.is_(None))
        .order_by(Person.last_name.asc(), Person.first_name.asc())
        .all()
    )

    if request.method == "GET":
        # Gruppen-Vorauswahl aus Query-Parameter
        group_filter = request.args.get("group", "")
        preselected_ids: set[int] = set()
        if group_filter:
            preselected_ids = {p.id for p in _persons_for_filter(group_filter)}

        compose_body = (cfg.mail_body_template or "").strip() or DEFAULT_MAIL_BODY_TEMPLATE

        return render_template(
            "email_newsletter/send.html",
            cfg=cfg,
            compose_body=compose_body,
            all_persons=all_persons,
            preselected_ids=preselected_ids,
            group_filter=group_filter,
        )

    # ---------- POST: Versand ----------
    form = request.form
    files = request.files

    mail_type = form.get("mail_type", "email")
    if mail_type not in {"email", "newsletter"}:
        mail_type = "email"

    subject = (form.get("subject") or "").strip()
    body = (form.get("body") or "").strip()
    inline_images_intro = (form.get("inline_images_intro") or "").strip()
    free_emails_raw = form.get("free_emails", "")
    override_newsletter = bool(form.get("override_newsletter_optout"))

    if not subject:
        flash("Betreff darf nicht leer sein.", "warning")
        return redirect(url_for("email_nl.send"))
    if not body:
        flash("E-Mail-Text darf nicht leer sein.", "warning")
        return redirect(url_for("email_nl.send"))

    # Empfänger aus Person-Checkboxen
    selected_person_ids = [
        int(v) for v in form.getlist("person_ids") if v.isdigit()
    ]
    selected_persons = Person.query.filter(Person.id.in_(selected_person_ids)).all()

    # Newsletter-Opt-out filtern
    recipient_persons = []
    skipped_optout = 0
    for p in selected_persons:
        if (
            mail_type == "newsletter"
            and getattr(p, "newsletter_opt_out", False)
            and not override_newsletter
        ):
            skipped_optout += 1
            continue
        if not p.email:
            continue
        recipient_persons.append(p)

    # Freie E-Mail-Adressen
    free_emails = []
    for line in free_emails_raw.replace(",", "\n").splitlines():
        addr = line.strip()
        if addr and "@" in addr:
            free_emails.append(addr)

    if not recipient_persons and not free_emails:
        flash(
            "Keine Empfänger ausgewählt (oder alle Newsletter-Abmeldungen gefiltert).",
            "warning",
        )
        return redirect(url_for("email_nl.send"))

    # Datei-Anhänge einlesen
    attachments: list[tuple[str, bytes]] = []
    for file_obj in files.getlist("attachments"):
        if file_obj and file_obj.filename:
            att_bytes = file_obj.read()
            if att_bytes:
                attachments.append((file_obj.filename, att_bytes))

    # Inline-Bilder einlesen
    inline_images: list[tuple[str, bytes, str]] = []
    from app.services.mailer_service import _image_content_subtype
    _unsupported_images: list[str] = []
    _SUPPORTED_IMG_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    for img_obj in files.getlist("inline_images"):
        if img_obj and img_obj.filename:
            ext = os.path.splitext(img_obj.filename.lower())[1]
            if ext in ('.heic', '.heif'):
                _unsupported_images.append(img_obj.filename)
                continue
            if ext not in _SUPPORTED_IMG_EXTENSIONS:
                _unsupported_images.append(img_obj.filename)
                continue
            img_bytes = img_obj.read()
            if img_bytes:
                # UUID-basierter CID ohne Punkte/Extension: verhindert Outlook-Bug
                # bei CIDs mit Dateiendungen wie .jpg, .png
                cid = f"img{uuid.uuid4().hex}"
                subtype = _image_content_subtype(img_obj.filename)
                inline_images.append((cid, img_bytes, subtype))
    if _unsupported_images:
        names = ', '.join(_unsupported_images)
        flash(
            f"Folgende Bilder wurden übersprungen, da das Format nicht von E-Mail-Clients "
            f"unterstützt wird: {names}. "
            f"Bitte Bilder vorher in JPG oder PNG umwandeln (z.B. per Windows-Fotos oder online-Konverter).",
            "warning",
        )

    sender_address = (
        (form.get("sender_address") or "").strip()
        or (cfg.mail_sender_address or "")
    )
    if not sender_address:
        flash("Keine Absenderadresse konfiguriert. Bitte E-Mail-Konfiguration prüfen.", "danger")
        return redirect(url_for("email_nl.send"))

    # Versand-Loop
    ok_recipients: list[str] = []
    error_recipients: list[str] = []

    def _send_to(to_addr: str, first_name: str = "", last_name: str = "") -> None:
        personal_body = body.replace("{first_name}", first_name).replace(
            "{last_name}", last_name
        )

        if mail_type == "newsletter":
            # Unsubscribe-Link anhängen
            # Token aus Person holen/generieren
            person = next(
                (p for p in recipient_persons if p.email == to_addr),
                None,
            )
            if person:
                if not person.newsletter_unsubscribe_token:
                    person.newsletter_unsubscribe_token = str(uuid.uuid4())
                    db.session.flush()
                token = person.newsletter_unsubscribe_token
                base_url = (
                    f"http://127.0.0.1:{_get_port()}"
                    if _running_locally()
                    else ""
                )
                unsub_url = f"{base_url}/email/unsubscribe/{token}"
                personal_body += (
                    "\n\n---\n"
                    "Newsletter abbestellen: Antworte einfach auf diese E-Mail mit dem Betreff 'Abmeldung'.\n"
                )

        MailerService.send_custom_email(
            to_email=to_addr,
            subject=subject,
            body=personal_body,
            cfg=cfg,
            sender_address=sender_address,
            attachments=attachments or None,
            inline_images=inline_images or None,
            inline_images_intro=inline_images_intro or None,
        )

    # Personen
    for p in recipient_persons:
        try:
            _send_to(p.email, p.first_name or "", p.last_name or "")
            ok_recipients.append(p.email)
        except Exception as exc:
            error_recipients.append(f"{p.email}: {exc}")

    # Freie Adressen
    for addr in free_emails:
        try:
            _send_to(addr)
            ok_recipients.append(addr)
        except Exception as exc:
            error_recipients.append(f"{addr}: {exc}")

    db.session.commit()  # newsletter_unsubscribe_token persistieren

    # Log-Eintrag
    status = "ok" if not error_recipients else ("partial" if ok_recipients else "error")
    log = EmailSendLog(
        sent_at=now_local().replace(tzinfo=None),
        subject=subject,
        body_preview=body[:500],
        mail_type=mail_type,
        status=status,
        error_detail=("; ".join(error_recipients[:5]) if error_recipients else None),
    )
    log.set_recipients(ok_recipients)
    db.session.add(log)
    db.session.commit()

    if ok_recipients:
        flash(
            f"E-Mail erfolgreich an {len(ok_recipients)} Empfänger gesendet."
            + (f" ({skipped_optout} Newsletter-Abmeldungen übersprungen.)" if skipped_optout else ""),
            "success",
        )
    if error_recipients:
        flash(
            f"Fehler bei {len(error_recipients)} Empfänger(n): "
            + " | ".join(error_recipients[:3]),
            "danger",
        )

    return redirect(url_for("email_nl.history"))


def _get_port() -> int:
    from flask import current_app
    try:
        return int(current_app.config.get("MANIFEST_PORT", 5000))
    except Exception:
        return 5000


def _running_locally() -> bool:
    return True  # Offline-Installer immer localhost


# ------------------------------------------------------------------
# GET /email/history  – Versand-Übersicht
# ------------------------------------------------------------------
@bp.route("/history")
def history():
    deny = _require_admin()
    if deny:
        return deny

    logs = (
        EmailSendLog.query
        .order_by(EmailSendLog.sent_at.desc())
        .limit(200)
        .all()
    )
    return render_template("email_newsletter/history.html", logs=logs)


# ------------------------------------------------------------------
# GET /email/history/<int:log_id>  – Versand-Detail
# ------------------------------------------------------------------
@bp.route("/history/<int:log_id>")
def history_detail(log_id: int):
    deny = _require_admin()
    if deny:
        return deny

    log = EmailSendLog.query.get_or_404(log_id)
    return render_template("email_newsletter/history_detail.html", log=log)


# ------------------------------------------------------------------
# POST /email/history/<int:log_id>/delete  – Versand-Log löschen (nur DEV)
# ------------------------------------------------------------------
@bp.route("/history/<int:log_id>/delete", methods=["POST"])
def history_delete(log_id: int):
    deny = _require_admin()
    if deny:
        return deny

    if not _is_dev_mode():
        abort(404)

    log = EmailSendLog.query.get_or_404(log_id)
    db.session.delete(log)
    db.session.commit()
    flash(f"Historie-Eintrag #{log_id} wurde gelöscht.", "success")
    return redirect(url_for("email_nl.history"))


# ------------------------------------------------------------------
# GET  /email/unsubscribe/<token>  – Abmeldeseite (öffentlich, kein Login)
# POST /email/unsubscribe/<token>  – Abmeldung bestätigen
# ------------------------------------------------------------------
@bp.route("/unsubscribe/<string:token>", methods=["GET", "POST"])
def unsubscribe(token: str):
    if not token or len(token) > 64:
        return render_template("email_newsletter/unsubscribe.html", state="invalid")

    person = Person.query.filter_by(newsletter_unsubscribe_token=token).first()
    if not person:
        return render_template("email_newsletter/unsubscribe.html", state="not_found")

    if request.method == "POST":
        person.newsletter_opt_out = True
        db.session.commit()
        return render_template(
            "email_newsletter/unsubscribe.html",
            state="done",
            person_name=person.first_name or "",
        )

    return render_template(
        "email_newsletter/unsubscribe.html",
        state="confirm",
        person_name=person.first_name or "",
        token=token,
    )
