from flask import Flask, redirect, url_for, request, session, g
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask_mail import Mail
from zoneinfo import ZoneInfo
from datetime import datetime, date
from tzlocal import get_localzone_name
import os
import time
import logging

# ✅ Datenbank
db = SQLAlchemy()

# ✅ Mail (für Rechnung per E-Mail)
mail = Mail()

# ✅ OPTIONALE zentrale Navigation für Sidebar & PWA
from app.routes.navigation import NAV_ITEMS
from app.helpers.runtime_control import touch_activity
from app.helpers.pdf_runtime import ensure_weasyprint_pdf_runtime
from app.security.credentials import hash_password, get_runtime_home_dir

# ---------------------------------------------------------
# Zeitzone: automatisch aus Systemeinstellung (z.B. Europe/Berlin)
# ---------------------------------------------------------
try:
    APP_TIMEZONE = ZoneInfo(get_localzone_name())
except Exception:
    APP_TIMEZONE = ZoneInfo("Europe/Berlin")  # Fallback
UTC_TIMEZONE = ZoneInfo("UTC")


def _ensure_windows_gtk_runtime() -> None:
    """
    Stellt unter Windows sicher, dass GTK/Cairo/Pango fuer WeasyPrint
    unabhängig vom Startskript gefunden wird.
    """
    if os.name != "nt":
        return

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    gtk_candidates = [
        os.environ.get("MANIFEST_GTK_BIN", "").strip(),
        os.path.join(project_root, "third_party", "gtk", "bin"),
        os.path.join(project_root, "runtime", "gtk", "bin"),
    ]
    gtk_bin = next((p for p in gtk_candidates if p and os.path.isdir(p)), "")
    if not gtk_bin:
        return

    path = os.environ.get("PATH", "")
    parts = path.split(os.pathsep) if path else []
    if gtk_bin not in parts:
        os.environ["PATH"] = gtk_bin + os.pathsep + path

    add_dll_directory = getattr(os, "add_dll_directory", None)
    if callable(add_dll_directory):
        try:
            add_dll_directory(gtk_bin)
        except Exception:
            # PATH-Fallback reicht in den meisten Umgebungen aus.
            pass

def now_local() -> datetime:
    """Aktuelle Zeit in der Systemtimezone."""
    return datetime.now(tz=APP_TIMEZONE)

# Alias für Abwärtskompatibilität (wird schrittweise entfernt)
now_berlin = now_local

