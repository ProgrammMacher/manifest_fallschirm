from __future__ import annotations

import pytest


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    runtime_home = tmp_path / "runtime"
    runtime_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("MANIFEST_RUNTIME_HOME", str(runtime_home))
    monkeypatch.delenv("MANIFEST_DB_PATH", raising=False)
    monkeypatch.setenv("MANIFEST_ENV", "dev")

    from app import create_app

    app = create_app()
    app.config.update(
        TESTING=True,
        ADMIN_PASSWORD_HASH="",
        DB_ADMIN_PASSWORD_HASH="",
        ADMIN_PASSWORD="admin-test-pw",
        DB_ADMIN_PASSWORD="dbadmin-test-pw",
    )
    return app.test_client()


def _flashes(client):
    with client.session_transaction() as sess:
        return list(sess.get("_flashes", []))


def _after_login_target(client):
    with client.session_transaction() as sess:
        return sess.get("after_login_redirect")


def _assert_login_redirect(response):
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


# ---------------------------------------------------------
# Admin-geschützte UI (Voll-Admin)
# ---------------------------------------------------------
@pytest.mark.parametrize(
    "path",
    [
        "/pricing/",
        "/aircraft/new",
        "/flugplatz/new",
        "/billing/admin/config",
        "/billing/invoices/cancelled",
    ],
)
def test_admin_ui_without_admin_redirects_to_login_with_hint(app_client, path):
    response = app_client.get(path, follow_redirects=False)

    _assert_login_redirect(response)
    assert any("Admin-Modus" in message for _cat, message in _flashes(app_client))
    assert _after_login_target(app_client) == path


def test_admin_ui_as_db_admin_is_still_denied_with_specific_hint(app_client):
    with app_client.session_transaction() as sess:
        sess["is_db_admin"] = True

    response = app_client.get("/aircraft/new", follow_redirects=False)

    _assert_login_redirect(response)
    messages = [message for _cat, message in _flashes(app_client)]
    assert any("Datenbank-Admin angemeldet" in message for message in messages)


def test_admin_post_without_admin_is_denied_and_returns_to_origin_page(app_client):
    response = app_client.post(
        "/aircraft/1/hard_delete",
        headers={"Referer": "http://localhost/aircraft/"},
        follow_redirects=False,
    )

    _assert_login_redirect(response)
    assert _after_login_target(app_client) == "/aircraft/"


def test_admin_post_never_remembers_post_only_path_as_return_target(app_client):
    response = app_client.post("/aircraft/1/hard_delete", follow_redirects=False)

    _assert_login_redirect(response)
    assert _after_login_target(app_client) != "/aircraft/1/hard_delete"


def test_external_referer_is_not_used_as_return_target(app_client):
    response = app_client.post(
        "/aircraft/1/hard_delete",
        headers={"Referer": "http://evil.example/phishing"},
        follow_redirects=False,
    )

    _assert_login_redirect(response)
    target = _after_login_target(app_client)
    assert not target or target.startswith("/")
    assert "evil.example" not in (target or "")


def test_ajax_request_without_admin_gets_no_return_target(app_client):
    response = app_client.post(
        "/billing/invoice/1/transaction_fee",
        headers={"X-Requested-With": "XMLHttpRequest"},
        follow_redirects=False,
    )

    assert response.status_code in (302, 403)
    assert _after_login_target(app_client) is None


def test_flugplatz_edit_save_without_admin_explains_and_redirects(app_client):
    response = app_client.post("/flugplatz/1/edit", data={"name": "X"}, follow_redirects=False)

    _assert_login_redirect(response)
    assert any("Admin-Modus" in message for _cat, message in _flashes(app_client))


# ---------------------------------------------------------
# DB-Admin-/Admin-oder-DB-Admin-geschützte UI
# ---------------------------------------------------------
@pytest.mark.parametrize(
    "path",
    [
        "/admin/database/",
        "/admin/database/export",
        "/email/history",
        "/email/config",
    ],
)
def test_db_admin_ui_without_rights_redirects_to_login_with_hint(app_client, path):
    response = app_client.get(path, follow_redirects=False)

    _assert_login_redirect(response)
    assert any("Datenbank-Admin-Rechte" in message for _cat, message in _flashes(app_client))
    assert _after_login_target(app_client) == path


def test_sepa_action_without_rights_redirects_to_login_with_hint(app_client):
    response = app_client.post(
        "/billing/invoice/1/mark_sepa_returned",
        headers={"Referer": "http://localhost/billing/invoice/1"},
        follow_redirects=False,
    )

    _assert_login_redirect(response)
    assert any("Datenbank-Admin-Rechte" in message for _cat, message in _flashes(app_client))
    assert _after_login_target(app_client) == "/billing/invoice/1"


def test_person_newsletter_reset_without_rights_redirects_to_login_with_hint(app_client):
    response = app_client.post("/persons/reset_newsletter_optout/1", follow_redirects=False)

    _assert_login_redirect(response)
    assert any("Datenbank-Admin-Rechte" in message for _cat, message in _flashes(app_client))


# ---------------------------------------------------------
# Authentifizierung und Rückkehr
# ---------------------------------------------------------
def test_admin_login_returns_to_original_target(app_client):
    app_client.get("/pricing/", follow_redirects=False)

    response = app_client.post(
        "/admin/login", data={"password": "admin-test-pw"}, follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/pricing/")
    assert _after_login_target(app_client) is None

    allowed = app_client.get("/pricing/", follow_redirects=False)
    assert allowed.status_code == 200


def test_db_admin_login_returns_to_database_page_and_gets_access(app_client):
    app_client.get("/admin/database/", follow_redirects=False)

    response = app_client.post(
        "/admin/login", data={"password": "dbadmin-test-pw"}, follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/database/")

    allowed = app_client.get("/admin/database/", follow_redirects=False)
    assert allowed.status_code == 200


def test_wrong_password_keeps_return_target_for_next_attempt(app_client):
    app_client.get("/pricing/", follow_redirects=False)

    wrong = app_client.post(
        "/admin/login", data={"password": "falsch"}, follow_redirects=False
    )
    assert wrong.status_code == 200
    assert _after_login_target(app_client) == "/pricing/"

    ok = app_client.post(
        "/admin/login", data={"password": "admin-test-pw"}, follow_redirects=False
    )
    assert ok.headers["Location"].endswith("/pricing/")


# ---------------------------------------------------------
# Keine Lockerung der Berechtigungen
# ---------------------------------------------------------
def test_db_admin_session_does_not_unlock_full_admin_functions(app_client):
    with app_client.session_transaction() as sess:
        sess["is_db_admin"] = True

    for path in ("/pricing/", "/aircraft/new", "/billing/admin/config"):
        response = app_client.get(path, follow_redirects=False)
        _assert_login_redirect(response)


def test_full_admin_session_still_has_access(app_client):
    with app_client.session_transaction() as sess:
        sess["is_admin"] = True

    for path in ("/pricing/", "/aircraft/new", "/flugplatz/new", "/admin/database/"):
        response = app_client.get(path, follow_redirects=False)
        assert response.status_code == 200, path


def test_public_functions_remain_accessible_without_login(app_client):
    for path in ("/flugplatz/", "/aircraft/"):
        response = app_client.get(path, follow_redirects=False)
        assert response.status_code == 200, path

