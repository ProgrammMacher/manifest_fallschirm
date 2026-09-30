from __future__ import annotations

import sys

from license_signing import PUBLIC_KEY_PATH, initialize_signing_key


def main() -> int:
    try:
        private_path = initialize_signing_key()
    except Exception as exc:
        print(f"Schlüsselpaar konnte nicht eingerichtet werden: {exc}", file=sys.stderr)
        return 1

    print("Ed25519-Entwicklerschlüssel ist eingerichtet.")
    print(f"Privater DPAPI-Schlüssel (nicht weitergeben): {private_path}")
    print(f"Öffentlicher Runtime-Prüfschlüssel: {PUBLIC_KEY_PATH}")
    print("Der private Schlüssel wurde nicht ausgegeben und liegt außerhalb des Repositories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())