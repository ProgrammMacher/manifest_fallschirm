from __future__ import annotations

import base64
import ctypes
import json
import os
import subprocess
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


LICENSE_ALGORITHM = "MFS2"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_KEY_PATH = PROJECT_ROOT / "app" / "security" / "license_public_key.pem"
PRIVATE_KEY_RELATIVE_PATH = Path("ManifestFallschirm") / "developer-signing" / "license_ed25519_private.dpapi"


def get_private_key_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA ist nicht gesetzt; privater Schlüssel kann nicht sicher gespeichert werden.")
    return Path(local_app_data) / PRIVATE_KEY_RELATIVE_PATH


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _make_blob(data: bytes):
    buffer = (ctypes.c_byte * len(data)).from_buffer_copy(data)
    blob = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    return blob, buffer


def _dpapi_transform(data: bytes, *, protect: bool) -> bytes:
    if os.name != "nt":
        raise RuntimeError("Der Entwicklerschlüssel kann nur unter Windows mit DPAPI verwendet werden.")

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    source, _source_buffer = _make_blob(data)
    target = _DataBlob()
    flags = 0x1  # CRYPTPROTECT_UI_FORBIDDEN; default scope is current Windows user.

    if protect:
        operation = crypt32.CryptProtectData
        operation.argtypes = [
            ctypes.POINTER(_DataBlob), wintypes.LPCWSTR, ctypes.POINTER(_DataBlob),
            wintypes.LPVOID, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(_DataBlob),
        ]
        operation.restype = wintypes.BOOL
        succeeded = operation(ctypes.byref(source), "Manifest Fallschirm license signing key", None, None, None, flags, ctypes.byref(target))
    else:
        operation = crypt32.CryptUnprotectData
        operation.argtypes = [
            ctypes.POINTER(_DataBlob), ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(_DataBlob),
            wintypes.LPVOID, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(_DataBlob),
        ]
        operation.restype = wintypes.BOOL
        description = wintypes.LPWSTR()
        succeeded = operation(ctypes.byref(source), ctypes.byref(description), None, None, None, flags, ctypes.byref(target))
        if description:
            kernel32.LocalFree(ctypes.cast(description, ctypes.c_void_p))

    if not succeeded:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel32.LocalFree(target.pbData)


def _restrict_directory_to_current_user(directory: Path) -> None:
    current_user = subprocess.check_output(["whoami"], text=True, stderr=subprocess.DEVNULL).strip()
    subprocess.run(
        [
            "icacls", str(directory), "/inheritance:r",
            "/grant:r", f"{current_user}:(OI)(CI)F",
            "/grant:r", "*S-1-5-18:(OI)(CI)F",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _public_bytes(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def initialize_signing_key() -> str:
    """Create the one-time DPAPI user-bound private key and its public verifier."""
    private_path = get_private_key_path()
    private_path.parent.mkdir(parents=True, exist_ok=True)
    _restrict_directory_to_current_user(private_path.parent)

    if private_path.exists():
        current_user = subprocess.check_output(["whoami"], text=True, stderr=subprocess.DEVNULL).strip()
        subprocess.run(
            [
                "icacls", str(private_path), "/inheritance:r",
                "/grant:r", f"{current_user}:F",
                "/grant:r", "*S-1-5-18:F",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        private_key = Ed25519PrivateKey.from_private_bytes(_dpapi_transform(private_path.read_bytes(), protect=False))
        public_bytes = _public_bytes(private_key)
        if PUBLIC_KEY_PATH.exists() and PUBLIC_KEY_PATH.read_bytes() != public_bytes:
            raise RuntimeError("Öffentlicher Schlüssel passt nicht zum lokalen privaten Schlüssel; nichts wurde überschrieben.")
        if not PUBLIC_KEY_PATH.exists():
            PUBLIC_KEY_PATH.write_bytes(public_bytes)
        return str(private_path)

    if PUBLIC_KEY_PATH.exists():
        raise RuntimeError("Öffentlicher Schlüssel existiert bereits, lokaler privater Schlüssel fehlt. Kein Schlüssel wurde ersetzt.")

    private_key = Ed25519PrivateKey.generate()
    private_raw = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    protected_private = _dpapi_transform(private_raw, protect=True)
    PUBLIC_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        with private_path.open("xb") as private_file:
            private_file.write(protected_private)
        with PUBLIC_KEY_PATH.open("xb") as public_file:
            public_file.write(_public_bytes(private_key))
    except Exception:
        if private_path.exists() and not PUBLIC_KEY_PATH.exists():
            private_path.unlink()
        raise

    return str(private_path)


def load_private_key() -> Ed25519PrivateKey:
    private_path = get_private_key_path()
    if not private_path.is_file():
        raise RuntimeError(
            "Privater Entwicklerschlüssel fehlt. Zuerst 'Signierschlüssel einmalig einrichten.bat' ausführen."
        )
    private_raw = _dpapi_transform(private_path.read_bytes(), protect=False)
    return Ed25519PrivateKey.from_private_bytes(private_raw)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def generate_license_key(*, customer: str, fingerprint: str, tier: str) -> tuple[str, dict]:
    tier_settings = {
        "3m": ("3 Monate", 90),
        "12m": ("12 Monate", 365),
        "unlimited": ("Unbegrenzt", None),
    }
    if tier not in tier_settings:
        raise ValueError("Ungültige Lizenzstufe")

    now = datetime.now(timezone.utc)
    tier_name, valid_days = tier_settings[tier]
    payload = {
        "customer": customer.strip(),
        "nbf": now.isoformat(),
        "issued_at": now.isoformat(),
        "hwfp": fingerprint.strip().lower(),
        "tier": tier_name,
    }
    if valid_days is not None:
        payload["exp"] = (now + timedelta(days=valid_days)).isoformat()

    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))
    signature_b64 = _b64url(load_private_key().sign(payload_b64.encode("ascii")))
    return f"{LICENSE_ALGORITHM}.{payload_b64}.{signature_b64}", payload