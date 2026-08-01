from __future__ import annotations

import os

import pytest

from app.routes.person import _collect_and_validate


@pytest.fixture()
def app_with_person_db(tmp_path):
    runtime_home = tmp_path / "runtime"
    db_file = runtime_home / "manifest_test.db"
    runtime_home.mkdir(parents=True, exist_ok=True)

    os.environ["MANIFEST_RUNTIME_HOME"] = str(runtime_home)
    os.environ["MANIFEST_DB_PATH"] = str(db_file)
    os.environ["MANIFEST_ENV"] = "dev"
    os.environ["MANIFEST_AUTO_CREATE_DB"] = "1"

    import app.helpers.db_migrations as db_migrations
    from app import create_app, db

    db_migrations.run_startup_migrations = lambda: None

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()


def _base_form(**overrides):
    form = {
        "first_name": "Max",
        "last_name": "Mustermann",
        "phone": "0123456789",
        "weight_kg": "80",
        "email": "",
        "iban": "",
        "bic": "",
        "account_holder": "",
        "sepa_enabled": "false",
        "sepa_mandate_reference": "",
        "sepa_mandate_date": "",
        "sepa_first_collection_done": "false",
        "street_and_number": "",
        "zip_code": "",
        "city": "",
        "license_number": "",
        "insurance_provider": "",
        "insurance_number": "",
        "comment": "",
        "notes": "",
        "birthdate": "",
        "emergency_name": "",
        "emergency_relation": "",
        "emergency_phone": "",
        "emergency_email": "",
        "is_member": "false",
        "is_partner_verein": "false",
        "is_tandem_guest": "false",
        "is_tandemmaster": "false",
        "is_tandem_kleinunternehmer": "false",
        "is_student": "false",
        "is_video": "false",
        "is_video_kleinunternehmer": "false",
        "is_aff_teacher": "false",
        "is_aff_student": "false",
        "is_teacher": "false",
        "teacher_license_expires": "",
        "liability_waiver_given": "false",
        "liability_waiver_date": "",
    }
    form.update(overrides)
    return form


def test_invalid_iban_is_rejected_with_clear_message():
    form = _base_form(iban="DE8937040044053201300X")

    data, field_errors, _ = _collect_and_validate(form)

    assert field_errors["iban"] == "Die eingegebene IBAN ist ungültig."
    assert data["iban"] == "DE8937040044053201300X"


def test_valid_iban_is_normalized_and_accepted():
    form = _base_form(iban="de 8937 0400 4405 3201 3000")

    data, field_errors, _ = _collect_and_validate(form)

    assert field_errors.get("iban") is None
    assert data["iban"] == "DE89370400440532013000"


def test_invalid_form_renders_error_summary_banner(app_with_person_db):
    app = app_with_person_db

    with app.test_client() as client:
        response = client.post(
            "/persons/new",
            data={
                "first_name": "",
                "last_name": "",
                "phone": "1",
                "weight_kg": "invalid",
                "iban": "DE8937040044053201300X",
            },
            follow_redirects=False,
        )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Das Formular enthält Fehler. Bitte prüfen Sie die markierten Felder." in html
    assert 'id="form-error-summary"' in html
    assert "scrollIntoView" in html
    assert "focus" in html
