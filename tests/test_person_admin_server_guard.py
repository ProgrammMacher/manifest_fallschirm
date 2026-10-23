from __future__ import annotations

import pytest


@pytest.fixture()
def app_ctx(tmp_path, monkeypatch):
    runtime_home = tmp_path / "runtime"
    runtime_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("MANIFEST_RUNTIME_HOME", str(runtime_home))
    monkeypatch.delenv("MANIFEST_DB_PATH", raising=False)
    monkeypatch.setenv("MANIFEST_ENV", "dev")

    from app import create_app, db
    from app.models.person import Person

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        active = Person(
            first_name="Erika", last_name="Aktiv", phone="0123456789", weight_kg=70
        )
        archived = Person(
            first_name="Anna", last_name="Archiv", phone="0123456780", weight_kg=65
        )
        db.session.add_all([active, archived])
        db.session.commit()
        archived.archive(reason="test")
        db.session.commit()
        ids = {"active": active.id, "archived": archived.id}

    return app, ids


def _client(app, admin=False, db_admin=False):
    client = app.test_client()
    if admin or db_admin:
        with client.session_transaction() as sess:
            if admin:
                sess["is_admin"] = True
            if db_admin:
                sess["is_db_admin"] = True
    return client


def _assert_login_redirect(response, path):
    assert response.status_code == 302, path
    assert "/admin/login" in response.headers["Location"], path


def _person(app, person_id):
    from app.models.person import Person

    with app.app_context():
        return Person.query.get(person_id)


# ---------------------------------------------------------
# Ohne Admin: Redirect zum Login, keine Aenderung
# ---------------------------------------------------------
def test_edit_person_requires_admin(app_ctx):
    app, ids = app_ctx
    path = f"/persons/edit/{ids['active']}"
    client = _client(app)

    _assert_login_redirect(client.get(path), path)
    _assert_login_redirect(
        client.post(path, data={"first_name": "Hacker", "last_name": "Name"}), path
    )
    assert _person(app, ids["active"]).first_name == "Erika"


def test_archive_person_requires_admin(app_ctx):
    app, ids = app_ctx
    path = f"/persons/archive/{ids['active']}"

    _assert_login_redirect(_client(app).post(path), path)
    assert _person(app, ids["active"]).deleted_at is None


def test_legacy_delete_person_requires_admin(app_ctx):
    app, ids = app_ctx
    path = f"/persons/delete/{ids['active']}"

    _assert_login_redirect(_client(app).post(path), path)
    assert _person(app, ids["active"]).deleted_at is None


def test_restore_person_requires_admin(app_ctx):
    app, ids = app_ctx
    path = f"/persons/restore/{ids['archived']}"

    _assert_login_redirect(_client(app).post(path), path)
    assert _person(app, ids["archived"]).deleted_at is not None


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/import/"),
        ("get", "/import/vorlage"),
        ("get", "/import/preview"),
        ("post", "/import/preview"),
        ("post", "/import/execute"),
        ("get", "/export/persons/import-template"),
        # Personenexport enthaelt Kontodaten (IBAN/BIC/Kontoinhaber) -> nur Admin
        ("get", "/export/persons/excel"),
    ],
)
def test_import_routes_require_admin(app_ctx, method, path):
    app, _ = app_ctx
    _assert_login_redirect(getattr(_client(app), method)(path), path)


def test_import_execute_without_admin_creates_no_person(app_ctx):
    app, _ = app_ctx
    from app.models.person import Person

    with app.app_context():
        before = Person.query.count()

    _client(app).post("/import/execute")

    with app.app_context():
        assert Person.query.count() == before


# ---------------------------------------------------------
# Datenbank-Admin allein reicht nicht (wie bei hard_delete)
# ---------------------------------------------------------
def test_db_admin_alone_is_not_enough(app_ctx):
    app, ids = app_ctx
    client = _client(app, db_admin=True)

    for method, path in (
        ("post", f"/persons/archive/{ids['active']}"),
        ("post", f"/persons/restore/{ids['archived']}"),
        ("get", f"/persons/edit/{ids['active']}"),
        ("get", "/import/"),
    ):
        _assert_login_redirect(getattr(client, method)(path), path)

    assert _person(app, ids["active"]).deleted_at is None
    assert _person(app, ids["archived"]).deleted_at is not None


# ---------------------------------------------------------
# Mit Admin: Funktionen arbeiten unveraendert
# ---------------------------------------------------------
def test_admin_can_open_edit_form_and_import_pages(app_ctx):
    app, ids = app_ctx
    client = _client(app, admin=True)

    assert client.get(f"/persons/edit/{ids['active']}").status_code == 200
    assert client.get("/import/").status_code == 200
    assert client.get("/import/vorlage").status_code == 200
    assert client.get("/export/persons/import-template").status_code == 200
    assert client.get("/export/persons/excel").status_code == 200


def test_admin_can_archive_and_restore(app_ctx):
    app, ids = app_ctx
    client = _client(app, admin=True)

    response = client.post(f"/persons/archive/{ids['active']}")
    assert response.status_code == 302
    assert "/admin/login" not in response.headers["Location"]
    assert _person(app, ids["active"]).deleted_at is not None

    response = client.post(f"/persons/restore/{ids['active']}")
    assert response.status_code == 302
    assert "/admin/login" not in response.headers["Location"]
    assert _person(app, ids["active"]).deleted_at is None


# ---------------------------------------------------------
# Nicht-administrative Personenfunktionen bleiben offen
# ---------------------------------------------------------
@pytest.mark.parametrize(
    "path",
    ["/persons/", "/persons/new", "/persons/mobile-intake"],
)
def test_general_person_functions_remain_open(app_ctx, path):
    app, _ = app_ctx
    assert _client(app).get(path).status_code == 200, path


def test_person_detail_remains_open(app_ctx):
    app, ids = app_ctx
    assert _client(app).get(f"/persons/detail/{ids['active']}").status_code == 200

