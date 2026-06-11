# C:\manifest_fallschirm\app\helpers\app_settings.py
from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime
from typing import Any, Dict, Optional, List
from app.security.credentials import get_runtime_home_dir

# Settings-Datei liegt im Laufzeit-Home unter "data".
# Standard ist die Projektkopie; der Installer kann das Laufzeit-Home
# bei Bedarf explizit setzen.
_DEFAULT_SETTINGS_FILENAME = "app_settings.json"


def _pick_writable_settings_dir() -> str:
    runtime_data_dir = os.path.join(get_runtime_home_dir(), "data")
    os.makedirs(runtime_data_dir, exist_ok=True)
    return runtime_data_dir


_SETTINGS_DIR = _pick_writable_settings_dir()

_LOCK = threading.Lock()


def _to_project_relative(path: str) -> str:
    """
    Konvertiert absolute Pfade innerhalb des Projekts in projektrelative Pfade.
    Externe Pfade bleiben unverändert.
    """
    if not path:
        return path
    try:
        abs_path = os.path.abspath(path)
        rel_path = os.path.relpath(abs_path, _PROJECT_ROOT)
        if rel_path.startswith(".."):
            return path
        return rel_path
    except Exception:
        return path


def _normalize_record_paths(record: Dict[str, Any]) -> Dict[str, Any]:
    """Normalisiert mögliche Pfadfelder in gespeicherten Metadaten."""
    normalized = dict(record)
    file_path = normalized.get("file")
    if isinstance(file_path, str):
        normalized["file"] = _to_project_relative(file_path)

    log_file = normalized.get("log_file")
    if isinstance(log_file, str):
        normalized["log_file"] = _to_project_relative(log_file)

    sources = normalized.get("sources")
    if isinstance(sources, list):
        normalized["sources"] = [
            _to_project_relative(p) if isinstance(p, str) else p
            for p in sources
        ]

    return normalized


def _utc_now_iso_seconds() -> str:
    """UTC-Zeitstempel ohne Sekundenbruchteile."""
    return datetime.utcnow().isoformat(timespec="seconds")


def _settings_path() -> str:
    """
    Liefert absoluten Pfad zur Settings-Datei.
    Relativ zur Projekt-Root (current working dir beim Start via .bat ist Root).
    """
    return os.path.join(_SETTINGS_DIR, _DEFAULT_SETTINGS_FILENAME)


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def _load_all() -> Dict[str, Any]:
    """
    Lädt die komplette Settings-Datei als Dict.
    Defensiv: nie crashen, bei Fehlern leeres Dict zurückgeben.
    """
    path = _settings_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        # defensiv: nie crashen
        return {}


