from __future__ import annotations

import base64
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import textwrap

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.security import license as runtime_license
from tools.lizenzgenerator import license_signing


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_FINGERPRINT = "a" * 64
FIXED_NOW = dt.datetime(2026, 9, 30, 12, 0, tzinfo=dt.timezone.utc)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _signed_test_license(private_key, *, tier, fingerprint=TEST_FINGERPRINT, nbf=None, exp=None):
    payload = {
        "customer": "Fixture Customer",
        "hwfp": fingerprint,
        "tier": tier,
        "nbf": (nbf or FIXED_NOW - dt.timedelta(minutes=1)).isoformat(),
        "issued_at": FIXED_NOW.isoformat(),
    }
    if exp is not None:
        payload["exp"] = exp.isoformat()
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode())
    signature = _b64url(private_key.sign(payload_b64.encode("ascii")))
    return f"MFS2.{payload_b64}.{signature}"


@pytest.fixture()
def signing_test_key(monkeypatch):
    private_key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(runtime_license, "load_public_key", lambda: private_key.public_key())
    return private_key


def test_valid_ed25519_license_is_accepted(signing_test_key):
    key = _signed_test_license(
        signing_test_key,
        tier="3 Monate",
        exp=FIXED_NOW + dt.timedelta(days=90),
    )
    ok, _, payload = runtime_license.validate_license_key(
        key,
        machine_fingerprint=TEST_FINGERPRINT,
        now_utc=FIXED_NOW,
    )
    assert ok is True
    assert payload["tier"] == "3 Monate"


def test_modified_signature_is_rejected(signing_test_key):
    key = _signed_test_license(
        signing_test_key,
        tier="Unbegrenzt",
    )
    parts = key.split(".")
    changed = "A" if parts[2][0] != "A" else "B"
    parts[2] = changed + parts[2][1:]
    ok, _, _ = runtime_license.validate_license_key(
        ".".join(parts),
        machine_fingerprint=TEST_FINGERPRINT,
        now_utc=FIXED_NOW,
    )
    assert ok is False


def test_mfs1_is_rejected(signing_test_key):
    key = _signed_test_license(signing_test_key, tier="Unbegrenzt")
    mfs1_key = key.replace("MFS2.", "MFS1.", 1)
    ok, _, _ = runtime_license.validate_license_key(
        mfs1_key,
        machine_fingerprint=TEST_FINGERPRINT,
        now_utc=FIXED_NOW,
    )
    assert ok is False


def test_wrong_machine_fingerprint_is_rejected(signing_test_key):
    key = _signed_test_license(signing_test_key, tier="12 Monate")
    ok, _, _ = runtime_license.validate_license_key(
        key,
        machine_fingerprint="b" * 64,
        now_utc=FIXED_NOW,
    )
    assert ok is False


def test_expired_license_is_rejected(signing_test_key):
    key = _signed_test_license(
        signing_test_key,
        tier="3 Monate",
        exp=FIXED_NOW - dt.timedelta(seconds=1),
    )
    ok, reason, _ = runtime_license.validate_license_key(
        key,
        machine_fingerprint=TEST_FINGERPRINT,
        now_utc=FIXED_NOW,
    )
    assert ok is False
    assert reason == "Lizenz abgelaufen"


@pytest.mark.parametrize(
    ("tier", "duration"),
    [("3 Monate", 90), ("12 Monate", 365), ("Unbegrenzt", None)],
)
def test_supported_tiers_validate(signing_test_key, tier, duration):
    expiry = FIXED_NOW + dt.timedelta(days=duration) if duration else None
    key = _signed_test_license(signing_test_key, tier=tier, exp=expiry)
    ok, _, payload = runtime_license.validate_license_key(
        key,
        machine_fingerprint=TEST_FINGERPRINT,
        now_utc=FIXED_NOW,
    )
    assert ok is True
    assert payload["tier"] == tier


def test_generator_form_uses_backend_parameter_names():
    from tools.lizenzgenerator import generator_app

    page = generator_app.app.test_client().get("/").get_data(as_text=True)
    assert 'name="customer"' in page
    assert 'name="fingerprint"' in page
    assert 'name="tier"' in page
    assert "customer," in page
    assert "fingerprint," in page
    assert "tier" in page


