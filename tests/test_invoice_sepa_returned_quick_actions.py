from __future__ import annotations

import os

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

        person = Person(
            first_name="Test",
            last_name="User",
            phone="123",
            email="test@example.org",
            weight_kg=80,
            sepa_enabled=True,
            iban="DE89370400440532013000",
            account_holder="Test User",
            sepa_mandate_date="2024-01-01",
        )
        db.session.add(person)
        db.session.flush()

        invoice = Invoice(
            person_id=person.id,
            stage="final",
            total_amount=100,
            payment_method="sepa",
            payment_state="paid",
            is_paid=True,
        )
        db.session.add(invoice)
        db.session.commit()

    yield app

    with app.app_context():
        db.session.remove()


def test_db_admin_can_mark_paid_sepa_invoice_as_returned(app_with_db):
    from app import db
    from app.models.invoice import Invoice

    app = app_with_db
    with app.app_context():
        invoice = db.session.query(Invoice).first()

    with app.test_client() as client:
        with client.session_transaction() as session:
            session["is_db_admin"] = True

        response = client.post(
            f"/billing/invoice/{invoice.id}/mark_sepa_returned",
            follow_redirects=True,
        )

        assert response.status_code == 200

        with app.app_context():
            refreshed = db.session.get(Invoice, invoice.id)
            assert refreshed.payment_state == "sepa_returned"
            assert refreshed.payment_method == "sepa"


def test_db_admin_can_restore_returned_sepa_invoice_to_pending(app_with_db):
    from app import db
    from app.models.invoice import Invoice

    app = app_with_db
    with app.app_context():
        invoice = db.session.query(Invoice).first()
        invoice.payment_state = "sepa_returned"
        invoice.payment_method = "sepa"
        invoice.is_paid = False
        db.session.commit()

    with app.test_client() as client:
        with client.session_transaction() as session:
            session["is_db_admin"] = True

        response = client.post(
            f"/billing/invoice/{invoice.id}/mark_sepa_pending",
            follow_redirects=True,
        )

        assert response.status_code == 200

        with app.app_context():
            refreshed = db.session.get(Invoice, invoice.id)
            assert refreshed.payment_state == "sepa_pending"
            assert refreshed.payment_method == "sepa"
