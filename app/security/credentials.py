from __future__ import annotations

import json
import os
import secrets
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="pbkdf2:sha256:260000")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return check_password_hash(password_hash, password)
    except Exception:
        return False


def random_secret_key() -> str:
    return secrets.token_urlsafe(48)


def load_json_file(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def get_project_root_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def get_runtime_home_dir() -> str:
    runtime_home = os.environ.get("MANIFEST_RUNTIME_HOME", "").strip()
    if runtime_home:
        return os.path.abspath(runtime_home)
    return get_project_root_dir()


def is_dev_mode() -> bool:
    return os.environ.get("MANIFEST_ENV", "").strip().lower() == "dev"


def get_program_data_dir() -> str:
    return get_runtime_home_dir()


def get_default_secrets_path() -> str:
    secrets_path = os.environ.get("MANIFEST_SECRETS_PATH", "").strip()
    if secrets_path:
        return os.path.abspath(secrets_path)
    return os.path.join(get_runtime_home_dir(), "secrets", "auth_config.json")
