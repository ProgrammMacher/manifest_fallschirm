from __future__ import annotations

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from security_core import get_machine_fingerprint  # type: ignore


if __name__ == "__main__":
    print(get_machine_fingerprint())
