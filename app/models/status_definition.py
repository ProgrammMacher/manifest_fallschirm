# C:\manifest_fallschirm\app\models\status_definition.py
from datetime import datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint
from app import db


class StatusDefinition(db.Model):
    __tablename__ = "status_definitions"

    id = db.Column(db.Integer, primary_key=True)

    # Technischer Code (z. B. "Verein", "G‑TD", "TD", "Video")
    # WICHTIG: NICHT unique, weil wir versionieren!
    code = db.Column(db.String(50), nullable=False, index=True)

    # Menschlich lesbarer Name
    label = db.Column(db.String(100), nullable=False, index=True)

    # Beschreibung (optional)
    beschreibung = db.Column(db.String(255), nullable=True)

    # Sortierreihenfolge für UI
    sort_order = db.Column(
        db.Integer,
        nullable=False,
        default=100,
        server_default="100",
        index=True
    )

    # Preise nach Absprunghöhe (Numeric statt Float!)
    preis_1500 = db.Column(db.Numeric(10, 2), nullable=True)
    preis_3000 = db.Column(db.Numeric(10, 2), nullable=True)
    preis_4000 = db.Column(db.Numeric(10, 2), nullable=True)

    # MwSt-Satz pro Status (neu): 0.00 / 7.00 / 19.00
    vat_rate = db.Column(
        db.Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0"
    )

    # Versionierung
    valid_from = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.now()
    )
    valid_to = db.Column(db.DateTime, nullable=True)

    # Aktivitätsflag
    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True
    )

    # Beziehung zu LoadEntry
    # WICHTIG: KEIN delete-orphan, sonst würden Sprünge verschwinden!
    load_entries = db.relationship(
        "LoadEntry",
        back_populates="status_definition",
        cascade="save-update, merge",
        lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_valid_range"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<StatusDefinition id={self.id} "
            f"code='{self.code}' "
            f"label='{self.label}' "
            f"vat_rate={self.vat_rate} "
            f"active={self.is_active}>"
        )