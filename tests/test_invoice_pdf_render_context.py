from datetime import date
from decimal import Decimal

import pytest


@pytest.fixture()
def app_with_temp_invoice_db(tmp_path, monkeypatch):
    runtime_home = tmp_path / "runtime"
    runtime_home.mkdir(parents=True, exist_ok=True)
    db_file = runtime_home / "manifest_test.db"

    monkeypatch.setenv("MANIFEST_RUNTIME_HOME", str(runtime_home))
    monkeypatch.setenv("MANIFEST_DB_PATH", str(db_file))
    monkeypatch.setenv("MANIFEST_SECRETS_PATH", str(runtime_home / "secrets" / "auth_config.json"))
    monkeypatch.setenv("MANIFEST_ENV", "dev")
    monkeypatch.setenv("MANIFEST_AUTO_DB_UPGRADE", "0")
    monkeypatch.setenv("MANIFEST_AUTO_CREATE_DB", "1")

    from app import create_app, db
    from app.models.billing_config import BillingConfig
    from app.models.invoice import Invoice
    from app.models.person import Person

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        person = Person(
            first_name="Test",
            last_name="PDF",
            phone="0123456789",
            weight_kg=80,
            sepa_enabled=True,
            iban="DE89370400440532013000",
            account_holder="Test PDF",
            sepa_mandate_date=date(2026, 9, 30),
        )
        cfg = BillingConfig(
            company_name="Test GmbH",
            street="Teststraße 1",
            zip_code="12345",
            city="Teststadt",
        )
        db.session.add_all([person, cfg])
        db.session.flush()

        invoice = Invoice(
            person_id=person.id,
            stage="final",
            seq_number=1,
            payment_state="sepa_pending",
            payment_method="sepa",
            total_amount=Decimal("100.00"),
        )
        db.session.add(invoice)
        db.session.commit()
        invoice_id = invoice.id

    yield app, invoice_id

    with app.app_context():
        db.session.remove()
        db.engine.dispose(close=True)


def test_render_invoice_pdf_uses_serializable_payment_state_context(app_with_temp_invoice_db):
    from flask import template_rendered

    from app import db
    from app.models.billing_config import BillingConfig
    from app.models.invoice import Invoice
    from app.services.billing_service import BillingService

    app, invoice_id = app_with_temp_invoice_db
    rendered_context = {}

    def capture_template_context(sender, template, context, **extra):
        if template.name == "billing/invoice_detail.html":
            rendered_context.update(context)

    template_rendered.connect(capture_template_context, app)
    try:
        with app.test_request_context(f"/billing/invoice/{invoice_id}"):
            invoice = db.session.get(Invoice, invoice_id)
            cfg = BillingConfig.query.one()
            assert invoice is not None

            pdf_bytes = BillingService.render_invoice_pdf(
                invoice,
                billing_config=cfg,
                epc_qr_data_uri=None,
                invoice_purpose="Test",
            )
    finally:
        template_rendered.disconnect(capture_template_context, app)

    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert len(pdf_bytes) > 0
    assert rendered_context["invoice_payment_state_code"] == "sepa_pending"
    assert isinstance(rendered_context["invoice_payment_state_label"], str)
    assert callable(rendered_context["invoice_split_payment_label"])
    assert rendered_context["invoice_split_payment_label"](invoice) == "SEPA-Lastschrift"
