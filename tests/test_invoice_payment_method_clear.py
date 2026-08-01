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
