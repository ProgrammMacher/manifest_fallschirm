# C:\manifest_fallschirm\app\models\load_entry.py
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import event

from app import db
from app.helpers.status_code import normalize_status_code


class LoadEntry(db.Model):
    __tablename__ = "load_entry"

    id = db.Column(db.Integer, primary_key=True)

    load_id = db.Column(db.Integer, db.ForeignKey("load.id"), nullable=False, index=True)
    load = db.relationship("Load", back_populates="entries", passive_deletes=False)

    person_id = db.Column(db.Integer, db.ForeignKey("person.id"), nullable=False, index=True)
    person = db.relationship("Person", back_populates="load_entries", passive_deletes=False)

    status_definition_id = db.Column(
        db.Integer, db.ForeignKey("status_definitions.id"), nullable=True, index=True
    )
    status_definition = db.relationship("StatusDefinition", back_populates="load_entries")

    invoice_items = db.relationship(
        "InvoiceItem",
        back_populates="load_entry",
        cascade="save-update, merge",
        lazy="dynamic"
    )

    seat = db.Column(db.Integer, nullable=True)
    height_m = db.Column(db.Integer, nullable=False, server_default="0")

    # WICHTIG: status_code wird ab jetzt automatisch normalisiert (siehe Event-Listener unten)
    status_code = db.Column(db.String(50), nullable=False, index=True)

    is_teacher = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    is_video = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    gear_rental = db.Column(db.Boolean, nullable=False, default=False, server_default="0")

    payload_kg = db.Column(db.Float, nullable=True)

    billed = db.Column(db.Boolean, nullable=False, default=False, server_default="0", index=True)
    billed_at = db.Column(db.DateTime, nullable=True)

    paid = db.Column(db.Boolean, nullable=False, default=False, server_default="0", index=True)
    paid_at = db.Column(db.DateTime, nullable=True)

    final_price = db.Column(db.Float, nullable=True)
    preis_berechnet = db.Column(db.Float, nullable=True)

    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, server_default=db.func.now()
    )

    @property
    def effective_price(self) -> float:
        if self.final_price is not None:
            return float(self.final_price)
        if self.preis_berechnet is not None:
            return float(self.preis_berechnet)
        return 0.0

    @property
    def effective_price_decimal(self) -> Decimal:
        return Decimal(str(self.effective_price))

    @property
    def calculated_payload(self) -> float:
        if self.payload_kg is not None:
            return float(self.payload_kg)
        if self.person and getattr(self.person, "weight_kg", None):
            return float(self.person.weight_kg + 15)
        return 0.0

    def mark_billed(self, price: Optional[float] = None) -> None:
        if price is not None:
            self.final_price = price
        elif self.preis_berechnet is not None:
            self.final_price = self.preis_berechnet
        self.billed = True
        self.billed_at = datetime.utcnow()

    def mark_paid(self) -> None:
        self.paid = True
        self.paid_at = datetime.utcnow()

    def __repr__(self) -> str:
        return (
            f"<LoadEntry {self.id} "
            f"Load={self.load_id} "
            f"Person={self.person_id} "
            f"Höhe={self.height_m} "
            f"Status={self.status_code}>"
        )


# ---------------------------------------------------------
# Automatische Normalisierung: vor Insert/Update
# ---------------------------------------------------------
@event.listens_for(LoadEntry, "before_insert")
def _normalize_status_before_insert(mapper, connection, target: LoadEntry):
    target.status_code = normalize_status_code(target.status_code)


@event.listens_for(LoadEntry, "before_update")
def _normalize_status_before_update(mapper, connection, target: LoadEntry):
    target.status_code = normalize_status_code(target.status_code)