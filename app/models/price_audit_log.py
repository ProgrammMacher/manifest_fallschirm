# C:\manifest_fallschirm\app\models\price_audit_log.py

from datetime import datetime
from app import db


class PriceAuditLog(db.Model):
    __tablename__ = "price_audit_log"

    id = db.Column(db.Integer, primary_key=True)

    # Zeitpunkt der Änderung
    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.now()
    )

    # Benutzer, der die Änderung ausgelöst hat
    user = db.Column(db.String(100), nullable=False)

    # Beschreibung der Aktion (z. B. "Preis geändert", "Neuer Preis angelegt")
    action = db.Column(db.String(255), nullable=False)

    # Alter Wert (JSON, Text, etc.)
    old_value = db.Column(db.Text, nullable=True)

    # Neuer Wert (JSON, Text, etc.)
    new_value = db.Column(db.Text, nullable=True)

    # Grund für die Änderung (Pflichtfeld)
    reason = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<PriceAuditLog id={self.id} time={self.timestamp}>"
