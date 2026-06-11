from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import os
from typing import Any


LICENSE_ALGO = "MFS1"


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
    # Fuer echten Produktionsschutz diesen Wert bei Release variieren
    # und nicht im Quellcode belassen.
    return os.environ.get(
        "MANIFEST_LICENSE_SIGNING_SECRET",
        "manifest-ou-license-secret-change-me",
    )
