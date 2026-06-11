# manifest_launcher.py
import os
import sys
import socket
import logging
import threading
import webbrowser
import signal
import time
import json
import subprocess
import hmac
import hashlib
import datetime as dt
from contextlib import closing

from waitress import serve
from app.security.credentials import get_default_secrets_path, get_runtime_home_dir, random_secret_key
from app.security.hardware_fingerprint import get_machine_fingerprint
from app.security.license import get_signing_secret, validate_license_key

# ------------------------------------------------------------
# Konfiguration
# ------------------------------------------------------------
HOST = "0.0.0.0"
PORT = 5000
OPEN_URL = f"http://localhost:5000/pwa"
THREADS = 6
# 0 disables inactivity auto-shutdown so standby/long idle does not kill the server.
def _read_positive_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value


WATCHDOG_INACTIVITY_SECONDS = _read_positive_int_env("MANIFEST_WATCHDOG_INACTIVITY_SECONDS", 0)
DISCONNECT_GRACE_SECONDS = 20
CLOCK_SKEW_TOLERANCE_SECONDS = 300

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_default_log_dir = os.path.join(BASE_DIR, "logs")
_runtime_log_dir = os.path.join(get_runtime_home_dir(), "logs")
LOG_DIR = _default_log_dir
try:
    os.makedirs(_default_log_dir, exist_ok=True)
except (OSError, PermissionError):
    LOG_DIR = _runtime_log_dir
LOG_FILE = os.path.join(LOG_DIR, "manifest_launcher.log")

# ------------------------------------------------------------
# Umgebung (Produktiv)
# ------------------------------------------------------------
os.environ.setdefault("MANIFEST_ENV", "production")
# GLib/GIO-Warnungen über UWP-Apps unterdrücken (harmlose GTK-Windows-Eigenheit)
os.environ.setdefault("GIO_USE_VFS", "local")


