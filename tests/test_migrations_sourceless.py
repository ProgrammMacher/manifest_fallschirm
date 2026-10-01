from __future__ import annotations

import os
import py_compile
import shutil

import pytest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REAL_MIGRATIONS_DIR = os.path.join(PROJECT_ROOT, "migrations")


def _make_app(tmp_path, name: str):
    runtime_home = tmp_path / name
    runtime_home.mkdir(parents=True, exist_ok=True)
    os.environ["MANIFEST_RUNTIME_HOME"] = str(runtime_home)
    os.environ["MANIFEST_DB_PATH"] = str(runtime_home / "manifest.db")
    os.environ["MANIFEST_ENV"] = "dev"

    from app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    return app


def _compile_only_copy(tmp_path):
    """Mirrors tools/build_offline_compiled_installer_zip.ps1: compile every
    .py to a sibling .pyc, then delete the .py (what the real installer ships)."""
    dest = tmp_path / "migrations_compiled"
    shutil.copytree(
        REAL_MIGRATIONS_DIR, dest, ignore=shutil.ignore_patterns("__pycache__")
    )
    for root, _dirs, files in os.walk(dest):
        for filename in files:
            if filename.endswith(".py"):
                py_path = os.path.join(root, filename)
                py_compile.compile(py_path, cfile=py_path + "c", doraise=True)
                os.remove(py_path)
    return dest


def test_alembic_ini_declares_sourceless():
    """Regression guard for Fehler 4: without this, Alembic silently ignores
    every compiled-only (.pyc) migration file, since it only matches *.py
    unless 'sourceless' is enabled."""
    ini_text = (
        open(os.path.join(REAL_MIGRATIONS_DIR, "alembic.ini"), encoding="utf-8").read()
    )
    assert "sourceless = true" in ini_text


def test_app_init_catches_systemexit_from_failed_upgrade():
    """flask_migrate's upgrade()/stamp() wrap alembic errors with sys.exit(1)
    (SystemExit, not an Exception subclass). Catching only Exception silently
    kills the whole app on any upgrade failure instead of degrading gracefully."""
    init_text = open(
        os.path.join(PROJECT_ROOT, "app", "__init__.py"), encoding="utf-8"
    ).read()
    assert "except BaseException as e:" in init_text
    assert "Alembic-Startup-Upgrade fehlgeschlagen" in init_text


def test_compiled_only_migrations_are_discoverable_by_alembic(tmp_path):
    """Core regression test for Fehler 4: simulate the exact real installer
    packaging (migrations shipped as bare .pyc, .py removed) and verify the
    full revision chain -- including 20260504_add_fuel_required_to_load --
    upgrades a fresh database to heads without 'Can't locate revision'."""
    compiled_dir = _compile_only_copy(tmp_path)
    # Sanity: packaging really produced a sourceless copy (no .py left).
    assert not any(f.endswith(".py") for _r, _d, fs in os.walk(compiled_dir) for f in fs)
    assert any(
        f == "XXXXXXXXXXXX_add_fuel_required_to_load.pyc"
        for _r, _d, fs in os.walk(compiled_dir / "versions")
        for f in fs
    )

    app = _make_app(tmp_path, "fresh_compiled")
    with app.app_context():
        from flask_migrate import Migrate, upgrade
        from app import db

        if "migrate" not in app.extensions:
            Migrate(app, db)

        # Must not raise (previously: CommandError -> sys.exit(1)).
        upgrade(directory=str(compiled_dir), revision="heads")

        row = db.session.execute(db.text("SELECT version_num FROM alembic_version")).fetchone()
        assert row is not None
        assert row[0]


def test_existing_db_second_start_upgrades_cleanly(tmp_path):
    """'zweiter Produktionsstart nach DB-Uebernahme': a DB already stamped at
    the historical revision from the real-world bug report must upgrade to
    heads via the compiled-only migrations without error."""
    compiled_dir = _compile_only_copy(tmp_path)
    app = _make_app(tmp_path, "existing_db")

    with app.app_context():
        from flask_migrate import Migrate, upgrade, stamp
        from app import db

        if "migrate" not in app.extensions:
            Migrate(app, db)

        db.create_all()
        stamp(directory=str(compiled_dir), revision="20260504_add_fuel_required_to_load")

        # Must not raise and must not require dropping/recreating the DB.
        upgrade(directory=str(compiled_dir), revision="heads")

        row = db.session.execute(db.text("SELECT version_num FROM alembic_version")).fetchone()
        assert row is not None
        assert row[0] != "20260504_add_fuel_required_to_load"
