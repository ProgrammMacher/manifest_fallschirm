# C:\manifest_fallschirm\app\models\load.py
from __future__ import annotations

from datetime import date, datetime
from typing import Any, List, Optional, cast

from sqlalchemy.orm import object_session

from app import db
from app.models.load_entry import LoadEntry
from app.services.tandem_block_service import build_tandem_blocks


class Load(db.Model):
    __tablename__ = "load"

    id = db.Column(db.Integer, primary_key=True)

    # ---------------------------------------------------------
    # Basisdaten
    # ---------------------------------------------------------
    load_number = db.Column(
        db.Integer,
        nullable=False,
        index=True,
    )

    height_m = db.Column(
        db.Integer,
        nullable=False,
        default=3000,
    )

    # Maximal zulässige Nutzlast (kg). Optional.
    max_payload_kg = db.Column(
        db.Float,
        nullable=True,
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="open",
        server_default="open",
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.now(),
    )

    # ---------------------------------------------------------
    # Zeit
    # ---------------------------------------------------------
    scheduled_time = db.Column(
     db.DateTime,
     nullable=True,
    )
    actual_time = db.Column(
     db.DateTime,
     nullable=True,
    )

    # ---------------------------------------------------------
    # ✅ Tankpause / Tanken erforderlich (reine Information)
    # ---------------------------------------------------------
    # Fachlich:
    # - Nur Anzeige (keine Abrechnung, keine Logik/Sperre)
    # - Binär: Ja/Nein
    # - Statistik später: fuel_required == True + actual_time (Datum/Uhrzeit)
    fuel_required = db.Column(
     db.Boolean,
     nullable=False,
     default=False,
     server_default="0",
     index=True,
    )

    # ---------------------------------------------------------
    # Beziehungen
    # ---------------------------------------------------------
    airfield_id = db.Column(
        db.Integer,
        db.ForeignKey("flugplatz.id"),
        nullable=False,
        index=True,
    )
    airfield = db.relationship(
        "Flugplatz",
        back_populates="loads",
        passive_deletes=False,
    )

    aircraft_id = db.Column(
        db.Integer,
        db.ForeignKey("aircraft.id"),
        nullable=False,
        index=True,
    )
    aircraft = db.relationship(
        "Aircraft",
        back_populates="loads",
        passive_deletes=False,
    )

    # ---------------------------------------------------------
    # Preismodell / Preismatrix (Freeze pro Load)
    # ---------------------------------------------------------
    # Das Preismodell wird ausschließlich über /pricing/ gesetzt.
    # Loads übernehmen beim Erstellen das aktuell aktive Preismodell.
    # In der Load-UI wird es nur angezeigt (read-only).
    #
    # Wichtig für Übergangsphase: nullable=True, damit bestehende DBs ohne Migration nicht sofort brechen.
    pricing_model_id = db.Column(
    db.Integer,
    db.ForeignKey("billing_price_period.id"),
    nullable=True,
    index=True,
    )

    pricing_model = db.relationship(
    "BillingPricePeriod",
    lazy="selectin",
    )

    # KEIN delete-orphan! (LoadEntries werden manuell gelöscht)
    entries = db.relationship(
        "LoadEntry",
        back_populates="load",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ---------------------------------------------------------
    # Nutzlast
    # ---------------------------------------------------------
    def _safe_float(self, value, default: float = 0.0) -> float:
        try:
            if value is None:
                return float(default)
            return float(value)
        except Exception:
            return float(default)

    def _entries_list(self) -> List[LoadEntry]:
        """Typed Zugriff fuer Pylance; runtime bleibt eine normale Relationship-Liste."""
        return cast(List[LoadEntry], cast(Any, self.entries) or [])

    @property
    def payload_sum_kg(self) -> float:
        """
        Summe der Nutzlast aller Einträge.

        Kompatibel zur bisherigen Logik:
        - bevorzugt gespeichertes payload_kg
        - sonst calculated_payload
        """
        total = 0.0
        for e in self._entries_list():
            if getattr(e, "payload_kg", None) is not None:
                total += self._safe_float(getattr(e, "payload_kg", None), 0.0)
            else:
                total += self._safe_float(getattr(e, "calculated_payload", None), 0.0)
        return float(total)

    @property
    def remaining_payload_kg(self) -> float:
        # Verhalten kompatibel: None -> 0.0
        if self.max_payload_kg is None:
            return 0.0
        return float(self.max_payload_kg - self.payload_sum_kg)

    # ✅ INKREMENTELL: UI-Helfer
    @property
    def payload_ratio(self) -> Optional[float]:
        """payload_sum / max_payload (None wenn kein Limit)."""
        if self.max_payload_kg is None:
            return None
        if self.max_payload_kg <= 0:
            return None
        return float(self.payload_sum_kg / float(self.max_payload_kg))

    @property
    def payload_state(self) -> str:
        """Ampel-Zustand: neutral / green / yellow / red."""
        ratio = self.payload_ratio
        if ratio is None:
            return "neutral"
        if ratio > 1.0:
            return "red"
        if ratio > 0.9:
            return "yellow"
        return "green"

    # ✅ INKREMENTELL: Sitzplatz-Helfer
    @property
    def seats_occupied(self) -> int:
        return int(len(self._entries_list()))

    @property
    def seats_capacity(self) -> int:
        return int(getattr(self.aircraft, "seats", 0) or 0)

    # ---------------------------------------------------------
    # Abrechnung / Zahlung (für UI-Logik)
    # ---------------------------------------------------------
    @property
    def has_paid_entries(self) -> bool:
        """True, wenn mindestens ein Eintrag dieses Loads als bezahlt markiert ist."""
        return any(getattr(e, "paid", False) for e in self._entries_list())

    @property
    def has_billed_entries(self) -> bool:
        """True, wenn mindestens ein Eintrag dieses Loads als abgerechnet markiert ist."""
        return any(getattr(e, "billed", False) for e in self._entries_list())

    @property
    def has_linked_invoice_items(self) -> bool:
        """True, wenn zu Eintraegen dieses Loads Rechnungspositionen existieren."""
        if not getattr(self, "id", None):
            return False

        from app.models.invoice_item import InvoiceItem

        session = object_session(self) or db.session
        return (
            session.query(InvoiceItem.id)
            .join(LoadEntry, LoadEntry.id == InvoiceItem.load_entry_id)
            .filter(LoadEntry.load_id == self.id)
            .limit(1)
            .first()
        ) is not None

    # ---------------------------------------------------------
    # Block-Erkennung (für Liste/Editor/Detail)
    # ---------------------------------------------------------
    @property
    def blocks(self):
        return build_tandem_blocks(self)

    # ---------------------------------------------------------
    # ✅ Bugfix: __repr__ MUSS string liefern (vorher Tuple durch trailing comma)
    # ---------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<Load {self.id} "
            f"Nr={self.load_number} "
            f"Höhe={self.height_m}m "
            f"Flugplatz={self.airfield.name if self.airfield else '??'} "
            f"Status={self.status}>"
        )

    # ---------------------------------------------------------
    # Kompatibilitaets-Helfer
    # ---------------------------------------------------------
    @property
    def operation_date(self) -> Optional[date]:
        """Fachlicher Betriebstag ohne eigene DB-Spalte (actual_time -> created_at)."""
        dt = self.actual_time or self.created_at
        if not dt:
            return None
        return dt.date()


# EOF