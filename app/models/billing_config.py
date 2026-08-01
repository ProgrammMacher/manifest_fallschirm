# C:\manifest_fallschirm\app\models\billing_config.py
from datetime import date
from app import db


MANUAL_MAIL_BODY_TEMPLATE_DEFAULT = (
    "Liebe/r {first_name} {last_name},\n\n"
    "in der Anlage erhältst Du Deine Rechnung für {manual_title}.\n"
    "Sollte die Rechnung noch nicht bezahlt sein, bitten wir um Begleichung bis zwei Tage nach Erhalt der Rechnung.\n\n"
    "Bitte antworte nicht auf diese E-Mail, da sie automatisiert generiert wurde. Ggf. Kontakt siehe unten.\n\n"
    "Viele Grüße aus Dessau"
)

# =========================================================
# 1) BillingConfig
# Rechnungssteller + Zahlungsinfos + Online-Präsenz
# + globale Abrechnungsparameter (Schirmmiete)
# =========================================================
class BillingConfig(db.Model):
    __tablename__ = "billing_config"

    id = db.Column(db.Integer, primary_key=True)

    # -------------------------
    # Rechnungssteller
    # -------------------------
    company_name = db.Column(db.String(200), nullable=False)
    street = db.Column(db.String(200), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    city = db.Column(db.String(200), nullable=False)
    country = db.Column(
        db.String(200),
        nullable=False,
        default="Deutschland",
        server_default="Deutschland",
    )

    # -------------------------
    # Steuer / Rechtliches
    # -------------------------
    tax_id = db.Column(db.String(100), nullable=True)
    vat_id = db.Column(db.String(100), nullable=True)
    # ✅ Steuernummer (für Rechnungsausgabe)
    tax_number = db.Column(db.String(100), nullable=True)

    # -------------------------
    # Kontakt
    # -------------------------
    email = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(100), nullable=True)


    # =====================================================
    # E-Mail Versand (Rechnungen)
    # - konfigurierbar über /billing/admin/config
    # =====================================================
    mail_sender_address = db.Column(
        db.String(255),
        nullable=True,
        doc="Absender-E-Mail-Adresse für Rechnungsversand"
    )

    mail_sender_name = db.Column(
        db.String(255),
        nullable=True,
        default="Dessauer Fallschirmsportverein",
        doc="Absendername (z.B. Dessauer Fallschirmsportverein)"
    )


    mail_subject_template = db.Column(
        db.String(255),
        nullable=False,
        default="Deine Rechnung vom Dessauer Fallschirmsportverein",
        doc="Betreff-Vorlage für Rechnungs-E-Mails"
    )

    mail_body_template = db.Column(
        db.Text,
        nullable=False,
        default=(
            "Lieber {first_name} {last_name},\n\n"
            "in der Anlage erhältst Du Deine Rechnung für die Sprünge "
            "vom {invoice_date} auf dem Flugplatz {airfield_name}.\n\n"
            "Viele Grüße aus Dessau\n"
            "Dessauer Fallschirmsportverein"
        ),
        doc="Body-Vorlage für Rechnungs-E-Mails mit Platzhaltern"
    )

    mail_body_template_manual = db.Column(
        db.Text,
        nullable=False,
        default=MANUAL_MAIL_BODY_TEMPLATE_DEFAULT,
        doc="Body-Vorlage für manuelle Rechnungs-E-Mails mit Platzhaltern",
    )

    waiver_text_skydiver = db.Column(
        db.Text,
        nullable=True,
        doc="Textvorlage Enthaftungserklärung für Fallschirmspringer",
    )

    waiver_text_tandem = db.Column(
        db.Text,
        nullable=True,
        doc="Textvorlage Enthaftungserklärung für Tandemgäste",
    )

    # =====================================================
    # SMTP / E-Mail Versand (Konfiguration)
    # =====================================================
    smtp_server = db.Column(db.String(255), nullable=True)
    smtp_fallback_host = db.Column(db.String(255), nullable=True)
    smtp_port = db.Column(db.Integer, nullable=True)
    smtp_use_tls = db.Column(db.Boolean, nullable=False, default=True, server_default="1")
    smtp_use_ssl = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    smtp_username = db.Column(db.String(255), nullable=True)
    smtp_password = db.Column(db.String(255), nullable=True)


    # -------------------------
    # Optional: Logo
    # -------------------------
    logo_filename = db.Column(db.String(200), nullable=True)

    # -------------------------
    # Zahlungsinformationen
    # -------------------------
    payment_methods_text = db.Column(
        db.String(300),
        nullable=True,
        doc="z.B. Barzahlung, Girocard, Kreditkarte oder Überweisung",
    )
    bank_name = db.Column(db.String(200), nullable=True)
    iban = db.Column(db.String(50), nullable=True)
    bic = db.Column(db.String(50), nullable=True)
    creditor_id = db.Column(
        db.String(35),
        nullable=False,
        default="",
        server_default="",
        doc="Gläubiger-Identifikationsnummer (Creditor ID) für SEPA-Exports",
    )
    pain_version = db.Column(
        db.String(30),
        nullable=False,
        default="pain.008.001.02",
        server_default="pain.008.001.02",
        doc="pain-Version für SEPA-XML-Exports",
    )
    payment_terms = db.Column(
        db.String(200),
        nullable=True,
        doc="z.B. Zahlbar sofort ohne Abzug",
    )

    # -------------------------
    # Transaktionsgebühr (Konfiguration)
    # -------------------------
    transaction_fee_mode = db.Column(
        db.String(20),
        nullable=False,
        default="none",
        server_default="none",
        doc="none / fixed / percent",
    )
    transaction_fee_fixed_eur = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0,
        server_default="0",
        doc="Fixer Betrag (Brutto), z.B. 2.50",
    )
    transaction_fee_percent = db.Column(
        db.Numeric(5, 2),
        nullable=False,
        default=0,
        server_default="0",
        doc="Prozentwert (z.B. 0.75 für 0,75%)",
    )

    # -------------------------
    # Online-Präsenz (URLs)
    # -------------------------
    website = db.Column(
        db.String(300),
        nullable=True,
        doc="Öffentliche Website (vollständige URL, z.B. https://www.freifall-dessau.de)",
    )
    instagram_url = db.Column(
        db.String(300),
        nullable=True,
        doc="Instagram-Profil (vollständige URL)",
    )
    facebook_url = db.Column(
        db.String(300),
        nullable=True,
        doc="Facebook-Seite (vollständige URL)",
    )

    # -------------------------
    # QR-Codes (Grafikdateien)
    # Ablage: app/static/img/qr/
    # Im Formular wird NUR der Dateiname gepflegt
    # -------------------------
    qr_instagram_filename = db.Column(
        db.String(200),
        nullable=True,
        doc="QR-Code Instagram (Dateiname, z.B. qr_instagram.png)",
    )
    qr_facebook_filename = db.Column(
        db.String(200),
        nullable=True,
        doc="QR-Code Facebook (Dateiname, z.B. qr_facebook.png)",
    )
    qr_website_filename = db.Column(
        db.String(200),
        nullable=True,
        doc="QR-Code Website (Dateiname, z.B. qr_website.png)",
    )

    # =====================================================
    # Schirmmiete (Teil der Abrechnungslogik)
    # =====================================================
    # Verein
    canopy_rent_member_eur = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=15,
        server_default="15",
        doc="Schirmmiete Verein: Preis pro Sprung (Brutto)",
    )
    canopy_rent_member_max_count = db.Column(
        db.Integer,
        nullable=False,
        default=3,
        server_default="3",
        doc="Schirmmiete Verein: max. Anzahl pro Tag",
    )
    canopy_rent_member_vat_rate = db.Column(
        db.Numeric(5, 2),
        nullable=False,
        default=7,
        server_default="7",
        doc="Schirmmiete Verein: MwSt in Prozent",
    )

    # Partner-Verein
    canopy_rent_partner_member_eur = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=15,
        server_default="15",
        doc="Schirmmiete Partner-Verein: Preis pro Sprung (Brutto)",
    )
    canopy_rent_partner_member_max_count = db.Column(
        db.Integer,
        nullable=False,
        default=3,
        server_default="3",
        doc="Schirmmiete Partner-Verein: max. Anzahl pro Tag",
    )
    canopy_rent_partner_member_vat_rate = db.Column(
        db.Numeric(5, 2),
        nullable=False,
        default=7,
        server_default="7",
        doc="Schirmmiete Partner-Verein: MwSt in Prozent",
    )

    # Gast
    canopy_rent_guest_eur = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=20,
        server_default="20",
        doc="Schirmmiete Gast: Preis pro Sprung (Brutto)",
    )
    canopy_rent_guest_max_count = db.Column(
        db.Integer,
        nullable=False,
        default=3,
        server_default="3",
        doc="Schirmmiete Gast: max. Anzahl pro Tag",
    )
    canopy_rent_guest_vat_rate = db.Column(
        db.Numeric(5, 2),
        nullable=False,
        default=7,
        server_default="7",
        doc="Schirmmiete Gast: MwSt in Prozent",
    )

    # Tandemmaster
    canopy_rent_tm_eur = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=25,
        server_default="25",
        doc="Schirmmiete Tandemmaster: Preis pro Sprung (Brutto)",
    )
    canopy_rent_tm_max_count = db.Column(
        db.Integer,
        nullable=False,
        default=50,
        server_default="50",
        doc="Schirmmiete Tandemmaster: max. Anzahl pro Tag",
    )
    canopy_rent_tm_vat_rate = db.Column(
        db.Numeric(5, 2),
        nullable=False,
        default=19,
        server_default="19",
        doc="Schirmmiete Tandemmaster: MwSt in Prozent",
    )

    def __repr__(self) -> str:
        return f"<BillingConfig {self.company_name}>"