def _load_runtime_secrets() -> dict:
    cfg_path = os.environ.get("MANIFEST_SECRETS_PATH", "").strip() or get_default_secrets_path()
    if not os.path.exists(cfg_path):
        raise RuntimeError(
            "Secrets-Datei fehlt. Erwartet: "
            f"{cfg_path}. Bitte Installer erneut ausfuehren."
        )

    with open(cfg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise RuntimeError("Secrets-Datei hat ungueltiges Format")
    return {"path": cfg_path, "data": data}


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _parse_iso_utc(raw: str) -> dt.datetime | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _derive_license_tier(payload: dict) -> str:
    tier = str((payload or {}).get("tier", "")).strip()
    if tier:
        return tier

    exp_dt = _parse_iso_utc(str((payload or {}).get("exp", "")))
    if exp_dt is None:
        return "Unbegrenzt"

    nbf_dt = _parse_iso_utc(str((payload or {}).get("nbf", ""))) or _utc_now()
    duration_days = max(0, int((exp_dt - nbf_dt).total_seconds() // 86400))
    if duration_days <= 100:
        return "3 Monate"
    if duration_days <= 400:
        return "12 Monate"
    return f"{duration_days} Tage"


def _runtime_state_payload(secrets_cfg: dict) -> str:
    state = {
        "license_key": str(secrets_cfg.get("license_key", "")),
        "license_hwfp": str(secrets_cfg.get("license_hwfp", "")),
        "machine_fingerprint": str(secrets_cfg.get("machine_fingerprint", "")),
        "last_validated_utc": str(secrets_cfg.get("last_validated_utc", "")),
        "clock_tamper_locked": bool(secrets_cfg.get("clock_tamper_locked", False)),
        "clock_tamper_reason": str(secrets_cfg.get("clock_tamper_reason", "")),
    }
    return json.dumps(state, separators=(",", ":"), sort_keys=True)


def _runtime_state_signature(secrets_cfg: dict, signing_secret: str) -> str:
    payload = _runtime_state_payload(secrets_cfg).encode("utf-8")
    return hmac.new(signing_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _persist_runtime_secrets(cfg_path: str, secrets_cfg: dict, signing_secret: str) -> None:
    secrets_cfg["runtime_state_sig"] = _runtime_state_signature(secrets_cfg, signing_secret)
    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(secrets_cfg, f, indent=2, ensure_ascii=False)
    except PermissionError:
        # Schreibzugriff verweigert (z.B. fehlende Rechte auf das Laufzeit-Home).
        # Lizenzprüfung war erfolgreich – Start trotzdem zulassen.
        print(
            f"[WARNUNG] Laufzeit-Secrets konnten nicht gespeichert werden "
            f"(Zugriff verweigert: {cfg_path}). "
            "Bitte als Administrator starten, um diesen Hinweis zu vermeiden.",
            flush=True,
        )


def _apply_runtime_secrets() -> None:
    loaded = _load_runtime_secrets()
    cfg_path = loaded["path"]
    secrets_cfg = loaded["data"]
    signing_secret = get_signing_secret()

    existing_sig = str(secrets_cfg.get("runtime_state_sig", "")).strip()
    if existing_sig:
        expected_sig = _runtime_state_signature(secrets_cfg, signing_secret)
        if not hmac.compare_digest(existing_sig, expected_sig):
            raise RuntimeError("Secrets-Datei manipuliert (Signatur ungueltig)")

    admin_hash = str(secrets_cfg.get("admin_password_hash", "")).strip()
    db_admin_hash = str(secrets_cfg.get("db_admin_password_hash", "")).strip()
    if not admin_hash and not db_admin_hash:
        raise RuntimeError("Keine Admin-Passwort-Hashes in Secrets-Datei")

    license_key = str(secrets_cfg.get("license_key", "")).strip()
    if not license_key:
        raise RuntimeError("Lizenzschluessel fehlt in Secrets-Datei")

    machine_fingerprint = get_machine_fingerprint()
    ok, msg, payload = validate_license_key(
        license_key,
        signing_secret,
        machine_fingerprint=machine_fingerprint,
    )
    if not ok:
        raise RuntimeError(f"Lizenzpruefung fehlgeschlagen: {msg}")

    if not payload or not str(payload.get("hwfp", "")).strip():
        raise RuntimeError("Lizenzpruefung fehlgeschlagen: Maschinenbindung (hwfp) fehlt")

    stored_machine_fingerprint = str(secrets_cfg.get("machine_fingerprint", "")).strip().lower()
    if stored_machine_fingerprint and stored_machine_fingerprint != machine_fingerprint.lower():
        raise RuntimeError("Installations-Secrets gehoeren zu einer anderen Maschine")

    now_utc = _utc_now()
    if bool(secrets_cfg.get("clock_tamper_locked", False)):
        reason = str(secrets_cfg.get("clock_tamper_reason", "Datum-Manipulationsschutz aktiv")).strip()
        raise RuntimeError(f"Start gesperrt: {reason}")

    last_validated_utc = _parse_iso_utc(str(secrets_cfg.get("last_validated_utc", "")))
    if last_validated_utc and (now_utc + dt.timedelta(seconds=CLOCK_SKEW_TOLERANCE_SECONDS) < last_validated_utc):
        secrets_cfg["clock_tamper_locked"] = True
        secrets_cfg["clock_tamper_reason"] = "Systemzeit wurde zurueckgestellt"
        secrets_cfg["clock_tamper_detected_at_utc"] = now_utc.isoformat()
        _persist_runtime_secrets(cfg_path, secrets_cfg, signing_secret)
        raise RuntimeError("Start gesperrt: Systemzeit wurde zurueckgestellt")

    secrets_cfg["machine_fingerprint"] = machine_fingerprint
    secrets_cfg["license_exp"] = str(payload.get("exp", "")) if payload else ""
    secrets_cfg["license_hwfp"] = str(payload.get("hwfp", "")) if payload else ""
    secrets_cfg["license_tier"] = _derive_license_tier(payload or {})
    secrets_cfg["last_validated_utc"] = now_utc.isoformat()
    secrets_cfg["clock_tamper_locked"] = False
    secrets_cfg["clock_tamper_reason"] = ""
    _persist_runtime_secrets(cfg_path, secrets_cfg, signing_secret)

    os.environ["MANIFEST_ADMIN_PASSWORD_HASH"] = admin_hash
    os.environ["MANIFEST_DB_ADMIN_PASSWORD_HASH"] = db_admin_hash
    os.environ.setdefault("MANIFEST_SECRET_KEY", str(secrets_cfg.get("secret_key", "")).strip() or random_secret_key())
    os.environ["MANIFEST_LICENSE_EXPIRES_AT"] = str(payload.get("exp", "")) if payload else ""
    os.environ["MANIFEST_LICENSE_HWFP"] = str(payload.get("hwfp", "")) if payload else ""
    os.environ["MANIFEST_LICENSE_TIER"] = str(secrets_cfg.get("license_tier", "Unbekannt")).strip() or "Unbekannt"
    os.environ["MANIFEST_LICENSE_CUSTOMER"] = str((payload or {}).get("customer", "")).strip()


_IS_DEV = os.environ.get("MANIFEST_ENV", "").strip().lower() == "dev"

if not _IS_DEV:
    _apply_runtime_secrets()
else:
    # Dev-Modus: Lizenz-/Secrets-Prüfung überspringen.
    # Passwörter kommen aus MANIFEST_ADMIN_PASSWORD / MANIFEST_DB_ADMIN_PASSWORD
    # (Klartextfall – wird in app/__init__.py automatisch gehashed).
    print("[DEV] Lizenz- und Secrets-Prüfung übersprungen (MANIFEST_ENV=dev)", flush=True)

# ------------------------------------------------------------
# Logging (Datei, kein Fenster)
# ------------------------------------------------------------
os.makedirs(LOG_DIR, exist_ok=True, mode=0o777)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")]
)
log = logging.getLogger("manifest-launcher")

# ------------------------------------------------------------
# Port-Check (Doppelstart verhindern)
# ------------------------------------------------------------
def port_in_use(port: int) -> bool:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0

# ------------------------------------------------------------
# Browser öffnen
# ------------------------------------------------------------
def open_browser():
    try:
        if os.name == "nt":
            subprocess.Popen(
                ["cmd", "/c", "start", "", OPEN_URL],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            webbrowser.open(OPEN_URL)
        log.info("Browser geöffnet: %s", OPEN_URL)
    except Exception:
        try:
            webbrowser.open(OPEN_URL)
            log.info("Browser geöffnet (Fallback): %s", OPEN_URL)
        except Exception:
            log.exception("Browser konnte nicht geöffnet werden")

# ------------------------------------------------------------
# Sauberer Shutdown
# ------------------------------------------------------------
def shutdown(signum, frame):
    log.info("Shutdown-Signal empfangen (%s), beende Anwendung", signum)
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# ------------------------------------------------------------
# App laden
# ------------------------------------------------------------
from app import create_app
from app.helpers.runtime_control import should_shutdown
app = create_app()


def watchdog_loop():
    while True:
        shutdown, reason = should_shutdown(
            inactivity_timeout_seconds=WATCHDOG_INACTIVITY_SECONDS,
            disconnect_grace_seconds=DISCONNECT_GRACE_SECONDS,
        )
        if shutdown:
            log.info("Watchdog beendet Waitress: %s", reason)
            os._exit(0)
        time.sleep(1.0)

# ------------------------------------------------------------
# Start
# ------------------------------------------------------------
if __name__ == "__main__":
    log.info("MANIFeST OU – Produktivstart")

    if port_in_use(PORT):
        log.info("Server läuft bereits – öffne Browser")
        open_browser()
        sys.exit(0)

    threading.Thread(target=watchdog_loop, daemon=True).start()
    threading.Timer(1.5, open_browser).start()

    log.info("Starte Waitress auf %s:%s", HOST, PORT)
    serve(app, host=HOST, port=PORT, threads=THREADS)