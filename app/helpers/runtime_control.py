from __future__ import annotations

import threading
import time
from typing import Optional, Tuple


_LOCK = threading.Lock()
_last_activity_monotonic = time.monotonic()
_last_disconnect_monotonic: Optional[float] = None
_shutdown_requested = False
_shutdown_reason = ""


def touch_activity() -> None:
    global _last_activity_monotonic
    with _LOCK:
        _last_activity_monotonic = time.monotonic()


def report_browser_disconnect() -> None:
    global _last_disconnect_monotonic
    with _LOCK:
        _last_disconnect_monotonic = time.monotonic()


def request_shutdown(reason: str) -> None:
    global _shutdown_requested, _shutdown_reason
    with _LOCK:
        _shutdown_requested = True
        _shutdown_reason = reason or "shutdown requested"


def should_shutdown(
    inactivity_timeout_seconds: int,
    disconnect_grace_seconds: int,
) -> Tuple[bool, str]:
    with _LOCK:
        now = time.monotonic()

        if _shutdown_requested:
            return True, _shutdown_reason

        inactivity = now - _last_activity_monotonic
        if inactivity_timeout_seconds > 0 and inactivity >= inactivity_timeout_seconds:
            return True, f"watchdog inactivity timeout ({int(inactivity)}s)"

        if _last_disconnect_monotonic is not None:
            disconnect_age = now - _last_disconnect_monotonic
            if (
                disconnect_age >= disconnect_grace_seconds
                and _last_activity_monotonic <= _last_disconnect_monotonic
            ):
                return True, "browser disconnect beacon without reconnect"

    return False, ""
