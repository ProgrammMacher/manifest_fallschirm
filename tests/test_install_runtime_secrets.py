from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.license import install_runtime_secrets as secrets_cli


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _fake_validate_ok(license_key, machine_fingerprint=""):
    return True, "Lizenz gueltig", {"hwfp": machine_fingerprint or "a" * 64, "exp": None}


def test_mismatched_admin_passwords_are_rejected(capsys):
    rc = secrets_cli.main(
        [
            "--license-key", "dummy",
            "--admin-password", "AdminSecret1",
            "--admin-password-confirm", "AdminSecretDifferent",
            "--db-admin-password", "DbSecret1",
            "--db-admin-password-confirm", "DbSecret1",
            "--secrets-path", "unused",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 7
    assert "stimmen nicht ueberein" in captured.err
    assert "AdminSecret1" not in captured.out
    assert "AdminSecret1" not in captured.err
    assert "AdminSecretDifferent" not in captured.out
    assert "AdminSecretDifferent" not in captured.err


def test_mismatched_db_admin_passwords_are_rejected(capsys):
    rc = secrets_cli.main(
        [
            "--license-key", "dummy",
            "--admin-password", "AdminSecret1",
            "--admin-password-confirm", "AdminSecret1",
            "--db-admin-password", "DbSecret1",
            "--db-admin-password-confirm", "DbSecretDifferent",
            "--secrets-path", "unused",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 9
    assert "DB-Admin-Passwort" in captured.err
    assert "DbSecret1" not in captured.out
    assert "DbSecret1" not in captured.err
    assert "DbSecretDifferent" not in captured.out
    assert "DbSecretDifferent" not in captured.err


@pytest.mark.parametrize(
    "missing_field",
    ["admin-password-confirm", "db-admin-password-confirm"],
)
def test_empty_confirmation_fields_are_rejected(capsys, missing_field):
    args = [
        "--license-key", "dummy",
        "--admin-password", "AdminSecret1",
        "--admin-password-confirm", "AdminSecret1",
        "--db-admin-password", "DbSecret1",
        "--db-admin-password-confirm", "DbSecret1",
        "--secrets-path", "unused",
    ]
    flag_index = args.index(f"--{missing_field}")
    args[flag_index + 1] = ""

    rc = secrets_cli.main(args)
    captured = capsys.readouterr()
    assert rc in (6, 8)
    assert "darf nicht leer sein" in captured.err
    assert "AdminSecret1" not in captured.out and "AdminSecret1" not in captured.err
    assert "DbSecret1" not in captured.out and "DbSecret1" not in captured.err


def test_matching_passwords_pass_validation_and_reach_license_check(capsys):
    # Passwords match, so the script must get past password validation and only
    # fail on the (intentionally bogus) license key -- proving match was accepted.
    rc = secrets_cli.main(
        [
            "--license-key", "not-a-real-license",
            "--admin-password", "AdminSecret1",
            "--admin-password-confirm", "AdminSecret1",
            "--db-admin-password", "DbSecret1",
            "--db-admin-password-confirm", "DbSecret1",
            "--secrets-path", "unused",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 4
    assert "Lizenz ungueltig" in captured.err
    assert "AdminSecret1" not in captured.out and "AdminSecret1" not in captured.err
    assert "DbSecret1" not in captured.out and "DbSecret1" not in captured.err


def test_matching_passwords_and_valid_license_write_secrets(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(secrets_cli, "validate_license_key", _fake_validate_ok)
    monkeypatch.setattr(
        secrets_cli, "get_machine_fingerprint", lambda: "a" * 64
    )
    target = tmp_path / "secrets" / "auth_config.json"

    rc = secrets_cli.main(
        [
            "--license-key", "MFS2.anything.anything",
            "--admin-password", "AdminSecret1",
            "--admin-password-confirm", "AdminSecret1",
            "--db-admin-password", "DbSecret1",
            "--db-admin-password-confirm", "DbSecret1",
            "--secrets-path", str(target),
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert target.is_file()

    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["admin_password_hash"] != "AdminSecret1"
    assert data["db_admin_password_hash"] != "DbSecret1"
    assert "AdminSecret1" not in captured.out and "AdminSecret1" not in captured.err
    assert "DbSecret1" not in captured.out and "DbSecret1" not in captured.err
    assert "AdminSecret1" not in target.read_text(encoding="utf-8")
    assert "DbSecret1" not in target.read_text(encoding="utf-8")


def test_secrets_can_be_supplied_via_environment_instead_of_cli(tmp_path, monkeypatch, capsys):
    """Secrets passed through env vars (Inno [Code] uses this) must not require
    plaintext command-line arguments, reducing exposure via process listings."""
    monkeypatch.setattr(secrets_cli, "validate_license_key", _fake_validate_ok)
    monkeypatch.setattr(secrets_cli, "get_machine_fingerprint", lambda: "a" * 64)
    monkeypatch.setenv(secrets_cli.ENV_LICENSE_KEY, "MFS2.anything.anything")
    monkeypatch.setenv(secrets_cli.ENV_ADMIN_PASSWORD, "AdminSecret1")
    monkeypatch.setenv(secrets_cli.ENV_ADMIN_PASSWORD_CONFIRM, "AdminSecret1")
    monkeypatch.setenv(secrets_cli.ENV_DB_ADMIN_PASSWORD, "DbSecret1")
    monkeypatch.setenv(secrets_cli.ENV_DB_ADMIN_PASSWORD_CONFIRM, "DbSecret1")

    target = tmp_path / "secrets" / "auth_config.json"
    rc = secrets_cli.main(["--secrets-path", str(target)])
    captured = capsys.readouterr()

    assert rc == 0
    assert target.is_file()
    assert "AdminSecret1" not in captured.out and "AdminSecret1" not in captured.err
