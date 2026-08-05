from __future__ import annotations

import os
from datetime import date
from types import SimpleNamespace

import pytest


@pytest.fixture()
def app_with_db(tmp_path):
    runtime_home = tmp_path / "runtime"
    db_file = runtime_home / "manifest_test.db"
    runtime_home.mkdir(parents=True, exist_ok=True)

    os.environ["MANIFEST_RUNTIME_HOME"] = str(runtime_home)
    os.environ["MANIFEST_DB_PATH"] = str(db_file)
    os.environ["MANIFEST_ENV"] = "dev"
    os.environ["MANIFEST_AUTO_CREATE_DB"] = "1"

    from app import create_app, db
    from app.models.invoice import Invoice
    from app.models.person import Person

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()

        person = Person(first_name="Test", last_name="User", phone="123", email="test@example.org", weight_kg=80)
        db.session.add(person)
        db.session.flush()

        invoice = Invoice(person_id=person.id, stage="final", total_amount=100, payment_method="cash")
        db.session.add(invoice)
        db.session.commit()

    yield app

    with app.app_context():
        db.session.remove()


def test_admin_set_payment_method_none_clears_value(app_with_db):
    from app import db
    from app.models.invoice import Invoice

    app = app_with_db
    with app.test_client() as client:
        with app.app_context():
            invoice = db.session.query(Invoice).first()
            assert invoice.payment_method == "cash"

        response = client.post(
            f"/billing/invoice/{invoice.id}/set_payment_method",
            data={"payment_method": ""},
            follow_redirects=True,
        )

        assert response.status_code == 200

        with app.app_context():
            refreshed = db.session.get(Invoice, invoice.id)
            assert refreshed.payment_method is None


def test_set_payment_method_rejects_sepa_with_deviating_billing_recipient(app_with_db):
    from app import db
    from app.models.invoice import Invoice
    from app.models.person import Person

    app = app_with_db
    with app.app_context():
        person = db.session.query(Person).first()
        person.sepa_enabled = True
        person.iban = "DE02120300000000202051"
        person.account_holder = "Test User"
        person.sepa_mandate_date = date(2026, 1, 1)

        invoice = db.session.query(Invoice).first()
        invoice.payment_method = None
        invoice.payment_state = "open"
        invoice.billing_address_name = "Fallschirmsportverein Zerbst"
        db.session.commit()
        invoice_id = invoice.id

    with app.test_client() as client:
        response = client.post(
            f"/billing/invoice/{invoice_id}/set_payment_method",
            data={"payment_method": "sepa"},
            follow_redirects=True,
        )

    assert response.status_code == 200

    with app.app_context():
        refreshed = db.session.get(Invoice, invoice_id)
        assert refreshed is not None
        assert refreshed.payment_method is None
        assert (refreshed.payment_state or "").strip().lower() == "open"


def test_invoice_allows_sepa_false_with_deviating_billing_recipient_snapshot():
    from app.services.invoice_state_service import _invoice_allows_sepa

    person = SimpleNamespace(
        is_tandem_guest=False,
        sepa_enabled=True,
        iban="DE02120300000000202051",
        account_holder="Test User",
        sepa_mandate_date=date(2026, 1, 1),
    )
    invoice = SimpleNamespace(
        person=person,
        billing_address_name="Abweichender Empfaenger",
        billing_address_street="",
        billing_address_zip="",
        billing_address_city="",
        billing_address_email="",
        items=[],
    )

    assert _invoice_allows_sepa(invoice) is False
