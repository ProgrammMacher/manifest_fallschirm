# C:\manifest_fallschirm\app\models\person.py

from datetime import date, datetime
from typing import Optional

from app import db


class Person(db.Model):
    __tablename__ = "person"

    id = db.Column(db.Integer, primary_key=True)

    # Pflichtfelder
    first_name = db.Column(db.String(50), nullable=False, index=True)
    last_name = db.Column(db.String(50), nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=False, index=True)

    # E-Mail: fachlich Pflicht, technisch tolerant
    email = db.Column(db.String(100), nullable=True, index=True)

    # Sprungrelevante Pflichtdaten
    weight_kg = db.Column(db.Integer, nullable=False)

    # Optionale Körperdaten
    height_cm = db.Column(db.Integer, nullable=True)
    birthdate = db.Column(db.Date, nullable=True)

    # Adresse
    street_and_number = db.Column(db.String(120), nullable=True)
    zip_code = db.Column(db.String(10), nullable=True)
    city = db.Column(db.String(50), nullable=True)

    # Mitgliedschaft
    is_member = db.Column(db.Boolean, nullable=False, default=False, server_default="0")

    # Partner-Verein (eigener Status, exklusiv zu Mitglied/Gast)
    is_partner_verein = db.Column(db.Boolean, nullable=False, default=False, server_default="0")

    # Tandemgast
    is_tandem_guest = db.Column(db.Boolean, nullable=False, default=False, server_default="0")

    # Tandemmaster (nur fuer UI-Filter im Loadeditor)
    is_tandemmaster = db.Column(db.Boolean, nullable=False, default=False, server_default="0")

    # Schüler (nur fuer UI-Filter im Loadeditor)
    is_student = db.Column(db.Boolean, nullable=False, default=False, server_default="0")

    # Video (nur fuer UI-Filter im Loadeditor)
    is_video = db.Column(db.Boolean, nullable=False, default=False, server_default="0")

    # Lehrer (manuell)
    is_teacher = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    teacher_license_expires = db.Column(db.Date, nullable=True)

    # AFF-Lehrer (neu)
    is_aff_teacher = db.Column(db.Boolean, nullable=False, default=False, server_default="0")

    # Schüler-AFF (neu)
    is_aff_student = db.Column(db.Boolean, nullable=False, default=False, server_default="0")

    # Lizenz & Versicherung
    license_number = db.Column(db.String(50), nullable=True)
    insurance_provider = db.Column(db.String(100), nullable=True)
    insurance_number = db.Column(db.String(100), nullable=True)

    # Datei-Uploads
    license_file = db.Column(db.String(255), nullable=True)
    insurance_file = db.Column(db.String(255), nullable=True)

    # Notfallkontakt
    emergency_name = db.Column(db.String(100), nullable=True)
    emergency_relation = db.Column(db.String(50), nullable=True)
    emergency_phone = db.Column(db.String(30), nullable=True)
    emergency_email = db.Column(db.String(100), nullable=True)

    # Konto / Lastschrift
    iban = db.Column(db.String(34), nullable=True, index=True)
    bic = db.Column(db.String(11), nullable=True)
    account_holder = db.Column(db.String(120), nullable=True)

    # Kommentar & Notizen
    comment = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    original_name = db.Column(db.String(120), nullable=True)

    # Newsletter
    newsletter_opt_out = db.Column(
        db.Boolean, nullable=False, default=False, server_default="0"
    )
    newsletter_unsubscribe_token = db.Column(db.String(64), nullable=True, index=True)

    # Zeitstempel (intern UTC, Anzeige in Berlin)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.now()
    )

    # Enthaftung
    liability_waiver_date = db.Column(db.Date, nullable=True)

    # -----------------------------
    # SOFT DELETE (NEU)
    # -----------------------------
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)
    deleted_reason = db.Column(db.String(255), nullable=True)

    # Beziehungen
    load_entries = db.relationship(
        "LoadEntry",
        back_populates="person",
        cascade="save-update, merge",
        lazy="dynamic",
        passive_deletes=True
    )
    invoices = db.relationship(
        "Invoice",
        back_populates="person",
        cascade="save-update, merge",
        lazy="dynamic",
        passive_deletes=True
    )

    # -----------------------------
    # Helper
    # -----------------------------
    def __repr__(self) -> str:
        return f"<Person {self.id}: {self.first_name} {self.last_name}>"

    @property
    def current_name(self) -> str:
        fn = (self.first_name or "").strip()
        ln = (self.last_name or "").strip()
        return f"{fn} {ln}".strip()

    @property
    def full_name(self) -> str:
        current = self.current_name
        original = (self.original_name or "").strip()
        if original and original.casefold() != current.casefold():
            return f"{current} ({original})"
        return current

    def remember_original_name(self, previous_name: Optional[str] = None) -> None:
        previous = (previous_name or "").strip()
        current = self.current_name
        if not previous or not current:
            return
        if previous.casefold() == current.casefold():
            return
        if not self.original_name:
            self.original_name = previous

    @property
    def has_email(self) -> bool:
        return bool(self.email and self.email.strip())

    # Softdelete
    @property
    def is_archived(self) -> bool:
        return self.deleted_at is not None

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None

    # ✅ Bugfix: Signature/Typing wieder syntaktisch korrekt (ohne Funktionsänderung)
    def archive(self, reason: Optional[str] = None) -> None:
        if self.deleted_at is None:
            self.deleted_at = datetime.utcnow()
            self.deleted_reason = reason or None

    def restore(self) -> None:
        self.deleted_at = None
        self.deleted_reason = None

    def can_hard_delete(self) -> bool:
        """Harddelete nur wenn nie in Load und keine Rechnung."""
        try:
            return (self.load_entries.count() == 0) and (self.invoices.count() == 0)
        except Exception:
            return False

    # Enthaftung (Tandemgäste brauchen keine gültige Enthaftung)
    @property
    def liability_waiver_valid(self) -> bool:
        # ✅ Tandemgäste / Mitflieger sind ausgenommen
        if self.is_tandem_guest:
            return True
        if not self.liability_waiver_date:
            return False
        return self.liability_waiver_date.year == date.today().year

    # ✅ Bugfix: Rückgabetyp wieder syntaktisch korrekt
    @property
    def liability_waiver_year(self) -> Optional[int]:
        return self.liability_waiver_date.year if self.liability_waiver_date else None

    # Lehrer-Lizenz-Logik (bestehend)
    @property
    def teacher_license_status(self) -> str:
        if not self.is_teacher or not self.teacher_license_expires:
            return "none"
        today = date.today()
        diff_days = (self.teacher_license_expires - today).days
        if diff_days < 0:
            return "expired"
        if diff_days < 120:
            return "warning"
        return "ok"

    # ✅ NEU: Bool-Flag für Load-Validierung (keine UI-Änderung notwendig)
    @property
    def teacher_license_valid(self) -> bool:
        """
        Lehrerlizenz ist gültig, wenn das Ablaufdatum nicht überschritten ist.
        - Nicht-Lehrer: True (nicht relevant)
        - Lehrer: Ablaufdatum muss gesetzt sein und >= heute
        """
        if not self.is_teacher:
            return True
        if not self.teacher_license_expires:
            return False
        return self.teacher_license_expires >= date.today()

    # ✅ Bugfix: Rückgabetyp wieder syntaktisch korrekt
    @property
    def teacher_license_message(self) -> Optional[str]:
        if self.teacher_license_status == "none":
            return None
        expires = self.teacher_license_expires.strftime("%d.%m.%Y")
        match self.teacher_license_status:
            case "expired":
                return f"Achtung: Lehrerlizenz am {expires} abgelaufen."
            case "warning":
                return "Achtung: Lehrerlizenz läuft ab."
            case "ok":
                return f"Lehrerlizenz gültig bis {expires}."
        return None

    # ✅ Bugfix: Rückgabetyp wieder syntaktisch korrekt
    @property
    def teacher_license_color(self) -> Optional[str]:
        match self.teacher_license_status:
            case "expired":
                return "red"
            case "warning":
                return "yellow"
            case "ok":
                return "green"
        return None