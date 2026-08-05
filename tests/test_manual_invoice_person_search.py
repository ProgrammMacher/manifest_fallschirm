import os

import pytest


@pytest.fixture()
def app_with_temp_db(tmp_path):
    runtime_home = tmp_path / "runtime"
    db_file = runtime_home / "manifest_test.db"
    runtime_home.mkdir(parents=True, exist_ok=True)

    os.environ["MANIFEST_RUNTIME_HOME"] = str(runtime_home)
    os.environ["MANIFEST_DB_PATH"] = str(db_file)
    os.environ["MANIFEST_ENV"] = "dev"
    os.environ["MANIFEST_AUTO_CREATE_DB"] = "1"

    from app import create_app, db

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()


def test_loads_person_search_includes_email_for_manual_invoice_selector(app_with_temp_db):
    from app import db
    from app.models.person import Person

    app = app_with_temp_db

    with app.app_context():
        person = Person(
            first_name="Fallschirmsportverein",
            last_name="Zerbst",
            phone="01784200060",
            email="fsvzerbst@aol.com",
            weight_kg=80,
        )
        db.session.add(person)
        db.session.commit()
        person_id = person.id

    client = app.test_client()
    response = client.get("/loads/api/person/search?q=FSV")

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, list)
    assert any((row.get("id") == person_id) for row in payload)


def test_loads_person_search_returns_address_fields_for_billing_copy(app_with_temp_db):
    from app import db
    from app.models.person import Person

    app = app_with_temp_db

    with app.app_context():
        person = Person(
            first_name="Copy",
            last_name="Target",
            phone="0123456789",
            email="copy.target@example.org",
            street_and_number="Musterstraße 1",
            zip_code="06844",
            city="Dessau",
            weight_kg=75,
        )
        db.session.add(person)
        db.session.commit()
        person_id = person.id

    client = app.test_client()
    response = client.get("/loads/api/person/search?q=Copy")

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, list)

    match = next((row for row in payload if row.get("id") == person_id), None)
    assert match is not None
    assert match.get("name") == "Copy Target"
    assert match.get("email") == "copy.target@example.org"
    assert match.get("street_and_number") == "Musterstraße 1"
    assert match.get("zip_code") == "06844"
    assert match.get("city") == "Dessau"
