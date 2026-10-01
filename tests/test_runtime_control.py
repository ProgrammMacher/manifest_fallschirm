from __future__ import annotations

import importlib

import pytest


@pytest.fixture()
def runtime_control(monkeypatch):
    """Fresh module instance with isolated module-level state per test."""
    import app.helpers.runtime_control as module

    importlib.reload(module)
    return module


def test_disconnect_without_followup_triggers_shutdown_after_grace(runtime_control, monkeypatch):
    """Genuine browser/tab close: beforeunload beacon fires, nothing else ever
    follows -> watchdog should eventually shut the server down."""
    fake_now = [1000.0]
    monkeypatch.setattr(runtime_control.time, "monotonic", lambda: fake_now[0])

    runtime_control.report_browser_disconnect()
    fake_now[0] += 21  # past the grace period
    shutdown, reason = runtime_control.should_shutdown(
        inactivity_timeout_seconds=0, disconnect_grace_seconds=20
    )
    assert shutdown is True
    assert "disconnect" in reason


def test_navigation_disconnect_followed_by_activity_does_not_shutdown(runtime_control, monkeypatch):
    """Root-cause regression test: a normal page navigation fires the
    beforeunload/sendBeacon disconnect signal for EVERY page change, not just
    real tab closes. As long as further requests (next page load, heartbeat)
    keep arriving, the production server must never be killed by this."""
    fake_now = [1000.0]
    monkeypatch.setattr(runtime_control.time, "monotonic", lambda: fake_now[0])

    runtime_control.report_browser_disconnect()
    fake_now[0] += 5
    # The next page's request (or heartbeat) arrives before the grace period
    # elapses - this must cancel the pending "disconnected" state entirely.
    runtime_control.touch_activity()

    fake_now[0] += 30  # well past the old grace window relative to the disconnect
    shutdown, reason = runtime_control.should_shutdown(
        inactivity_timeout_seconds=0, disconnect_grace_seconds=20
    )
    assert shutdown is False
    assert reason == ""


def test_heartbeat_interval_equal_to_grace_no_longer_races(runtime_control, monkeypatch):
    """The frontend heartbeat fires every 20s; DISCONNECT_GRACE_SECONDS used to
    equal 20s too, so any jitter could race a false shutdown. Simulate the
    exact boundary repeatedly and confirm no shutdown as long as heartbeats
    keep landing (even slightly late)."""
    fake_now = [0.0]
    monkeypatch.setattr(runtime_control.time, "monotonic", lambda: fake_now[0])

    runtime_control.report_browser_disconnect()
    for _ in range(5):
        fake_now[0] += 20.4  # heartbeat arrives slightly late each cycle
        runtime_control.touch_activity()
        shutdown, _ = runtime_control.should_shutdown(
            inactivity_timeout_seconds=0, disconnect_grace_seconds=45
        )
        assert shutdown is False


def test_inactivity_timeout_still_works_when_enabled(runtime_control, monkeypatch):
    fake_now = [0.0]
    monkeypatch.setattr(runtime_control.time, "monotonic", lambda: fake_now[0])

    runtime_control.touch_activity()
    fake_now[0] += 100
    shutdown, reason = runtime_control.should_shutdown(
        inactivity_timeout_seconds=60, disconnect_grace_seconds=45
    )
    assert shutdown is True
    assert "inactivity" in reason


def test_inactivity_disabled_by_default_zero_value(runtime_control, monkeypatch):
    fake_now = [0.0]
    monkeypatch.setattr(runtime_control.time, "monotonic", lambda: fake_now[0])

    runtime_control.touch_activity()
    fake_now[0] += 10_000
    shutdown, _ = runtime_control.should_shutdown(
        inactivity_timeout_seconds=0, disconnect_grace_seconds=45
    )
    assert shutdown is False


def test_manual_shutdown_request_triggers_immediately(runtime_control):
    runtime_control.request_shutdown("manual shutdown via pwa UI")
    shutdown, reason = runtime_control.should_shutdown(
        inactivity_timeout_seconds=0, disconnect_grace_seconds=45
    )
    assert shutdown is True
    assert reason == "manual shutdown via pwa UI"
