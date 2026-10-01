from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from secrets import token_urlsafe

from werkzeug.security import generate_password_hash

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.security.hardware_fingerprint import get_machine_fingerprint
from app.security.license import validate_license_key

# Env var names used as a less-visible alternative to CLI arguments for secrets
# (CLI arguments are visible to other local admins via process listings).
ENV_LICENSE_KEY = "MANIFEST_INSTALL_LICENSE_KEY"
ENV_ADMIN_PASSWORD = "MANIFEST_INSTALL_ADMIN_PASSWORD"
ENV_ADMIN_PASSWORD_CONFIRM = "MANIFEST_INSTALL_ADMIN_PASSWORD_CONFIRM"
ENV_DB_ADMIN_PASSWORD = "MANIFEST_INSTALL_DB_ADMIN_PASSWORD"
ENV_DB_ADMIN_PASSWORD_CONFIRM = "MANIFEST_INSTALL_DB_ADMIN_PASSWORD_CONFIRM"


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="pbkdf2:sha256:260000")


def get_default_secrets_path() -> str:
    configured_path = os.environ.get("MANIFEST_SECRETS_PATH", "").strip()
    if configured_path:
        return os.path.abspath(configured_path)
    runtime_home = os.environ.get("MANIFEST_RUNTIME_HOME", "").strip()
    if runtime_home:
        return os.path.join(os.path.abspath(runtime_home), "secrets", "auth_config.json")
    return os.path.join(PROJECT_ROOT, "data", "secrets", "auth_config.json")


def _resolve_secret(cli_value: str | None, env_name: str) -> str:
    """CLI argument wins if given; otherwise read from environment (not echoed anywhere)."""
    if cli_value is not None:
        return cli_value
    return os.environ.get(env_name, "")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Schreibt Runtime-Secrets fuer Installation")
    parser.add_argument("--license-key", default=None)
    parser.add_argument("--admin-password", default=None)
    parser.add_argument("--admin-password-confirm", default=None)
    parser.add_argument("--db-admin-password", default=None)
    parser.add_argument("--db-admin-password-confirm", default=None)
    parser.add_argument("--secrets-path", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    license_key = _resolve_secret(args.license_key, ENV_LICENSE_KEY)
    admin_password = _resolve_secret(args.admin_password, ENV_ADMIN_PASSWORD)
    admin_password_confirm = _resolve_secret(args.admin_password_confirm, ENV_ADMIN_PASSWORD_CONFIRM)
    db_admin_password = _resolve_secret(args.db_admin_password, ENV_DB_ADMIN_PASSWORD)
    db_admin_password_confirm = _resolve_secret(
        args.db_admin_password_confirm, ENV_DB_ADMIN_PASSWORD_CONFIRM
    )

    if not license_key.strip():
        print("Lizenzschluessel darf nicht leer sein.", file=sys.stderr)
        return 1

    if not admin_password.strip():
        print("Admin-Passwort darf nicht leer sein.", file=sys.stderr)
        return 2
    if not admin_password_confirm.strip():
        print("Admin-Passwort-Wiederholung darf nicht leer sein.", file=sys.stderr)
        return 6
    if admin_password != admin_password_confirm:
        print(
            "Die beiden Eingaben fuer das Admin-Passwort stimmen nicht ueberein.",
            file=sys.stderr,
        )
        return 7

    if not db_admin_password.strip():
        print("DB-Admin-Passwort darf nicht leer sein.", file=sys.stderr)
        return 3
    if not db_admin_password_confirm.strip():
        print("DB-Admin-Passwort-Wiederholung darf nicht leer sein.", file=sys.stderr)
        return 8
    if db_admin_password != db_admin_password_confirm:
        print(
            "Die beiden Eingaben fuer das DB-Admin-Passwort stimmen nicht ueberein.",
            file=sys.stderr,
        )
        return 9

    machine_fingerprint = get_machine_fingerprint()
    ok, msg, payload = validate_license_key(
        license_key,
        machine_fingerprint=machine_fingerprint,
    )
    if not ok:
        print(f"Lizenz ungueltig: {msg}", file=sys.stderr)
        return 4

    if not payload or not str(payload.get("hwfp", "")).strip():
        print("Lizenz ungueltig: Maschinenbindung (hwfp) fehlt.", file=sys.stderr)
        return 5

    target = args.secrets_path.strip() or get_default_secrets_path()
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "license_key": license_key,
        "license_exp": payload.get("exp") if payload else None,
        "license_hwfp": payload.get("hwfp") if payload else None,
        "machine_fingerprint": machine_fingerprint,
        "admin_password_hash": hash_password(admin_password),
        "db_admin_password_hash": hash_password(db_admin_password),
        "secret_key": token_urlsafe(48),
        "runtime_state_key": token_urlsafe(48),
    }

    with target_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Secrets geschrieben: {target_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