@pytest.mark.skipif(os.name != "nt", reason="Der Generator-Starter ist eine Windows-BAT-Datei")
def test_batch_start_imports_signer_and_handles_browser_post(tmp_path):
    startup_hook = tmp_path / "sitecustomize.py"
    startup_hook.write_text(
        textwrap.dedent(
            '''
            import builtins
            import inspect
            import os
            import sys
            import threading
            import webbrowser
            from pathlib import Path

            project_root = Path(os.environ["MFS2_DIAGNOSTIC_PROJECT_ROOT"])
            sys.path.insert(0, str(project_root))

            class TestOnlySigner:
                def sign(self, _message):
                    return b"\\0" * 64

            from tools.lizenzgenerator import license_signing
            license_signing.load_private_key = lambda: TestOnlySigner()

            real_print = builtins.print
            builtins.print = lambda *args, **kwargs: (
                None if args and str(args[0]).startswith("MFS2-Lizenzgenerator:")
                else real_print(*args, **kwargs)
            )

            class NoBrowserTimer:
                def __init__(self, *_args, **_kwargs):
                    pass

                def start(self):
                    return self

            threading.Timer = NoBrowserTimer
            webbrowser.open = lambda *_args, **_kwargs: True

            import flask

            def exercise_real_route(application, *_args, **_kwargs):
                generator_module = sys.modules["__main__"]
                signing_function = generator_module.generate_license_key
                signing_module = sys.modules[signing_function.__module__]
                assert signing_function.__module__ == "tools.lizenzgenerator.license_signing"
                assert "license_signing" not in sys.modules
                real_print("Generator __file__:", generator_module.__file__)
                real_print("Signer-Modul __file__:", signing_module.__file__)
                real_print("inspect.signature(generate_license_key):", inspect.signature(signing_function))

                from app.security import license as runtime_license

                client = application.test_client()
                page = client.get("/").get_data(as_text=True)
                assert 'name="customer"' in page
                assert 'name="fingerprint"' in page
                assert 'name="tier"' in page
                assert "customer," in page and "fingerprint," in page and "tier" in page

                expected_tiers = {
                    "3m": "3 Monate",
                    "12m": "12 Monate",
                    "unlimited": "Unbegrenzt",
                }
                for tier, expected_tier in expected_tiers.items():
                    response = client.post(
                        "/api/generate",
                        json={
                            "customer": "Runtime Test Only",
                            "fingerprint": "a" * 64,
                            "tier": tier,
                        },
                    )
                    assert response.status_code == 200, response.get_data(as_text=True)
                    result = response.get_json()
                    parsed = runtime_license.parse_license_key(result["license_key"])
                    assert parsed["payload"]["customer"] == "Runtime Test Only"
                    assert parsed["payload"]["tier"] == expected_tier

            flask.Flask.run = exercise_real_route
            '''
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["MFS2_DIAGNOSTIC_PROJECT_ROOT"] = str(PROJECT_ROOT)
    env["PYTHONPATH"] = os.pathsep.join(
        part
        for part in (str(tmp_path), str(PROJECT_ROOT), env.get("PYTHONPATH", ""))
        if part
    )
    starter = PROJECT_ROOT / "tools" / "lizenzgenerator" / "Lizenzgenerator starten.bat"
    result = subprocess.run(
        f'call "{starter}"',
        shell=True,
        executable=os.environ.get("COMSPEC", "cmd.exe"),
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    diagnostics = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert len(diagnostics) == 3, result.stdout
    assert str((PROJECT_ROOT / "tools" / "lizenzgenerator" / "generator_app.py").resolve()) in diagnostics[0]
    assert str((PROJECT_ROOT / "tools" / "lizenzgenerator" / "license_signing.py").resolve()) in diagnostics[1]
    assert "customer" in diagnostics[2]
    print("\\n".join(diagnostics))


@pytest.mark.parametrize(
    ("ui_tier", "expected_tier"),
    [("3m", "3 Monate"), ("12m", "12 Monate"), ("unlimited", "Unbegrenzt")],
)
def test_developer_generator_signs_mfs2_for_public_runtime_verifier(
    monkeypatch, signing_test_key, ui_tier, expected_tier
):
    from tools.lizenzgenerator import generator_app

    monkeypatch.setattr(license_signing, "load_private_key", lambda: signing_test_key)
    monkeypatch.setattr(generator_app, "load_private_key", lambda: signing_test_key)
    monkeypatch.setattr(runtime_license, "load_public_key", lambda: signing_test_key.public_key())

    response = generator_app.app.test_client().post(
        "/api/generate",
        json={
            "customer": "Fixture Customer",
            "fingerprint": TEST_FINGERPRINT,
            "tier": ui_tier,
        },
    )
    assert response.status_code == 200
    response_data = response.get_json()
    key = response_data["license_key"]

    ok, reason, verified_payload = runtime_license.validate_license_key(
        key,
        machine_fingerprint=TEST_FINGERPRINT,
        now_utc=dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=1),
    )
    assert key.startswith("MFS2.")
    assert ok is True, reason
    assert verified_payload["customer"] == "Fixture Customer"
    assert verified_payload["tier"] == expected_tier


def test_developer_generator_refuses_to_sign_without_private_key(monkeypatch):
    from tools.lizenzgenerator import generator_app

    def missing_key():
        raise RuntimeError("test key unavailable")

    monkeypatch.setattr(generator_app, "load_private_key", missing_key)
    response = generator_app.app.test_client().post(
        "/api/generate",
        json={
            "customer": "Fixture Customer",
            "fingerprint": TEST_FINGERPRINT,
            "tier": "3m",
        },
    )
    assert response.status_code == 500
    assert "Lizenzschlüssel" not in response.get_data(as_text=True)


def test_missing_developer_private_key_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(
        license_signing,
        "_restrict_directory_to_current_user",
        lambda _directory: None,
    )
    with pytest.raises(RuntimeError, match="Privater Entwicklerschlüssel fehlt"):
        license_signing.load_private_key()


def test_runtime_verifier_contains_only_public_key_validation():
    assert not hasattr(runtime_license, "generate_license_key")
    assert not hasattr(runtime_license, "get_signing_secret")
    public_key = runtime_license.load_public_key()
    assert public_key.__class__.__name__ == "Ed25519PublicKey"
    source = Path(runtime_license.__file__).read_text(encoding="utf-8")
    public_bytes = runtime_license._PUBLIC_KEY_PATH.read_bytes()
    assert b"BEGIN PUBLIC KEY" in public_bytes
    assert b"PRIVATE KEY" not in public_bytes
    assert "Ed25519PublicKey" in source
    assert "Ed25519PrivateKey" not in source
    assert "get_signing_secret" not in source
    assert "manifest-ou-license-secret" not in source
    assert runtime_license._PUBLIC_KEY_PATH.is_file()
    builder = (PROJECT_ROOT / "tools/build_inno_offline_setup.ps1").read_text(encoding="utf-8")
    assert "Get-ChildItem -Path (Join-Path $ProjectRoot 'tools\\license')" not in builder
    assert "tools\\license\\install_runtime_secrets.py" in builder
    assert "tools/(lizenzgenerator|fingerprint|analyse|pdf-runtime)" in builder
    assert "license_signing" in builder


def test_customer_fingerprint_script_has_hardware_only_inputs():
    fingerprint_script = (
        PROJECT_ROOT / "tools/fingerprint/Fingerprint ermitteln.ps1"
    ).read_text(encoding="utf-8")
    assert r"HKLM:\SOFTWARE\Microsoft\Cryptography" in fingerprint_script
    assert "GetVolumeInformation" in fingerprint_script
    assert "PROCESSOR_IDENTIFIER" in fingerprint_script
    assert "generate_license" not in fingerprint_script.lower()
    assert "private_key" not in fingerprint_script.lower()
    assert "signing_secret" not in fingerprint_script.lower()
