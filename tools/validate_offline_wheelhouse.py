from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prueft, ob requirements.txt strikt offline aus packages installierbar ist."
    )
    parser.add_argument("--project-root", required=True)
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python-Interpreter fuer den pip-Dry-Run (Standard: aktueller Interpreter)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    requirements_file = project_root / "requirements.txt"
    wheelhouse_dir = project_root / "packages"

    if not requirements_file.is_file():
        print(f"[FEHLER] requirements.txt fehlt: {requirements_file}", file=sys.stderr)
        return 2
    if not wheelhouse_dir.is_dir():
        print(f"[FEHLER] packages-Ordner fehlt: {wheelhouse_dir}", file=sys.stderr)
        return 3

    command = [
        str(Path(args.python).resolve()),
        "-m",
        "pip",
        "install",
        "--dry-run",
        "--ignore-installed",
        "--no-index",
        "--find-links",
        str(wheelhouse_dir),
        "-r",
        str(requirements_file),
    ]

    print("[INFO] Pruefe Offline-Wheelhouse gegen requirements.txt ...")
    result = subprocess.run(command, cwd=project_root)
    if result.returncode != 0:
        print(
            "[FEHLER] Nicht alle Abhaengigkeiten sind strikt offline aus packages installierbar.",
            file=sys.stderr,
        )
        return result.returncode

    print("[OK] Offline-Wheelhouse ist vollstaendig.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())