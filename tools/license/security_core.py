from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import platform
import secrets
import subprocess
from typing import Any, Iterable

from werkzeug.security import generate_password_hash


LICENSE_ALGO = "MFS1"


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="pbkdf2:sha256:260000")


def random_secret_key() -> str:
    return secrets.token_urlsafe(48)


def _safe_part(value: str | None) -> str:
    return (value or "").strip().lower()


def _sha256_hex(parts: Iterable[str]) -> str:
    joined = "|".join(parts).encode("utf-8", errors="ignore")
    return hashlib.sha256(joined).hexdigest()


def _get_windows_machine_guid() -> str:
    if os.name != "nt":
        return ""
    try:
        import winreg  # type: ignore

        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
        value, _ = winreg.QueryValueEx(key, "MachineGuid")
        return str(value)
    except Exception:
        return ""


def _get_volume_serial() -> str:
    if os.name != "nt":
        return ""

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        volume_name = ctypes.create_unicode_buffer(261)
        fs_name = ctypes.create_unicode_buffer(261)
        serial_number = ctypes.c_uint32(0)
        max_component = ctypes.c_uint32(0)
        file_system_flags = ctypes.c_uint32(0)

        root = os.environ.get("SystemDrive", "C:") + "\\"
        ok = kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root),
            volume_name,
            ctypes.sizeof(volume_name),
            ctypes.byref(serial_number),
            ctypes.byref(max_component),
            ctypes.byref(file_system_flags),
            fs_name,
            ctypes.sizeof(fs_name),
        )
        if ok:
            return f"{serial_number.value:08X}"
    except Exception:
        pass
    return ""


def _get_cpu_identifier() -> str:
    cpu_env = _safe_part(os.environ.get("PROCESSOR_IDENTIFIER"))
    if cpu_env:
        return cpu_env

    if os.name != "nt":
        return _safe_part(platform.processor())

    try:
        output = subprocess.check_output(
            ["wmic", "cpu", "get", "ProcessorId"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        )
        lines = [ln.strip() for ln in output.splitlines() if ln.strip() and "ProcessorId" not in ln]
        if lines:
            return lines[0]
    except Exception:
        pass
    return ""


def get_machine_fingerprint() -> str:
    parts = [
        _safe_part(_get_windows_machine_guid()),
        _safe_part(_get_volume_serial()),
        _safe_part(_get_cpu_identifier()),
    ]

    if not any(parts):
        parts = [
            _safe_part(platform.node()),
            _safe_part(platform.platform()),
            _safe_part(platform.machine()),
        ]

    return _sha256_hex(parts)


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _sign_payload(payload_b64: str, signing_secret: str) -> str:
    return hmac.new(
        signing_secret.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def parse_license_key(license_key: str) -> dict[str, Any]:
    parts = license_key.strip().split(".")
    if len(parts) != 3:
        raise ValueError("Lizenzschluessel-Format ungueltig")
    algo, payload_b64, signature = parts
    if algo != LICENSE_ALGO:
        raise ValueError("Lizenzschluessel-Algorithmus ungueltig")
    try:
        payload_raw = _b64url_decode(payload_b64)
        payload = json.loads(payload_raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError("Lizenz-Payload unlesbar") from exc
    if not isinstance(payload, dict):
        raise ValueError("Lizenz-Payload ungueltig")
    return {
        "algo": algo,
        "payload_b64": payload_b64,
        "signature": signature,
        "payload": payload,
    }


def validate_license_key(
    license_key: str,
    signing_secret: str,
    machine_fingerprint: str = "",
    now_utc: dt.datetime | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    if now_utc is None:
        now_utc = dt.datetime.now(dt.timezone.utc)

    try:
        parsed = parse_license_key(license_key)
    except ValueError as exc:
        return False, str(exc), None

    expected_sig = _sign_payload(parsed["payload_b64"], signing_secret)
    if not hmac.compare_digest(expected_sig, parsed["signature"]):
        return False, "Lizenz-Signatur ungueltig", None

    payload = parsed["payload"]

    nbf_raw = str(payload.get("nbf", "")).strip()
    if nbf_raw:
        try:
            nbf_dt = dt.datetime.fromisoformat(nbf_raw)
        except ValueError:
            return False, "Startdatum im Lizenzschluessel ungueltig", None

        if nbf_dt.tzinfo is None:
            nbf_dt = nbf_dt.replace(tzinfo=dt.timezone.utc)
        else:
            nbf_dt = nbf_dt.astimezone(dt.timezone.utc)

        if now_utc < nbf_dt:
            return False, "Lizenz noch nicht gueltig (Startdatum)", payload

    exp_raw = str(payload.get("exp", "")).strip()
    if exp_raw:
        try:
            exp_dt = dt.datetime.fromisoformat(exp_raw)
        except ValueError:
            return False, "Ablaufdatum im Lizenzschluessel ungueltig", None

        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=dt.timezone.utc)
        else:
            exp_dt = exp_dt.astimezone(dt.timezone.utc)

        if exp_dt < now_utc:
            return False, "Lizenz abgelaufen", payload

    expected_hwfp = str(payload.get("hwfp", "")).strip().lower()
    if expected_hwfp:
        current_hwfp = machine_fingerprint.strip().lower()
        if not current_hwfp:
            return False, "Maschinenbindung aktiv, aber kein aktueller Fingerprint verfuegbar", payload
        if current_hwfp != expected_hwfp:
            return False, "Lizenz ist an eine andere Maschine gebunden", payload

    return True, "Lizenz gueltig", payload


def generate_license_key(payload: dict[str, Any], signing_secret: str) -> str:
    payload_raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    payload_b64 = _b64url_encode(payload_raw)
    signature = _sign_payload(payload_b64, signing_secret)
    return f"{LICENSE_ALGO}.{payload_b64}.{signature}"


def get_signing_secret() -> str:
    return os.environ.get(
        "MANIFEST_LICENSE_SIGNING_SECRET",
        "manifest-ou-license-secret-change-me",
    )


def get_default_secrets_path() -> str:
    secrets_path = os.environ.get("MANIFEST_SECRETS_PATH", "").strip()
    if secrets_path:
        return os.path.abspath(secrets_path)

    runtime_home = os.environ.get("MANIFEST_RUNTIME_HOME", "").strip()
    if runtime_home:
        return os.path.join(os.path.abspath(runtime_home), "secrets", "auth_config.json")

    script_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(script_root, "data", "secrets", "auth_config.json")