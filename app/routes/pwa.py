from __future__ import annotations

from flask import (
    Blueprint,
    render_template,
    jsonify,
    request,
    current_app,
    session,
    abort,
)

import socket
import ipaddress

from app.helpers.app_settings import (
    get_network_check_disabled,
    set_network_check_disabled,
    get_published_display,
    set_published_display,
    clear_published_display,
    get_manual_wifi_config,
    set_manual_wifi_config,
    clear_manual_wifi_config,
)

# ✅ NEU: zentrale Navigation (Sidebar = Kacheln)
from app.routes.navigation import NAV_ITEMS


bp = Blueprint(
    "pwa",
    __name__,
    url_prefix="/pwa",
    template_folder="../templates/pwa",
)


def _is_admin() -> bool:
    return bool(session.get("is_admin"))


def _is_local_request() -> bool:
    remote = (request.remote_addr or "").strip()
    if not remote:
        return False
    try:
        return ipaddress.ip_address(remote).is_loopback
    except ValueError:
        return False


# -------------------------------------------------
# Health
# -------------------------------------------------

@bp.route("/health", methods=["GET"])
def health():
    """
    Minimaler Health-Check für Connect (PWA).
    Muss schnell sein, ohne DB, ohne externe Calls.
    """
    return jsonify({"ok": True}), 200


# -------------------------------------------------
# Connect Info
# -------------------------------------------------

@bp.route("/connect/info", methods=["GET"])
def connect_info():
    """
    Minimaler Connect-Info-Endpoint:
    - liefert eine lokale IP für Mobile-Zugriff (WLAN/Hotspot)
    - liefert Flag, ob Mobile-Zugriff realistisch möglich ist (IP != 127.0.0.1)
    - KEINE externen Calls, KEINE DB
    """
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "127.0.0.1"

    return jsonify(
        {
            "local_ip": local_ip,
            "mobile_reachable": local_ip != "127.0.0.1",
        }
    )


# -------------------------------------------------
# PWA Connectivity UI
# -------------------------------------------------

from app.services.display_service import build_display_qr_url
from app.helpers.network_utils import get_wifi_qr_string, get_wlan_info, get_effective_wlan_info, get_network_profile
from app.helpers.runtime_control import request_shutdown, report_browser_disconnect, touch_activity


@bp.route("/connectivity", methods=["GET"])
def connectivity_ui():
    """
    PWA-Infoseite für mobilen Zugriff.

    Aufgabe dieser Seite:
    - QR-Code und Ziel-URL anzeigen (read-only)
    - ruhig erklären, unter welchen Bedingungen mobiler Zugriff funktioniert
    - KEINE Statusprüfung
    - KEIN Publish-/Lock-Workflow
    - KEINE Warnungen oder Blocker

    Quelle der Wahrheit:
    - build_display_qr_url() aus load.py
    """

    can_manage_connectivity = _is_admin()

    qr_available, qr_url = build_display_qr_url()

    # qr_url ist:
    # - leerer String "", wenn keine geeignete Netzwerkadresse ermittelt werden kann
    # - sonst z. B. "http://192.168.x.x:5000/loads/display"
    wifi_available, wifi_qr_data = get_wifi_qr_string()

    # wifi_qr_data ist:
    # - leerer String "", wenn WLAN-Informationen nicht verfügbar sind
    # - sonst z. B. "WIFI:T:WPA;S:MyNetwork;P:Password123;;"
    
    # Debug-Informationen für Admin (nur erkannte Daten zeigen)
    from app.helpers.network_utils import get_all_available_wlans_debug
    wlan_debug = get_all_available_wlans_debug()
    auto_wlan_ssid, auto_wlan_password, auto_wlan_is_open = get_wlan_info()
    active_wlan_source, active_wlan_ssid, active_wlan_password, active_wlan_is_open = get_effective_wlan_info()
    manual_wlan_config = get_manual_wifi_config()
    network_profile = get_network_profile()

    return render_template(
        "pwa/connectivity.html",
        can_manage_connectivity=can_manage_connectivity,
        qr_url=qr_url,
        wifi_qr_data=wifi_qr_data,
        wifi_available=wifi_available,
        wlan_debug=wlan_debug,
        auto_wlan_ssid=auto_wlan_ssid,
        auto_wlan_password=auto_wlan_password,
        auto_wlan_is_open=auto_wlan_is_open,
        active_wlan_source=active_wlan_source,
        active_wlan_ssid=active_wlan_ssid,
        active_wlan_password=active_wlan_password,
        active_wlan_is_open=active_wlan_is_open,
        manual_wlan_config=manual_wlan_config,
        network_profile=network_profile,
    )


