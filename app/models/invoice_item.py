# C:\manifest_fallschirm\app\models\invoice_item.py
from decimal import Decimal
from app import db


class InvoiceItem(db.Model):
    __tablename__ = "invoice_item"

    id = db.Column(db.Integer, primary_key=True)

    # Beziehung zur Rechnung
    invoice_id = db.Column(
        db.Integer,
        db.ForeignKey("invoice.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    invoice = db.relationship(
        "Invoice",
        back_populates="items",
        lazy="selectin",
        passive_deletes=False
    )

    # Beziehung zum LoadEntry
    load_entry_id = db.Column(
        db.Integer,
        db.ForeignKey("load_entry.id", ondelete="RESTRICT"),
        nullable=True,
        index=True
    )
    load_entry = db.relationship(
        "LoadEntry",
        back_populates="invoice_items",
        lazy="selectin",
        passive_deletes=False
    )

    # Betrag dieses Postens (BRUTTO)
    amount = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0,
        server_default="0"
    )

    # Quelle der Position: load = automatisch aus Sprungdaten, manual = manuell erfasst
    item_source = db.Column(
        db.String(20),
        nullable=False,
        default="load",
        server_default="load",
        index=True,
    )

    # Mengen-/Einzelpreisfelder für manuelle Positionen (optional auch für andere Positionen befüllbar)
    quantity = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=Decimal("1.00"),
        server_default="1",
    )

    unit_price_gross = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )

    manual_position_code = db.Column(db.String(50), nullable=True)
    manual_unit = db.Column(db.String(50), nullable=True)

    # --- MwSt / Netto-Aufteilung (neu, DB-Spalten sind bereits migriert) ---
    # MwSt-Satz in Prozent, z. B. 0.00 / 7.00 / 19.00
    vat_rate = db.Column(
        db.Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0"
    )

    # Netto-Anteil
    net_amount = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0"
    )

    # MwSt-Anteil
    vat_amount = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0"
    )

    # Beschreibung (z. B. "Sprung 4000 m – Vereinsmitglied")
    description = db.Column(db.String(200), nullable=True)

    # Snapshot der Preis- und Basislogik zum Zeitpunkt der Rechnungserstellung
    price_source_eur = db.Column(
        db.Numeric(10, 2),
        nullable=True,
        default=None,
    )
    price_source_vat_rate = db.Column(
        db.Numeric(5, 2),
        nullable=True,
        default=None,
    )
    ku_credit_payout_basis = db.Column(
        db.String(10),
        nullable=True,
        default=None,
    )
    ku_credit_payout_amount = db.Column(
        db.Numeric(10, 2),
        nullable=True,
        default=None,
    )

    @property
    def gross_decimal(self) -> Decimal:
        return Decimal(str(self.amount or 0))

    @property
    def net_decimal(self) -> Decimal:
        return Decimal(str(self.net_amount or 0))

    @property
    def vat_decimal(self) -> Decimal:
        return Decimal(str(self.vat_amount or 0))

    def __repr__(self) -> str:
        return f"<InvoiceItem id={self.id} gross={self.amount} vat_rate={self.vat_rate}>"