from __future__ import annotations

import os

import pytest


@pytest.fixture()
def fresh_app(tmp_path, monkeypatch):
    """Simulates a brand-new customer install: empty runtime home, no
    pre-existing database, production-like env (MANIFEST_ENV production)."""
    runtime_home = tmp_path / "runtime"
    runtime_home.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("MANIFEST_RUNTIME_HOME", str(runtime_home))
    monkeypatch.delenv("MANIFEST_DB_PATH", raising=False)
    monkeypatch.setenv("MANIFEST_ENV", "production")
    monkeypatch.setenv("MANIFEST_ADMIN_PASSWORD_HASH", "x")
    monkeypatch.setenv("MANIFEST_DB_ADMIN_PASSWORD_HASH", "x")
    monkeypatch.setenv("MANIFEST_SECRET_KEY", "test-secret")

    from app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    return app


def test_fresh_install_seeds_airfields_and_aircraft(fresh_app):
    from app.models.aircraft import Aircraft
    from app.models.flugplatz import Flugplatz
    from app.models.billing_config import BillingPrice, BillingPricePeriod

    with fresh_app.app_context():
        assert BillingPricePeriod.query.count() > 0
        assert BillingPrice.query.count() > 0
        assert Flugplatz.query.count() > 0
        assert Aircraft.query.count() > 0


def test_new_flugplatz_form_renders_without_buildrror(fresh_app):
    """Regression test for a real production 500: the 'new' form rendered the
    archive/restore/hard-delete admin actions block even for a brand-new,
    not-yet-saved Flugplatz (id=None), causing url_for(...) BuildError."""
    with fresh_app.test_client() as client:
        with client.session_transaction() as sess:
            sess["is_admin"] = True

        response = client.get("/flugplatz/new")
        assert response.status_code == 200

        body = response.get_data(as_text=True)
        assert "flugplatz.delete_flugplatz" not in body
        assert "flugplatz.hard_delete" not in body
        assert "flugplatz.restore" not in body


def test_new_flugplatz_post_creates_record(fresh_app):
    with fresh_app.test_client() as client:
        with client.session_transaction() as sess:
            sess["is_admin"] = True

        response = client.post(
            "/flugplatz/new", data={"name": "Test Flugplatz"}, follow_redirects=True
        )
        assert response.status_code == 200

    from app.models.flugplatz import Flugplatz

    with fresh_app.app_context():
        assert Flugplatz.query.filter_by(name="Test Flugplatz").first() is not None


def test_admin_database_index_reachable_on_fresh_install(fresh_app):
    with fresh_app.test_client() as client:
        with client.session_transaction() as sess:
            sess["is_admin"] = True

        response = client.get("/admin/database/")
        assert response.status_code == 200
