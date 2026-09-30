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


def main() -> int:
    parser = argparse.ArgumentParser(description="Schreibt Runtime-Secrets fuer Installation")
    parser.add_argument("--license-key", required=True)
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--db-admin-password", required=True)
    parser.add_argument("--secrets-path", default="")
    args = parser.parse_args()

    if not args.admin_password.strip():
        print("Admin-Passwort darf nicht leer sein.", file=sys.stderr)
        return 2
    if not args.db_admin_password.strip():
        print("DB-Admin-Passwort darf nicht leer sein.", file=sys.stderr)
        return 3

    machine_fingerprint = get_machine_fingerprint()
    ok, msg, payload = validate_license_key(
        args.license_key,
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
        "license_key": args.license_key,
        "license_exp": payload.get("exp") if payload else None,
        "license_hwfp": payload.get("hwfp") if payload else None,
        "machine_fingerprint": machine_fingerprint,
        "admin_password_hash": hash_password(args.admin_password),
        "db_admin_password_hash": hash_password(args.db_admin_password),
        "secret_key": token_urlsafe(48),
        "runtime_state_key": token_urlsafe(48),
    }

    with target_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Secrets geschrieben: {target_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
