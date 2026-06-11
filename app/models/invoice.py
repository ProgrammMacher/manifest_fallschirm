# C:\manifest_fallschirm\app\models\invoice.py
from decimal import Decimal

from app import db, now_local
now_berlin = now_local  # Alias für Abwärtskompatibilität
from app.models.invoice_item import InvoiceItem


class Invoice(db.Model):
    __tablename__ = "invoice"

    # Abweichende Rechnungsanschrift (optional, überschreibt Personendaten)
    billing_address_name = db.Column(db.String(200), nullable=True)
    billing_address_street = db.Column(db.String(200), nullable=True)
    billing_address_zip = db.Column(db.String(20), nullable=True)
    billing_address_city = db.Column(db.String(100), nullable=True)
    billing_address_email = db.Column(db.String(200), nullable=True)
    # Leistungsdatum (optional; bei manuellen Rechnungen verpflichtend)
    service_date = db.Column(db.Date, nullable=True)
    # Ueberschrift fuer manuelle Positionsbloecke / Verwendungszweck
    manual_title = db.Column(
        db.String(120),
        nullable=False,
        default="Manuelle Positionen",
        server_default="Manuelle Positionen",
    )

    id = db.Column(db.Integer, primary_key=True)

    # Fortlaufende Rechnungsnummer (unabhängig von DB-id, wird beim Finalisieren vergeben)
    seq_number = db.Column(db.Integer, nullable=True, unique=True, index=True)


    # Zu welcher Person gehört die Rechnung?
    person_id = db.Column(
        db.Integer,
        db.ForeignKey("person.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    person = db.relationship(
        "Person",
        back_populates="invoices",
        passive_deletes=False
    )

    # ---------------------------------------------------------
    # Zeitpunkt der Rechnungserstellung (Lokalzeit Berlin)
    # ---------------------------------------------------------
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: now_berlin().replace(tzinfo=None),
    )

    # ---------------------------------------------------------
    # Zeitpunkt der Bezahlung (optional, Lokalzeit Berlin)
    # ---------------------------------------------------------
    paid_at = db.Column(db.DateTime, nullable=True)

    # Zahlungsart (nur relevant, wenn is_paid = True)
    # Mögliche Werte: "cash" | "card" | "transfer" | "wero"
    payment_method = db.Column(db.String(20), nullable=True)

    # Teilzahlung über Vorkasse / Gutschein (Bruttoanteil)
    prepaid_voucher_amount = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0,
        server_default="0"
    )

    # Gesamtsumme (wird automatisch berechnet)
    total_amount = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0,
        server_default="0"
    )

    # Wurde die Rechnung bezahlt?
    is_paid = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default="0",
        index=True
    )

    # Soft-Delete (Storno)
    is_deleted = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default="0",
        index=True
    )

    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_reason = db.Column(db.String(255), nullable=True)
    deleted_by = db.Column(db.String(100), nullable=True)

    # Beziehung zu den einzelnen Rechnungsposten
    items = db.relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # ---------------------------------------------------------
    # Status der Rechnung
    # ---------------------------------------------------------
    # - 'draft' = erzeugt & prüfbar, aber noch nicht gespeichert
    # - 'final' = bewusst gespeichert, offiziell
    stage = db.Column(
        db.String(10),
        nullable=False,
        default="draft",
        server_default="draft",
        index=True
    )

    # ---------------------------------------------------------
    # E-Mail Versand Audit Trail
    # ---------------------------------------------------------
    email_last_attempt_at = db.Column(db.DateTime, nullable=True)
    email_last_error = db.Column(db.String(500), nullable=True)
    email_last_recipient = db.Column(db.String(255), nullable=True)
    email_last_message_id = db.Column(db.String(255), nullable=True)
    email_sent_at = db.Column(db.DateTime, nullable=True)
    email_sent_ok = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default="0"
    )
    email_delivery_confirmed_at = db.Column(db.DateTime, nullable=True)
    email_delivery_confirmed_by = db.Column(db.String(100), nullable=True)

    # Cached PDF bytes for faster email sending
    pdf_bytes = db.Column(db.LargeBinary, nullable=True)

    # ---------------------------------------------------------
    # Methoden
    # ---------------------------------------------------------

    def calculate_total(self) -> None:
        """
        Berechnet die Gesamtsumme zuverlässig aus der DB (Snapshot),
        damit nachträgliche Änderungen (z.B. Transaktionskosten) immer
        in total_amount landen – unabhängig davon, ob self.items bereits
        geladen/alt ist.
        """
        # Wenn die Rechnung noch keine ID hat (noch nicht gespeichert),
        # fällt auf in-memory zurück.
        if not self.id:
            self.total_amount = sum((item.amount or 0) for item in self.items)
            return

        # Pending Deletes/Adds in dieser Session in die DB flushen,
        # damit die Summenabfrage den aktuellen Stand sieht.
        try:
            db.session.flush()
        except Exception:
            # Flush kann in seltenen Fällen fehlschlagen
            pass

        total = (
            db.session.query(db.func.coalesce(db.func.sum(InvoiceItem.amount), 0))
            .filter(InvoiceItem.invoice_id == self.id)
            .scalar()
        )

        self.total_amount = total if total is not None else Decimal("0.00")

    def mark_paid(self) -> None:
        """Markiert die Rechnung als bezahlt (Zahlungsart wird extern gesetzt)."""
        self.is_paid = True
        self.paid_at = now_berlin().replace(tzinfo=None)

    @property
    def prepaid_voucher_amount_decimal(self) -> Decimal:
        return Decimal(str(self.prepaid_voucher_amount or 0))

    @property
    def onsite_amount_decimal(self) -> Decimal:
        total = Decimal(str(self.total_amount or 0))
        prepaid = self.prepaid_voucher_amount_decimal
        rest = total - prepaid
        return rest if rest > Decimal("0.00") else Decimal("0.00")

    def __repr__(self) -> str:
        return (
            f"<Invoice id={self.id} "
            f"person={self.person_id} "
            f"total={self.total_amount}>"
        )