def _atomic_write(path: str, data: Dict[str, Any]) -> None:
    """
    Atomisches Schreiben:
    - schreibt in eine temporäre Datei im gleichen Ordner
    - ersetzt dann die Zieldatei via os.replace()
    """
    _ensure_parent_dir(path)
    dir_name = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(prefix="app_settings_", suffix=".json", dir=dir_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def get_setting(key: str, default: Any = None) -> Any:
    with _LOCK:
        data = _load_all()
        return data.get(key, default)


def set_setting(key: str, value: Any) -> None:
    with _LOCK:
        data = _load_all()
        data[key] = value
        data["_last_updated_utc"] = _utc_now_iso_seconds()
        _atomic_write(_settings_path(), data)


def delete_setting(key: str) -> None:
    with _LOCK:
        data = _load_all()
        if key in data:
            del data[key]
            data["_last_updated_utc"] = _utc_now_iso_seconds()
            _atomic_write(_settings_path(), data)


def ensure_defaults() -> None:
    """
    OPTIONAL: Stellt sicher, dass Basis-Keys existieren.
    Überschreibt KEINE existierenden Werte.
    """
    with _LOCK:
        data = _load_all()
        if "_last_updated_utc" not in data:
            data["_last_updated_utc"] = _utc_now_iso_seconds()
        if KEY_NETWORK_CHECK_DISABLED not in data:
            data[KEY_NETWORK_CHECK_DISABLED] = False
        _atomic_write(_settings_path(), data)


# -----------------------------
# Konventionen für dieses Projekt
# -----------------------------
KEY_NETWORK_CHECK_DISABLED = "network_check_disabled"
KEY_PUBLISHED_DISPLAY = "published_display"
KEY_MANUAL_WIFI_CONFIG = "manual_wifi_config"
KEY_MANUAL_WIFI_CONFIG = "manual_wifi_config"

# Neue Keys für DB-Operationen / Import-Historie
KEY_DATABASE_OPERATIONS = "database_operations"
KEY_IMPORT_HISTORY = "import_history"

DBOP_LAST_BACKUP = "last_backup"
DBOP_LAST_ARCHIVE = "last_archive"
DBOP_LAST_IMPORT = "last_import"

IMPORT_HISTORY_MAX = 20  # letzte N Einträge behalten


def get_network_check_disabled() -> bool:
    return bool(get_setting(KEY_NETWORK_CHECK_DISABLED, False))


def set_network_check_disabled(value: bool) -> None:
    set_setting(KEY_NETWORK_CHECK_DISABLED, bool(value))


def get_published_display() -> Optional[Dict[str, Any]]:
    """
    Struktur:
    {
      "url": "http://192.168.178.31:5000/loads/display",
      "published_at_utc": "2026-04-03T12:58:52",
      "published_by": "admin"
    }
    """
    val = get_setting(KEY_PUBLISHED_DISPLAY, None)
    return val if isinstance(val, dict) else None


def set_published_display(url: str, published_by: str = "unknown") -> None:
    set_setting(
        KEY_PUBLISHED_DISPLAY,
        {
            "url": url,
            "published_at_utc": _utc_now_iso_seconds(),
            "published_by": published_by or "unknown",
        },
    )


def clear_published_display() -> None:
    delete_setting(KEY_PUBLISHED_DISPLAY)


def get_manual_wifi_config() -> Optional[Dict[str, Any]]:
    """
    Struktur:
    {
      "ssid": "E.I.V.",
      "password": "secret",
      "is_open_network": false,
      "updated_at_utc": "2026-04-16T10:15:00"
    }
    """
    val = get_setting(KEY_MANUAL_WIFI_CONFIG, None)
    return val if isinstance(val, dict) else None


def set_manual_wifi_config(
    ssid: str,
    password: Optional[str] = None,
    is_open_network: bool = False,
) -> None:
    set_setting(
        KEY_MANUAL_WIFI_CONFIG,
        {
            "ssid": (ssid or "").strip(),
            "password": password if password is not None else None,
            "is_open_network": bool(is_open_network),
            "updated_at_utc": _utc_now_iso_seconds(),
        },
    )


def clear_manual_wifi_config() -> None:
    delete_setting(KEY_MANUAL_WIFI_CONFIG)


# -----------------------------
# Neue Helper für Backup / Archiv / Import
# -----------------------------

def _get_database_operations(data: Dict[str, Any]) -> Dict[str, Any]:
    ops = data.get(KEY_DATABASE_OPERATIONS, {})
    return ops if isinstance(ops, dict) else {}


def _set_database_operations(data: Dict[str, Any], ops: Dict[str, Any]) -> None:
    data[KEY_DATABASE_OPERATIONS] = ops


def get_database_operations() -> Dict[str, Any]:
    """
    Gibt das dict 'database_operations' zurück oder {}.
    """
    val = get_setting(KEY_DATABASE_OPERATIONS, {})
    return val if isinstance(val, dict) else {}


def get_last_backup() -> Optional[Dict[str, Any]]:
    ops = get_database_operations()
    val = ops.get(DBOP_LAST_BACKUP)
    return _normalize_record_paths(val) if isinstance(val, dict) else None


def get_last_archive() -> Optional[Dict[str, Any]]:
    ops = get_database_operations()
    val = ops.get(DBOP_LAST_ARCHIVE)
    return _normalize_record_paths(val) if isinstance(val, dict) else None


def get_last_import() -> Optional[Dict[str, Any]]:
    ops = get_database_operations()
    val = ops.get(DBOP_LAST_IMPORT)
    return _normalize_record_paths(val) if isinstance(val, dict) else None


def record_database_backup(file_path: str, created_by: str = "admin") -> None:
    """
    Speichert Metadaten zur letzten Sicherung.
    Beispiel:
    database_operations.last_backup = {
      "created_at_utc": "...",
            "file": "data\\backup\\manifest_2026-04-05.db",
      "created_by": "admin"
    }
    """
    with _LOCK:
        data = _load_all()
        ops = _get_database_operations(data)
        ops[DBOP_LAST_BACKUP] = {
            "created_at_utc": _utc_now_iso_seconds(),
            "file": _to_project_relative(file_path),
            "created_by": created_by or "unknown",
        }
        _set_database_operations(data, ops)
        data["_last_updated_utc"] = _utc_now_iso_seconds()
        _atomic_write(_settings_path(), data)


def record_database_archive(year: int, file_path: str, created_by: str = "admin") -> None:
    """
    Speichert Metadaten zum letzten Jahresarchiv.
    Beispiel:
    database_operations.last_archive = {
      "year": 2026,
      "created_at_utc": "...",
            "file": "data\\archive\\manifest_2026.db",
      "created_by": "admin"
    }
    """
    with _LOCK:
        data = _load_all()
        ops = _get_database_operations(data)
        ops[DBOP_LAST_ARCHIVE] = {
            "year": int(year),
            "created_at_utc": _utc_now_iso_seconds(),
            "file": _to_project_relative(file_path),
            "created_by": created_by or "unknown",
        }
        _set_database_operations(data, ops)
        data["_last_updated_utc"] = _utc_now_iso_seconds()
        _atomic_write(_settings_path(), data)


def record_import_result(
    import_id: str,
    status: str,
    mode: str,
    sources: Optional[List[str]] = None,
    log_file: Optional[str] = None,
    created_by: str = "admin",
) -> None:
    """
    Speichert Metadaten zum letzten Import sowie eine kurze Import-Historie.

    database_operations.last_import = {
      "import_id": "...",
      "status": "success|partial_success|failed",
      "mode": "multi_db_merge|year_import|archive_restore",
      "finished_at_utc": "...",
      "created_by": "admin",
      "sources": [...],
      "log_file": "temp/import_log_....txt"
    }

    import_history = [ ... ] (max. IMPORT_HISTORY_MAX Einträge)
    """
    with _LOCK:
        data = _load_all()
        ops = _get_database_operations(data)

        payload = {
            "import_id": import_id,
            "status": status,
            "mode": mode,
            "finished_at_utc": _utc_now_iso_seconds(),
            "created_by": created_by or "unknown",
        }
        if sources:
            payload["sources"] = [_to_project_relative(p) for p in list(sources)]
        if log_file:
            payload["log_file"] = _to_project_relative(log_file)

        ops[DBOP_LAST_IMPORT] = payload
        _set_database_operations(data, ops)

        # History pflegen (optional)
        history_val = data.get(KEY_IMPORT_HISTORY, [])
        history: List[Dict[str, Any]] = history_val if isinstance(history_val, list) else []

        history.append(payload)
        if len(history) > IMPORT_HISTORY_MAX:
            history = history[-IMPORT_HISTORY_MAX:]

        data[KEY_IMPORT_HISTORY] = history
        data["_last_updated_utc"] = _utc_now_iso_seconds()
        _atomic_write(_settings_path(), data)


def get_import_history() -> List[Dict[str, Any]]:
    """
    Gibt die Import-Historie zurück (ggf. leer).
    """
    val = get_setting(KEY_IMPORT_HISTORY, [])
    if not isinstance(val, list):
        return []
    return [_normalize_record_paths(item) if isinstance(item, dict) else item for item in val]