# -------------------------------------------------
# Published QR Status API
# -------------------------------------------------

@bp.route("/publish/status", methods=["GET"])
def publish_status():
    """
    Liefert:
    - published_url (LOCKED)
    - recommended_url (aus connect/info Logik)
    - conflict (published != recommended)
    - network_check_disabled
    """
    pub = get_published_display() or {}

    published_url = (pub.get("url") or "").strip()

    network_check_disabled = get_network_check_disabled()

    return jsonify(
        {
            "published_url": published_url,
            "network_check_disabled": network_check_disabled,
        }
    )


# -------------------------------------------------
# Publish / Unpublish API
# -------------------------------------------------

@bp.route("/publish", methods=["POST"])
def publish():
    """
    Veröffentlicht (LOCKT) den QR-Code.
    """
    payload = request.get_json(silent=True) or {}
    manual_url = (payload.get("url") or "").strip()

    if manual_url:
        set_published_display(manual_url)

    return jsonify({"ok": True}), 200


@bp.route("/publish/clear", methods=["POST"])
def unpublish():
    """
    Widerruft die Veröffentlichung.
    """
    clear_published_display()
    return jsonify({"ok": True}), 200


# -------------------------------------------------
# Admin Toggle Network Check
# -------------------------------------------------

@bp.route("/admin/network-check", methods=["POST"])
def admin_toggle_network_check():
    """
    Admin-only.
    Body JSON: { "disabled": true|false }
    """
    if not _is_admin():
        abort(403)

    payload = request.get_json(silent=True) or {}
    disabled = bool(payload.get("disabled"))

    set_network_check_disabled(disabled)

    return jsonify({"ok": True}), 200


# -------------------------------------------------
# ✅ PWA Home (KACHELN)
# -------------------------------------------------

@bp.route("/")
def pwa_index():
    """
    PWA-Startseite.

    Quelle der Wahrheit:
    - NAV_ITEMS (identisch zur Sidebar)
    """
    tiles = [
        item
        for item in NAV_ITEMS
        if not item.get("admin_only") or session.get("is_admin")
    ]

    return render_template("pwa/home.html", tiles=tiles)


# -------------------------------------------------
# WLAN-API für manuelles Eingeben (Admin-only)
# -------------------------------------------------

@bp.route("/api/wlan/generate-qr", methods=["POST"])
def api_wlan_generate_qr():
    """
    Erstellt einen WLAN-QR-Code mit manuell eingegebenen Werten.
    Nur Admin.
    
    Erwartet JSON:
    {
        "ssid": "NetworkName",
        "password": "OptionalPassword"  // optional
    }
    """
    if not _is_admin():
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.get_json() or {}
    ssid = (data.get("ssid") or "").strip()
    password = (data.get("password") or "").strip() or None
    
    if not ssid:
        return jsonify({"error": "SSID erforderlich"}), 400
    
    from app.helpers.network_utils import build_wifi_qr_with_manual_ssid_password
    qr_data = build_wifi_qr_with_manual_ssid_password(ssid, password)
    
    if not qr_data:
        return jsonify({"error": "QR-Code konnte nicht erstellt werden"}), 400
    
    set_manual_wifi_config(ssid, password=password, is_open_network=not bool(password))

    return jsonify({
        "success": True,
        "ssid": ssid,
        "has_password": bool(password),
        "qr_data": qr_data,
        "saved": True,
    })


@bp.route("/api/wlan/manual-config/clear", methods=["POST"])
def api_wlan_clear_manual_config():
    if not _is_admin():
        return jsonify({"error": "Unauthorized"}), 403

    clear_manual_wifi_config()
    return jsonify({"success": True})


@bp.route("/runtime/heartbeat", methods=["POST"])
def runtime_heartbeat():
    touch_activity()
    return ("", 204)


@bp.route("/runtime/disconnect", methods=["POST"])
def runtime_disconnect():
    # beforeunload/sendBeacon beim Browser-Schließen.
    # Kann auch bei Reload ausgelöst werden; die Watchdog-Logik nutzt daher Grace-Time.
    report_browser_disconnect()
    return ("", 204)


@bp.route("/runtime/shutdown", methods=["POST"])
def runtime_shutdown():
    if not _is_local_request():
        return jsonify({"error": "Shutdown nur lokal am Server erlaubt"}), 403

    request_shutdown("manual shutdown via pwa UI")
    return jsonify(
        {
            "success": True,
            "message": "Anwendung wird beendet. Dieses Fenster kann geschlossen werden.",
        }
    )