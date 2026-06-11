from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from security_core import generate_license_key, get_signing_secret  # type: ignore


def main() -> int:
    parser = argparse.ArgumentParser(description="Generiert MANIFeST Lizenzschluessel")
    parser.add_argument("--customer", required=True)
    parser.add_argument("--valid-days", type=int, default=0)
    parser.add_argument("--no-expiry", action="store_true", help="Lizenz ohne Ablaufdatum")
    parser.add_argument(
        "--tier",
        choices=["3m", "12m", "unlimited"],
        default="",
        help="Vordefinierte Laufzeitstufe (ueberschreibt valid-days/no-expiry)",
    )
    parser.add_argument("--not-before", default="")
    parser.add_argument("--fingerprint", required=True)
    args = parser.parse_args()

    if args.tier == "3m":
        args.valid_days = 90
        args.no_expiry = False
    elif args.tier == "12m":
        args.valid_days = 365
        args.no_expiry = False
    elif args.tier == "unlimited":
        args.valid_days = 0
        args.no_expiry = True

    if not args.no_expiry and args.valid_days <= 0:
        print("Entweder --valid-days > 0 oder --no-expiry angeben", file=sys.stderr)
        return 2

    now = dt.datetime.now(dt.timezone.utc)
    nbf = now
    if args.not_before.strip():
        try:
            nbf = dt.datetime.fromisoformat(args.not_before.strip())
            if nbf.tzinfo is None:
                nbf = nbf.replace(tzinfo=dt.timezone.utc)
            else:
                nbf = nbf.astimezone(dt.timezone.utc)
        except ValueError:
            print("not-before muss ISO8601 sein", file=sys.stderr)
            return 3

    payload = {
        "customer": args.customer,
        "nbf": nbf.isoformat(),
        "issued_at": now.isoformat(),
    }
    if not args.no_expiry:
        exp = nbf + dt.timedelta(days=args.valid_days)
        payload["exp"] = exp.isoformat()

    fp = args.fingerprint.strip().lower()
    payload["hwfp"] = fp
    if args.tier == "3m":
        payload["tier"] = "3 Monate"
    elif args.tier == "12m":
        payload["tier"] = "12 Monate"
    elif args.tier == "unlimited":
        payload["tier"] = "Unbegrenzt"
    else:
        payload["tier"] = "Unbegrenzt" if args.no_expiry else f"{args.valid_days} Tage"

    key = generate_license_key(payload, get_signing_secret())
    print(key)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
