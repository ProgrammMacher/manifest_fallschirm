from __future__ import annotations

import re

import pytest

HINT = "Nur Ansicht – keine Änderungen möglich. Bitte als Administrator anmelden."
PAGES = ["/aircraft/", "/flugplatz/", "/flugplatz/archiv", "/persons/"]


@pytest.fixture()
def app_ctx(tmp_path, monkeypatch):
    runtime_home = tmp_path / "runtime"
    runtime_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("MANIFEST_RUNTIME_HOME", str(runtime_home))
    monkeypatch.delenv("MANIFEST_DB_PATH", raising=False)
    monkeypatch.setenv("MANIFEST_ENV", "dev")

    from app import create_app, db
    from app.models.aircraft import Aircraft
    from app.models.flugplatz import Flugplatz
    from app.models.person import Person

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        person = Person(
            first_name="Erika",
            last_name="Musterfrau",
            phone="0123456789",
            weight_kg=70,
        )
        db.session.add(person)
        db.session.commit()
        ids = {
            "person": person.id,
            "aircraft": Aircraft.query.first().id,
            "flugplatz": Flugplatz.query.first().id,
        }

    return app, ids


def _disabled_count(body):
    """Anzahl gerenderter <button>/<a> mit disabled-Attribut.

    Das Layout (base.html) enthaelt einen eigenen, deaktivierten Dialog-Button;
    deshalb wird nur verglichen, ob die Seite fuer Nicht-Admins MEHR
    deaktivierte Elemente enthaelt als fuer Admins.
    """
    return len(re.findall(r"<(?:button|a)\b[^>]*\bdisabled\b", body))


def _assert_no_disabled_placeholders(app, path, body):
    assert _disabled_count(body) <= _disabled_count(_get(app, path, admin=True)), path


def _get(app, path, admin=False):
    with app.test_client() as client:
        if admin:
            with client.session_transaction() as sess:
                sess["is_admin"] = True
        response = client.get(path)
        assert response.status_code == 200, path
        return response.get_data(as_text=True)


# ---------------------------------------------------------
# Hinweis: einheitlicher Text, nur ohne Admin
# ---------------------------------------------------------
@pytest.mark.parametrize("path", PAGES)
def test_view_only_hint_shown_without_admin(app_ctx, path):
    app, _ = app_ctx
    assert HINT in _get(app, path)


@pytest.mark.parametrize("path", PAGES)
def test_view_only_hint_hidden_for_admin(app_ctx, path):
    app, _ = app_ctx
    assert HINT not in _get(app, path, admin=True)


def test_view_only_hint_on_person_detail_and_flugplatz_edit(app_ctx):
    app, ids = app_ctx
    person_path = f"/persons/detail/{ids['person']}"
    edit_path = f"/flugplatz/{ids['flugplatz']}/edit"

    assert HINT in _get(app, person_path)
    assert HINT not in _get(app, person_path, admin=True)
    assert HINT in _get(app, edit_path)
    assert HINT not in _get(app, edit_path, admin=True)


# ---------------------------------------------------------
# Flugzeuge
# ---------------------------------------------------------
def test_aircraft_admin_actions_hidden_without_admin(app_ctx):
    app, ids = app_ctx
    body = _get(app, "/aircraft/")

    assert "/aircraft/new" not in body
    assert f"/aircraft/{ids['aircraft']}/edit" not in body
    assert f"/aircraft/{ids['aircraft']}/archive" not in body
    assert "/restore" not in body
    assert "/hard_delete" not in body
    _assert_no_disabled_placeholders(app, "/aircraft/", body)


def test_aircraft_admin_actions_visible_for_admin(app_ctx):
    app, ids = app_ctx
    body = _get(app, "/aircraft/", admin=True)

    assert "/aircraft/new" in body
    assert f"/aircraft/{ids['aircraft']}/edit" in body
    assert f"/aircraft/{ids['aircraft']}/archive" in body


# ---------------------------------------------------------
# Flugplaetze (Referenz)
# ---------------------------------------------------------
def test_flugplatz_admin_actions_hidden_without_admin(app_ctx):
    app, _ = app_ctx
    body = _get(app, "/flugplatz/")

    assert "/flugplatz/new" not in body
    assert "btn-outline-warning" not in body
    _assert_no_disabled_placeholders(app, "/flugplatz/", body)


def test_flugplatz_admin_actions_visible_for_admin(app_ctx):
    app, _ = app_ctx
    body = _get(app, "/flugplatz/", admin=True)

    assert "/flugplatz/new" in body
    assert "/flugplatz/archiv" in body


# ---------------------------------------------------------
# Personen
# ---------------------------------------------------------
def test_person_list_admin_actions_hidden_without_admin(app_ctx):
    app, ids = app_ctx
    pid = ids["person"]
    body = _get(app, "/persons/")

    assert "Musterfrau" in body
    assert f"/persons/edit/{pid}" not in body
    assert f"/persons/archive/{pid}" not in body
    assert "/persons/restore/" not in body
    assert "/persons/hard_delete/" not in body
    assert "/import/" not in body
    assert "Vertikal-Import direkt" not in body
    assert f"/persons/detail/{pid}" in body
    _assert_no_disabled_placeholders(app, "/persons/", body)


def test_person_list_general_actions_visible_without_admin(app_ctx):
    app, _ = app_ctx
    body = _get(app, "/persons/")

    assert "/persons/new" in body
    assert "/persons/mobile-intake" in body
    assert "/export/persons/excel" in body


def test_person_list_all_actions_visible_for_admin(app_ctx):
    app, ids = app_ctx
    pid = ids["person"]
    body = _get(app, "/persons/", admin=True)

    assert "/persons/new" in body
    assert "/persons/mobile-intake" in body
    assert "/export/persons/excel" in body
    assert "/import/" in body
    assert "Vertikal-Import direkt" in body
    assert f"/persons/edit/{pid}" in body
    assert f"/persons/archive/{pid}" in body


def test_person_detail_admin_actions_hidden_without_admin(app_ctx):
    app, ids = app_ctx
    pid = ids["person"]
    body = _get(app, f"/persons/detail/{pid}")

    assert "Erika Musterfrau" in body
    assert f"/persons/edit/{pid}" not in body
    assert f"/persons/archive/{pid}" not in body
    assert f"/persons/restore/{pid}" not in body
    assert f"/persons/hard_delete/{pid}" not in body
    _assert_no_disabled_placeholders(app, f"/persons/detail/{pid}", body)


def test_person_detail_admin_actions_visible_for_admin(app_ctx):
    app, ids = app_ctx
    pid = ids["person"]
    body = _get(app, f"/persons/detail/{pid}", admin=True)

    assert f"/persons/edit/{pid}" in body
    assert f"/persons/archive/{pid}" in body


# ---------------------------------------------------------
# Sicherheit unveraendert: bestehende Schutzmechanismen
# ---------------------------------------------------------
def test_existing_admin_guards_still_redirect_to_login(app_ctx):
    app, ids = app_ctx
    with app.test_client() as client:
        for method, path in (
            ("get", "/aircraft/new"),
            ("post", f"/aircraft/{ids['aircraft']}/archive"),
            ("post", f"/persons/hard_delete/{ids['person']}"),
            ("get", "/flugplatz/new"),
        ):
            response = getattr(client, method)(path, follow_redirects=False)
            assert response.status_code == 302, path
            assert "/admin/login" in response.headers["Location"], path