# =========================================================
# 2) BillingPricePeriod
# =========================================================
class BillingPricePeriod(db.Model):
    __tablename__ = "billing_price_period"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    valid_from = db.Column(db.Date, nullable=False)
    valid_to = db.Column(db.Date, nullable=True)

    # (Legacy) Periodenweite Orga (wird ab jetzt als Default/Fallback behandelt)
    orga_fee_eur = db.Column(db.Numeric(10, 2), nullable=True)
    orga_fee_mode = db.Column(
        db.String(20),
        nullable=False,
        default="period",
        server_default="period",
    )
    orga_fee_vat_strategy = db.Column(
        db.String(20),
        nullable=False,
        default="max_status",
        server_default="max_status",
    )

    is_homebase_default = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    prices = db.relationship(
        "BillingPrice",
        back_populates="period",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def is_active_on(self, day: date) -> bool:
        if self.valid_from and day < self.valid_from:
            return False
        if self.valid_to and day > self.valid_to:
            return False
        return True

    def __repr__(self) -> str:
        return f"<BillingPricePeriod {self.name}>"


# =========================================================
# 3) BillingPrice
# =========================================================
class BillingPrice(db.Model):
    __tablename__ = "billing_price"

    id = db.Column(db.Integer, primary_key=True)

    # flugplatz_id entfernt: Preismatrix gilt global für alle Flugplätze
    period_id = db.Column(
        db.Integer,
        db.ForeignKey("billing_price_period.id"),
        nullable=False,
        index=True,
    )
    period = db.relationship("BillingPricePeriod", back_populates="prices")

    status_code = db.Column(
        db.String(50),
        nullable=False,
        index=True,
    )
    height_m = db.Column(db.Integer, nullable=False)

    price_eur = db.Column(
        db.Numeric(10, 2),
        nullable=False,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "period_id",
            "status_code",
            "height_m",
            name="uq_price_period_status_height",
        ),
    )

    def __repr__(self) -> str:
        return f"<BillingPrice {self.status_code} {self.height_m}m {self.price_eur}€>"


