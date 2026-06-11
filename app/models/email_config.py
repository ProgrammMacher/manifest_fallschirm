from app import db


class EmailConfig(db.Model):
    """
    Konfiguration für E-Mail / Newsletter-Versand.
    Separate Tabelle von BillingConfig, gleiche SMTP-Attributnamen
    für Kompatibilität mit mailer_service.
    """
    __tablename__ = "email_config"

    id = db.Column(db.Integer, primary_key=True)

    # =====================================================
    # Block A: Sprungplatzbetreiber
    # =====================================================
    company_name = db.Column(db.String(255), nullable=True)
    logo_filename = db.Column(db.String(200), nullable=True)
    street = db.Column(db.String(255), nullable=True)
    zip_code = db.Column(db.String(10), nullable=True)
    city = db.Column(db.String(50), nullable=True)

    # =====================================================
    # Block C: Online-Präsenz
    # =====================================================
    website = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    tax_number = db.Column(db.String(50), nullable=True)
    instagram_url = db.Column(db.String(255), nullable=True)
    facebook_url = db.Column(db.String(255), nullable=True)

    # =====================================================
    # Block D: E-Mail-Versand Standardwerte
    # =====================================================
    mail_sender_address = db.Column(db.String(255), nullable=True)
    mail_sender_name = db.Column(db.String(255), nullable=True)
    mail_subject_template = db.Column(db.String(500), nullable=True)
    mail_body_template = db.Column(db.Text, nullable=True)

    # =====================================================
    # Block E: SMTP (gleiche Attributnamen wie BillingConfig)
    # =====================================================
    smtp_server = db.Column(db.String(255), nullable=True)
    smtp_fallback_host = db.Column(db.String(255), nullable=True)
    smtp_port = db.Column(db.Integer, nullable=True)
    smtp_use_tls = db.Column(
        db.Boolean, nullable=False, default=True, server_default="1"
    )
    smtp_use_ssl = db.Column(
        db.Boolean, nullable=False, default=False, server_default="0"
    )
    smtp_username = db.Column(db.String(255), nullable=True)
    smtp_password = db.Column(db.String(255), nullable=True)

    # =====================================================
    # Block F: QR-Codes
    # =====================================================
    qr_instagram_filename = db.Column(db.String(200), nullable=True)
    qr_facebook_filename = db.Column(db.String(200), nullable=True)
    qr_website_filename = db.Column(db.String(200), nullable=True)

    def __repr__(self) -> str:
        return f"<EmailConfig id={self.id} sender={self.mail_sender_address}>"
