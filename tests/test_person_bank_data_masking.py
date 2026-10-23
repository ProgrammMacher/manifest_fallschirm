from __future__ import annotations

import pytest

from app.routes.person import mask_bank_value

IBAN = "DE12345678901234567890"
BIC = "ABCDEFGH123"
HOLDER = "Erika Kontoinhaberin"


# ---------------------------------------------------------
# Filter / Hilfsfunktion
# ---------------------------------------------------------
def test_mask_iban_shows_first_two_and_last_three():
    assert mask_bank_value(IBAN) == "DE-----890"


def test_mask_bic_shows_first_two_and_last_three():
    assert mask_bank_value(BIC) == "AB-----123"


def test_mask_ignores_whitespace_in_value():
    assert mask_bank_value("DE12 3456 7890 1234 5678 90") == "DE-----890"


@pytest.mark.parametrize("empty", [None, "", "   "])
def test_mask_empty_value_returns_dash(empty):
    assert mask_bank_value(empty) == "–"


def test_mask_short_value_is_fully_masked():
    assert mask_bank_value("ABCDE") == "-----"


# ---------------------------------------------------------
# Routen
# ---------------------------------------------------------
@pytest.fixture()
def app_with_person(tmp_path, monkeypatch):
    runtime_home = tmp_path / "runtime"
    runtime_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("MANIFEST_RUNTIME_HOME", str(runtime_home))
    monkeypatch.setenv("MANIFEST_DB_PATH", str(runtime_home / "manifest_test.db"))
    monkeypatch.setenv("MANIFEST_ENV", "dev")
    monkeypatch.setenv("MANIFEST_AUTO_CREATE_DB", "1")

    import app.helpers.db_migrations as db_migrations
    from app import create_app, db
    from app.models.person import Person

    monkeypatch.setattr(db_migrations, "run_startup_migrations", lambda: None)

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        person = Person(
            first_name="Max",
            last_name="Mustermann",
            phone="0123456789",
            weight_kg=80,
            iban=IBAN,
            bic=BIC,
            account_holder=HOLDER,
        )
        db.session.add(person)
        db.session.commit()
        app.config["TEST_PERSON_ID"] = person.id

    yield app

    with app.app_context():
        db.session.remove()


def _detail_html(app, as_admin: bool) -> str:
    person_id = app.config["TEST_PERSON_ID"]
    with app.test_client() as client:
        if as_admin:
            with client.session_transaction() as sess:
                sess["is_admin"] = True
        response = client.get(f"/persons/detail/{person_id}")
        assert response.status_code == 200
        return response.get_data(as_text=True)


def test_detail_non_admin_sees_masked_bank_data(app_with_person):
    html = _detail_html(app_with_person, as_admin=False)

    assert "DE-----890" in html
    assert "AB-----123" in html
    assert "Nicht sichtbar" in html
    assert IBAN not in html
    assert BIC not in html
    assert HOLDER not in html


def test_detail_admin_sees_full_bank_data(app_with_person):
    html = _detail_html(app_with_person, as_admin=True)

    assert IBAN in html
    assert BIC in html
    assert HOLDER in html
    assert "Nicht sichtbar" not in html


def test_excel_export_requires_admin(app_with_person):
    with app_with_person.test_client() as client:
        response = client.get("/export/persons/excel", follow_redirects=False)

    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_excel_export_available_for_admin(app_with_person):
    with app_with_person.test_client() as client:
        with client.session_transaction() as sess:
            sess["is_admin"] = True
        response = client.get("/export/persons/excel", follow_redirects=False)

    assert response.status_code == 200
    assert "spreadsheetml" in response.headers["Content-Type"]


def test_person_list_hides_export_button_for_non_admin(app_with_person):
    with app_with_person.test_client() as client:
        html = client.get("/persons/").get_data(as_text=True)

    assert "/export/persons/excel" not in html


def test_person_list_shows_export_button_for_admin(app_with_person):
    with app_with_person.test_client() as client:
        with client.session_transaction() as sess:
            sess["is_admin"] = True
        html = client.get("/persons/").get_data(as_text=True)

    assert "/export/persons/excel" in html
