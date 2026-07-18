from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import event, inspect

from app import db


class SepaExport(db.Model):
    __tablename__ = "sepa_export"

    id = db.Column(db.Integer, primary_key=True)
    export_code = db.Column(db.String(20), nullable=False, unique=True, index=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.now(),
        index=True,
    )
    created_by = db.Column(db.String(100), nullable=False)

    invoice_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default="0")

    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(1024), nullable=False)

    # Lifecycle für spätere Erweiterungen: created -> submitted -> executed -> file_deleted
    status = db.Column(db.String(30), nullable=False, default="created", server_default="created", index=True)
    xml_version = db.Column(db.String(30), nullable=False, default="infra-v1", server_default="infra-v1")
    selection_scope = db.Column(db.String(30), nullable=False, default="manual", server_default="manual")

    submitted_at = db.Column(db.DateTime, nullable=True)
    submitted_by = db.Column(db.String(100), nullable=True)
    executed_at = db.Column(db.DateTime, nullable=True)
    executed_by = db.Column(db.String(100), nullable=True)
    file_deleted_at = db.Column(db.DateTime, nullable=True)
    file_deleted_by = db.Column(db.String(100), nullable=True)

    invoices = db.relationship(
        "SepaExportInvoice",
        back_populates="export",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def total_amount_decimal(self) -> Decimal:
        return Decimal(str(self.total_amount or "0.00"))


class SepaExportInvoice(db.Model):
    __tablename__ = "sepa_export_invoice"

    id = db.Column(db.Integer, primary_key=True)

    export_id = db.Column(
        db.Integer,
        db.ForeignKey("sepa_export.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id = db.Column(
        db.Integer,
        db.ForeignKey("invoice.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    invoice_number_snapshot = db.Column(db.String(50), nullable=False)
    invoice_total_snapshot = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default="0")
    person_name_snapshot = db.Column(db.String(200), nullable=False)
    iban_snapshot = db.Column(db.String(34), nullable=True)
    mandate_reference_snapshot = db.Column(db.String(32), nullable=True)
    payment_method_snapshot = db.Column(db.String(20), nullable=True)
    payment_state_snapshot = db.Column(db.String(20), nullable=False)

    load_date_from = db.Column(db.Date, nullable=True)
    load_date_to = db.Column(db.Date, nullable=True)
    load_dates_text = db.Column(db.String(500), nullable=True)

    export = db.relationship("SepaExport", back_populates="invoices")
    invoice = db.relationship("Invoice", lazy="joined", back_populates="sepa_exports")


_SNAPSHOT_FIELDS = {
    "invoice_id",
    "invoice_number_snapshot",
    "invoice_total_snapshot",
    "person_name_snapshot",
    "iban_snapshot",
    "mandate_reference_snapshot",
    "payment_method_snapshot",
    "payment_state_snapshot",
    "load_date_from",
    "load_date_to",
    "load_dates_text",
}


@event.listens_for(SepaExportInvoice, "before_update")
def _prevent_snapshot_update(_mapper, _connection, target: SepaExportInvoice):
    state = inspect(target)
    for field_name in _SNAPSHOT_FIELDS:
        attr = state.attrs.get(field_name)
        if attr is not None and attr.history.has_changes():
            raise ValueError(f"Snapshot field '{field_name}' is immutable after export creation.")
