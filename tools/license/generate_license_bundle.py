from __future__ import annotations

import argparse
import datetime as dt
import json

from app.security.license import generate_license_key, get_signing_secret


TIERS = (
    ("3 Monate", 90, False),
    ("12 Monate", 365, False),
    ("Unbegrenzt", 0, True),
)


def _build_payload(customer: str, fingerprint: str, nbf: dt.datetime, tier_name: str, valid_days: int, no_expiry: bool) -> dict:
    payload = {
        "customer": customer,
        "nbf": nbf.isoformat(),
        "issued_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "hwfp": fingerprint.strip().lower(),
        "tier": tier_name,
    }
    if not no_expiry:
        payload["exp"] = (nbf + dt.timedelta(days=valid_days)).isoformat()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Erzeugt 3 Lizenzschluessel (3M/12M/Unbegrenzt)")
    parser.add_argument("--customer", required=True)
    parser.add_argument("--fingerprint", required=True)
    parser.add_argument("--not-before", default="")
    args = parser.parse_args()

    nbf = dt.datetime.now(dt.timezone.utc)
    if args.not_before.strip():
        parsed = dt.datetime.fromisoformat(args.not_before.strip())
        if parsed.tzinfo is None:
            nbf = parsed.replace(tzinfo=dt.timezone.utc)
        else:
            nbf = parsed.astimezone(dt.timezone.utc)

    signing_secret = get_signing_secret()
    result = []
    for tier_name, valid_days, no_expiry in TIERS:
        payload = _build_payload(args.customer, args.fingerprint, nbf, tier_name, valid_days, no_expiry)
        key = generate_license_key(payload, signing_secret)
        result.append({"tier": tier_name, "key": key, "payload": payload})

    for entry in result:
        print(f"=== {entry['tier']} ===")
        print(entry["key"])
        print(json.dumps(entry["payload"], indent=2, ensure_ascii=False))
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
