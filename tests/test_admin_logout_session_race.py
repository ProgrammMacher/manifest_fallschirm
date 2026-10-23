from __future__ import annotations

import pytest
from flask import Response, session


@pytest.fixture()
def app(tmp_path, monkeypatch):
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
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, password):
    response = client.post(
        "/admin/login", data={"password": password}, follow_redirects=False
    )
    assert response.status_code == 302
    return response


def _stored_session(app, client):
    """Liest die tatsaechlich gespeicherte Server-Session (Filesystem)."""
    sid = client.get_cookie("session").value
    interface = app.session_interface
    return interface.cache.get(interface.key_prefix + sid) or {}


def _logout_while_runtime_request_is_in_flight(app, client, path, role_key):
    """
    Bildet die Race Condition nach:
    1. Ein Runtime-Request (sendBeacon/Heartbeat) laedt die Admin-Session.
    2. Waehrenddessen laeuft der Logout komplett durch.
    3. Der Runtime-Request endet und speichert seinen alten Session-Stand.
    """
    sid = client.get_cookie("session").value
    ctx = app.test_request_context(
        path, method="POST", headers={"Cookie": f"session={sid}"}
    )
    ctx.push()
    try:
        app.preprocess_request()
        assert session.get(role_key) is True  # alter Stand im Speicher

        logout = client.post("/admin/logout", follow_redirects=False)
        assert logout.status_code == 302

        app.process_response(Response("", 204))
    finally:
        ctx.pop()


# ---------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------
def test_session_is_not_refreshed_on_every_request(app):
    assert app.config["SESSION_REFRESH_EACH_REQUEST"] is False


# ---------------------------------------------------------
# Logout funktioniert nach einem Klick
# ---------------------------------------------------------
def test_admin_logout_works_with_single_click(app, client):
    _login(client, "admin-test-pw")
    assert _stored_session(app, client).get("is_admin") is True

    response = client.post("/admin/logout", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/pwa/")
    stored = _stored_session(app, client)
    assert not stored.get("is_admin")
    assert not stored.get("is_db_admin")

    page = client.get("/pwa/")
    assert page.status_code == 200
    assert "adminModeBanner" not in page.get_data(as_text=True)
    assert client.get("/pricing/", follow_redirects=False).status_code == 302


def test_db_admin_logout_works_with_single_click(app, client):
    _login(client, "dbadmin-test-pw")
    assert client.get("/admin/database/", follow_redirects=False).status_code == 200

    client.post("/admin/logout", follow_redirects=False)

    stored = _stored_session(app, client)
    assert not stored.get("is_admin")
    assert not stored.get("is_db_admin")
    assert client.get("/admin/database/", follow_redirects=False).status_code == 302


def test_admin_logout_via_get_still_supported(app, client):
    _login(client, "admin-test-pw")

    response = client.get("/admin/logout", follow_redirects=False)

    assert response.status_code == 302
    assert not _stored_session(app, client).get("is_admin")


# ---------------------------------------------------------
# Runtime-Requests duerfen die Session nicht wiederherstellen
# ---------------------------------------------------------
RUNTIME_PATHS = ["/pwa/runtime/disconnect", "/pwa/runtime/heartbeat"]


@pytest.mark.parametrize("path", RUNTIME_PATHS)
def test_runtime_request_does_not_restore_admin_session_after_logout(
    app, client, path
):
    _login(client, "admin-test-pw")

    _logout_while_runtime_request_is_in_flight(app, client, path, "is_admin")

    stored = _stored_session(app, client)
    assert not stored.get("is_admin")
    assert not stored.get("is_db_admin")
    page = client.get("/pwa/")
    assert "adminModeBanner" not in page.get_data(as_text=True)


@pytest.mark.parametrize("path", RUNTIME_PATHS)
def test_runtime_request_does_not_restore_db_admin_session_after_logout(
    app, client, path
):
    _login(client, "dbadmin-test-pw")

    _logout_while_runtime_request_is_in_flight(app, client, path, "is_db_admin")

    assert not _stored_session(app, client).get("is_db_admin")
    assert client.get("/admin/database/", follow_redirects=False).status_code == 302


@pytest.mark.parametrize("path", RUNTIME_PATHS)
def test_runtime_requests_do_not_write_session_or_cookie(app, client, path):
    _login(client, "admin-test-pw")
    before = _stored_session(app, client)

    response = client.post(path)

    assert response.status_code == 204
    assert response.headers.getlist("Set-Cookie") == []
    assert _stored_session(app, client) == before


# ---------------------------------------------------------
# remember_last_page
# ---------------------------------------------------------
def test_last_page_is_not_overwritten_by_loads_api_requests(app, client):
    client.get("/aircraft/")
    assert _stored_session(app, client).get("last_page") == "/aircraft/"

    client.get("/loads/api/status/list")

    assert _stored_session(app, client).get("last_page") == "/aircraft/"


def test_last_page_is_only_written_when_value_changes(app, client):
    first = client.get("/aircraft/")
    assert first.status_code == 200
    assert first.headers.getlist("Set-Cookie") != []

    second = client.get("/aircraft/")

    assert second.status_code == 200
    assert second.headers.getlist("Set-Cookie") == []
    assert _stored_session(app, client).get("last_page") == "/aircraft/"


def test_last_page_still_follows_content_pages(app, client):
    client.get("/aircraft/")
    client.get("/flugplatz/")

    assert _stored_session(app, client).get("last_page") == "/flugplatz/"


# ---------------------------------------------------------
# Login bleibt unveraendert funktionsfaehig
# ---------------------------------------------------------
def test_admin_session_survives_normal_requests_and_heartbeat(app, client):
    _login(client, "admin-test-pw")

    client.get("/aircraft/")
    client.post("/pwa/runtime/heartbeat")

    assert _stored_session(app, client).get("is_admin") is True
    assert client.get("/pricing/", follow_redirects=False).status_code == 200

