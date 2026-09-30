from __future__ import annotations

import base64
import datetime as dt
import json
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


LICENSE_ALGO = "MFS2"
_PUBLIC_KEY_PATH = Path(__file__).with_name("license_public_key.pem")
_ALLOWED_TIERS = {"3 Monate", "12 Monate", "Unbegrenzt"}


def _b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def load_public_key() -> Ed25519PublicKey:
    try:
        public_key = serialization.load_pem_public_key(_PUBLIC_KEY_PATH.read_bytes())
    except FileNotFoundError as exc:
        raise RuntimeError("Öffentlicher Lizenz-Prüfschlüssel fehlt.") from exc
    if not isinstance(public_key, Ed25519PublicKey):
        raise RuntimeError("Öffentlicher Lizenz-Prüfschlüssel hat ein ungültiges Format.")
    return public_key


def parse_license_key(license_key: str) -> dict[str, Any]:
    parts = license_key.strip().split(".")
    if len(parts) != 3:
        raise ValueError("Lizenzschlüssel-Format ungültig")
    algorithm, payload_b64, signature_b64 = parts
    if algorithm != LICENSE_ALGO:
        raise ValueError("Lizenzformat nicht unterstützt")
    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        signature = _b64url_decode(signature_b64)
    except Exception as exc:
        raise ValueError("Lizenz-Payload oder Signatur unlesbar") from exc
    if not isinstance(payload, dict) or len(signature) != 64:
        raise ValueError("Lizenz-Payload oder Signatur ungültig")
    return {"algo": algorithm, "payload_b64": payload_b64, "signature": signature, "payload": payload}


def validate_license_key(
    license_key: str,
    machine_fingerprint: str = "",
    now_utc: dt.datetime | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    """Validate MFS2 with the bundled Ed25519 public key; no signing key is used here."""
    now_utc = now_utc or dt.datetime.now(dt.timezone.utc)
    try:
        parsed = parse_license_key(license_key)
        load_public_key().verify(parsed["signature"], parsed["payload_b64"].encode("ascii"))
    except InvalidSignature:
        return False, "Lizenz-Signatur ungültig", None
    except (ValueError, RuntimeError) as exc:
        return False, str(exc), None

    payload = parsed["payload"]
    tier = str(payload.get("tier", "")).strip()
    if tier not in _ALLOWED_TIERS:
        return False, "Lizenzstufe ungültig", payload

    fingerprint = str(payload.get("hwfp", "")).strip().lower()
    if len(fingerprint) != 64 or any(char not in "0123456789abcdef" for char in fingerprint):
        return False, "Maschinenbindung ungültig", payload
    if not machine_fingerprint or fingerprint != machine_fingerprint.strip().lower():
        return False, "Lizenz ist an einen anderen Rechner gebunden", payload

    try:
        not_before = dt.datetime.fromisoformat(str(payload["nbf"]))
        if not_before.tzinfo is None:
            not_before = not_before.replace(tzinfo=dt.timezone.utc)
        else:
            not_before = not_before.astimezone(dt.timezone.utc)

        expiry_raw = str(payload.get("exp", "")).strip()
        expiry = None
        if expiry_raw:
            expiry = dt.datetime.fromisoformat(expiry_raw)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=dt.timezone.utc)
            else:
                expiry = expiry.astimezone(dt.timezone.utc)
    except (KeyError, TypeError, ValueError):
        return False, "Lizenzzeitraum ungültig", payload

    if now_utc < not_before:
        return False, "Lizenz noch nicht gültig (Startdatum)", payload
    if expiry and expiry < now_utc:
        return False, "Lizenz abgelaufen", payload
    if (tier == "Unbegrenzt") != (expiry is None):
        return False, "Lizenzzeitraum passt nicht zur Lizenzstufe", payload

    return True, "Lizenz gültig", payload