def _to_local(dt: datetime) -> datetime | None:
    """Datetime in die Systemtimezone konvertieren."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=APP_TIMEZONE)
    return dt.astimezone(APP_TIMEZONE)

# Alias für Abwärtskompatibilität
_to_berlin = _to_local


def _ensure_writable_dir(primary_dir: str, fallback_dir: str) -> str:
    """Nutze bevorzugt primary_dir, falle bei fehlenden Rechten auf fallback_dir zurück."""
    candidates: list[str] = []
    for candidate in (primary_dir, fallback_dir):
        normalized = os.path.abspath(candidate)
        if normalized not in candidates:
            candidates.append(normalized)

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            os.makedirs(candidate, exist_ok=True)
            probe_path = os.path.join(candidate, ".write_probe")
            with open(probe_path, "w", encoding="utf-8") as probe:
                probe.write("ok")
            os.remove(probe_path)
            return candidate
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise RuntimeError("Kein schreibbares Verzeichnis gefunden")

def create_app():
    _ensure_windows_gtk_runtime()
    if os.name == "nt":
        # Startup bleibt absichtlich "lazy": kein aktiver DLL-Preflight,
        # damit beim App-Start keine GLib/GIO-UWP-Warnungen im Terminal entstehen.
        # Fuer Diagnose kann der alte Preflight optional wieder aktiviert werden.
        preflight_enabled = os.environ.get("MANIFEST_PDF_RUNTIME_PREFLIGHT", "0").lower() in (
            "1", "true", "yes", "on"
        )
        if preflight_enabled:
            try:
                ok, msg = ensure_weasyprint_pdf_runtime()
                if ok:
                    print(f"[MANIFEST] PDF-Runtime bereit: {msg}", flush=True)
                else:
                    print(f"[MANIFEST][WARN] PDF-Runtime nicht vollstaendig: {msg}", flush=True)
            except Exception as exc:
                print(f"[MANIFEST][WARN] PDF-Runtime-Pruefung fehlgeschlagen: {exc}", flush=True)
        else:
            print(
                "[MANIFEST] PDF-Runtime-Preflight: deaktiviert (lazy check bei PDF-Erstellung)",
                flush=True,
            )

    app = Flask(__name__)
    app.logger.setLevel(logging.INFO)
    # Verhindert massive Terminal-Logfluten durch Access-Logs im Dev-Server.
    werkzeug_level_name = os.environ.get("MANIFEST_WERKZEUG_LOG_LEVEL", "WARNING").upper()
    werkzeug_level = getattr(logging, werkzeug_level_name, logging.WARNING)
    logging.getLogger("werkzeug").setLevel(werkzeug_level)

    # ---------------------------------------------------------
    # Basisverzeichnisse
    # ---------------------------------------------------------
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # .../app
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))  # .../manifest_fallschirm
    RUNTIME_HOME_ROOT = get_runtime_home_dir()

    # ---------------------------------------------------------
    # Logging
    # ---------------------------------------------------------
    LOG_DIR = _ensure_writable_dir(
        os.path.join(RUNTIME_HOME_ROOT, "logs"),
        os.path.join(PROJECT_ROOT, "logs"),
    )
    REQUEST_LOG_FILE = os.path.join(LOG_DIR, "http_requests.log")
    request_log_console = os.environ.get("MANIFEST_REQUEST_LOG_CONSOLE", "0").lower() in ("1", "true", "yes", "on")
    try:
        request_log_min_ms = float(os.environ.get("MANIFEST_REQUEST_LOG_MIN_MS", "1200"))
    except ValueError:
        request_log_min_ms = 1200.0
    request_log_skip_prefixes = (
        "/static/",
        "/pwa/runtime/heartbeat",
    )

    # ---------------------------------------------------------
    # Datenbankpfad (SQLite)
    # ---------------------------------------------------------
    PROJECT_DATA_DIR = os.path.join(PROJECT_ROOT, "data")
    DATA_DIR = _ensure_writable_dir(
        os.path.join(RUNTIME_HOME_ROOT, "data"),
        PROJECT_DATA_DIR,
    )

    old_db_path = os.path.join(PROJECT_ROOT, "manifest.db")
    new_db_path = os.path.join(DATA_DIR, "manifest.db")

    env_db_path = os.environ.get("MANIFEST_DB_PATH", "").strip()
    if env_db_path:
        db_path = env_db_path
    else:
        # Automatische Migration alter DB-Struktur
        if DATA_DIR == PROJECT_DATA_DIR and os.path.exists(old_db_path) and not os.path.exists(new_db_path):
            db_path = old_db_path
        else:
            db_path = new_db_path

    # ---------------------------------------------------------
    # Netzwerk / Mobile-IP (aus Start-Skript)
    # ---------------------------------------------------------
    manifest_local_ip = os.environ.get("MANIFEST_LOCAL_IP", "").strip()

    admin_password = os.environ.get("MANIFEST_ADMIN_PASSWORD", "")
    db_admin_password = os.environ.get("MANIFEST_DB_ADMIN_PASSWORD", "")
    admin_password_hash = os.environ.get("MANIFEST_ADMIN_PASSWORD_HASH", "")
    db_admin_password_hash = os.environ.get("MANIFEST_DB_ADMIN_PASSWORD_HASH", "")

    # Rueckwaertskompatibilitaet: Falls noch Klartext-ENV genutzt wird,
    # werden zur Laufzeit Hashes abgeleitet.
    if not admin_password_hash and admin_password:
        admin_password_hash = hash_password(admin_password)
    if not db_admin_password_hash and db_admin_password:
        db_admin_password_hash = hash_password(db_admin_password)

    # ---------------------------------------------------------
    # App-Konfiguration
    # ---------------------------------------------------------
    app.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,

        # 🔐 Flask Session / Sicherheit
        SECRET_KEY=os.environ.get(
            "MANIFEST_SECRET_KEY",
            "bitte-später-ändern"
        ),

        # 🌍 Zeitzone (aus Systemeinstellung)
        APP_TIMEZONE=str(APP_TIMEZONE),  # z.B. 'Europe/Berlin'

        # 🔐 Admin-Passwörter (Hash-basiert)
        ADMIN_PASSWORD_HASH=admin_password_hash,
        DB_ADMIN_PASSWORD_HASH=db_admin_password_hash,

        # 🌐 Local IP für QR / Mobile Access
        MANIFEST_LOCAL_IP=manifest_local_ip,
        MANIFEST_PORT=int(
            os.environ.get("MANIFEST_PORT", "5000")
        ),
        MANIFEST_ENV=os.environ.get("MANIFEST_ENV", "development"),
        MANIFEST_LICENSE_TIER=os.environ.get("MANIFEST_LICENSE_TIER", "Unbekannt"),
        MANIFEST_LICENSE_EXPIRES_AT=os.environ.get("MANIFEST_LICENSE_EXPIRES_AT", ""),
        MANIFEST_LICENSE_CUSTOMER=os.environ.get("MANIFEST_LICENSE_CUSTOMER", ""),
    )

    # ---------------------------------------------------------
    # SQLite Engine Optionen
    # ---------------------------------------------------------
    app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {})
    app.config["SQLALCHEMY_ENGINE_OPTIONS"].update({
        "pool_pre_ping": True,
        "connect_args": {"check_same_thread": False},
    })

    # ---------------------------------------------------------
    # Upload-Verzeichnis
    # ---------------------------------------------------------
    app.config["UPLOAD_FOLDER"] = _ensure_writable_dir(
        os.path.join(RUNTIME_HOME_ROOT, "uploads"),
        os.path.join(BASE_DIR, "uploads"),
    )

    # ---------------------------------------------------------
    # Serverseitige Session
    # ---------------------------------------------------------
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = _ensure_writable_dir(
        os.path.join(RUNTIME_HOME_ROOT, "session_data"),
        os.path.join(BASE_DIR, "session_data"),
    )
    Session(app)

    @app.before_request
    def remember_last_page():
        """
        Merkt sich die zuletzt besuchte *inhaltliche* Seite,
        um nach dem Admin-Login dorthin zurückzuleiten.
        """
        if request.method != "GET":
            return

        path = request.path or ""

        EXCLUDED_PREFIXES = (
            "/admin/login",
            "/pwa/health",
            "/pwa/publish",
            "/pwa/publish/status",
            "/api/",
            "/static/",
        )

        if path.startswith(EXCLUDED_PREFIXES):
            return

        session["last_page"] = path

    @app.before_request
    def runtime_touch_activity():
        path = request.path or ""
        if path.startswith("/static/"):
            return
        touch_activity()

    @app.before_request
    def _request_log_start_time():
        g._request_started_at = time.perf_counter()

    @app.after_request
    def _request_log_line(response):
        path = request.path or ""
        if path.startswith("/static/"):
            return response

        started = getattr(g, "_request_started_at", None)
        if started is not None:
            duration_ms = (time.perf_counter() - started) * 1000.0
        else:
            duration_ms = -1.0

        is_noisy = path.startswith(request_log_skip_prefixes)
        is_interesting = response.status_code >= 400 or duration_ms >= request_log_min_ms
        if is_noisy and not is_interesting:
            return response

        line = (
            f"{now_local().strftime('%H:%M:%S')} "
            f"{request.method} {path} -> {response.status_code} ({duration_ms:.1f} ms)"
        )

        # Konsole nur auf Wunsch, sonst nur Datei fuer geringere Terminal-Last.
        if request_log_console:
            print(line, flush=True)

        try:
            with open(REQUEST_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

        if is_interesting:
            app.logger.info(line)
        return response

    print("[MANIFEST] Request-Logging aktiv: Konsole + logs/http_requests.log", flush=True)

    # ---------------------------------------------------------
    # Erweiterungen initialisieren
    # ---------------------------------------------------------
    db.init_app(app)

    # ✅ Flask-Mail initialisieren (ERFORDERLICH!)
    mail.init_app(app)

    # ---------------------------------------------------------
    # STARTUP-DB-MIGRATIONEN
    # ---------------------------------------------------------
    from app.helpers.db_migrations import run_startup_migrations
    with app.app_context():
        run_startup_migrations()

    # ---------------------------------------------------------
    # Migrationen (optional)
    # ---------------------------------------------------------
    if os.environ.get("MANIFEST_ENABLE_MIGRATIONS", "0").lower() in ("1", "true", "yes"):
        try:
            from flask_migrate import Migrate
            Migrate(app, db)
        except Exception as e:
            print("[WARNUNG] Migrationen konnten nicht aktiviert werden:", e)

    # ---------------------------------------------------------
    # Modelle importieren
    # ---------------------------------------------------------
    from app.models.aircraft import Aircraft
    from app.models.load import Load
    from app.models.load_entry import LoadEntry
    from app.models.person import Person
    from app.models.status_definition import StatusDefinition
    from app.models.flugplatz import Flugplatz
    from app.models.billing_config import BillingPrice, BillingPricePeriod
    from app.models.email_config import EmailConfig
    from app.models.email_send_log import EmailSendLog

    # ---------------------------------------------------------
    # Tabellen erzeugen (DEV)
    # ---------------------------------------------------------
    if os.environ.get("MANIFEST_AUTO_CREATE_DB", "1").lower() not in ("0", "false", "no"):
        with app.app_context():
            db.create_all()

    # ---------------------------------------------------------
    # Blueprints importieren
    # ---------------------------------------------------------
    from app.routes.settings_status import bp_settings_status
    from app.routes.load import bp_load
    from app.routes.load_entry import bp_load_entry
    from app.routes.aircraft import bp_aircraft
    from app.routes.person import bp_person
    from app.routes.pricing import bp_pricing
    from app.routes.pwa import bp as bp_pwa
    from app.routes.api_weather import bp as bp_api_weather
    from app.routes.api_upperwind import bp as bp_api_upperwind
    from app.routes.import_preview import bp as bp_import_preview
    from app.routes.import_execute import bp as bp_import_execute
    from app.routes.flugplatz import bp as bp_flugplatz
    from app.routes.export_person import bp_export_person
    from app.routes.billing import bp as bp_billing
    from app.routes.admin_auth import bp_admin_auth, is_admin
    from app.routes.admin_database import bp as bp_admin_database
    from app.routes.email_newsletter import bp as bp_email_nl

    # ---------------------------------------------------------
    # Blueprints registrieren
    # ---------------------------------------------------------
    app.register_blueprint(bp_settings_status)
    app.register_blueprint(bp_load)
    app.register_blueprint(bp_load_entry)
    app.register_blueprint(bp_aircraft)
    app.register_blueprint(bp_person)
    app.register_blueprint(bp_pricing)
    app.register_blueprint(bp_pwa)
    app.register_blueprint(bp_api_weather)
    app.register_blueprint(bp_api_upperwind)
    app.register_blueprint(bp_import_preview)
    app.register_blueprint(bp_import_execute)
    app.register_blueprint(bp_flugplatz)
    app.register_blueprint(bp_export_person)
    app.register_blueprint(bp_billing)
    app.register_blueprint(bp_admin_auth)
    app.register_blueprint(bp_admin_database)
    app.register_blueprint(bp_email_nl)

    # ---------------------------------------------------------
    # Jinja-Filter
    # ---------------------------------------------------------
    def datetimeformat_input(value):
        if not value:
            return ""
        dt = _to_local(value)
        return dt.strftime("%Y-%m-%dT%H:%M")

    def datetimeformat_display(value, fmt="%d.%m.%Y um %H:%M"):
        """Formatiert lokale DateTime für Anzeige."""
        if not value:
            return ""
        dt = _to_local(value)
        return dt.strftime(fmt)

    def datetimeformat_display_from_utc(value, fmt="%d.%m.%Y um %H:%M"):
        """
        Konvertiert Datetimes aus UTC nach Europe/Berlin.
        Naive Datetimes werden als UTC interpretiert (wichtig fuer legacy utcnow()-Speicherungen).
        """
        if not value:
            return ""
        dt = value
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return ""
            # Support fuer ISO-Strings aus app_settings (z.B. "2026-05-11T09:15:30" oder mit "Z").
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                return value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_TIMEZONE)
        dt = dt.astimezone(APP_TIMEZONE)
        return dt.strftime(fmt)

    app.jinja_env.filters["datetimeformat_input"] = datetimeformat_input
    app.jinja_env.filters["datetimeformat_display"] = datetimeformat_display
    app.jinja_env.filters["datetimeformat_display_from_utc"] = datetimeformat_display_from_utc

    from app.helpers.status_code import status_display_label
    app.jinja_env.filters["status_label"] = status_display_label

    # ---------------------------------------------------------
    # Context-Processor: Zeit
    # ---------------------------------------------------------
    @app.context_processor
    def inject_time_helpers():
        return {"now_berlin": now_local, "now_local": now_local, "APP_TIMEZONE": APP_TIMEZONE}

    # ---------------------------------------------------------
    # Context-Processor: date & datetime
    # ---------------------------------------------------------
    @app.context_processor
    def inject_date_utils():
        return {"date": date, "datetime": datetime}

    # ---------------------------------------------------------
    # Context-Processor: Admin
    # ---------------------------------------------------------
    @app.context_processor
    def inject_admin_utils():
        return {"is_admin": is_admin}

    # ---------------------------------------------------------
    # ✅ OPTIONAL: Context-Processor Navigation (NEU)
    # ---------------------------------------------------------
    @app.context_processor
    def inject_navigation():
        return {"nav_items": NAV_ITEMS}

    @app.context_processor
    def inject_license_meta():
        exp_raw = app.config.get("MANIFEST_LICENSE_EXPIRES_AT", "")
        env_name = str(app.config.get("MANIFEST_ENV", "development")).strip().lower()
        is_dev_mode = env_name != "production"
        exp_display = ""
        if exp_raw:
            try:
                exp_dt = datetime.fromisoformat(str(exp_raw))
                exp_display = exp_dt.strftime("%d.%m.%Y")
            except Exception:
                exp_display = str(exp_raw)

        return {
            "manifest_license_tier": app.config.get("MANIFEST_LICENSE_TIER", "Unbekannt"),
            "manifest_license_expires_at": exp_display,
            "manifest_license_customer": app.config.get("MANIFEST_LICENSE_CUSTOMER", ""),
            "manifest_is_dev": is_dev_mode,
        }

    # ---------------------------------------------------------
    # Startseite
    # ---------------------------------------------------------
    @app.route("/")
    def index():
        return redirect(url_for("pwa.pwa_index"))

    return app