# =========================================================
# 4) BillingOrgaRule (bestehend)
# Orga pro Status pro Flugplatz + Periode
# =========================================================
class BillingOrgaRule(db.Model):
    __tablename__ = "billing_orga_rule"

    id = db.Column(db.Integer, primary_key=True)

    # flugplatz_id entfernt: Orga-Regeln gelten global für alle Flugplätze
    period_id = db.Column(
        db.Integer,
        db.ForeignKey("billing_price_period.id"),
        nullable=False,
        index=True,
    )

    status_code = db.Column(
        db.String(50),
        nullable=False,
        index=True,
    )

    apply_orga = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "period_id",
            "status_code",
            name="uq_billing_orga_rule",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<BillingOrgaRule period={self.period_id} status={self.status_code} "
            f"apply_orga={self.apply_orga}>"
        )


# =========================================================
# 5) BillingOrgaConfig (NEU)
# Orga-Betrag + Modus pro Flugplatz + Periode
# =========================================================
class BillingOrgaConfig(db.Model):
    __tablename__ = "billing_orga_config"

    id = db.Column(db.Integer, primary_key=True)

    # flugplatz_id entfernt: Orga-Konfiguration gilt global für alle Flugplätze
    period_id = db.Column(
        db.Integer,
        db.ForeignKey("billing_price_period.id"),
        nullable=False,
        index=True,
    )

    # Brutto
    orga_fee_eur = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    # 'period' = einmal pro Periode, 'day' = pro Tag
    orga_fee_mode = db.Column(
        db.String(20),
        nullable=False,
        default="period",
        server_default="period",
    )

    # Strategie zur MwSt-Ermittlung (vorbereitet)
    orga_fee_vat_strategy = db.Column(
        db.String(20),
        nullable=False,
        default="max_status",
        server_default="max_status",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "period_id",
            name="uq_billing_orga_config",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<BillingOrgaConfig period={self.period_id} "
            f"amount={self.orga_fee_eur} mode={self.orga_fee_mode}>"
        )