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
    app.config.update(TESTING=True)
    return app.test_client()


def test_pricing_without_admin_redirects_to_login_with_hint(app_client):
    """Regression: anonymous /pricing/ access used to silently redirect to
    /loads (and from there to the split view) without any visible hint."""
    response = app_client.get("/pricing/", follow_redirects=False)
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]

    with app_client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
    assert any("Admin-Modus" in message for _category, message in flashes)
