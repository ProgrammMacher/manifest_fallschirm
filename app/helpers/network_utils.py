"""
WLAN-Hilfsfunktionen für QR-Code-Generierung.
Unterstützt das Auslesen von WLAN-Informationen und deren Konvertierung
in das WIFI-QR-Format: WIFI:T:WPA;S:SSID;P:PASSWORD;;
"""
from __future__ import annotations
import subprocess
import re
from typing import Optional, Tuple
import platform
import logging
import time

from app.helpers.app_settings import get_manual_wifi_config

logger = logging.getLogger(__name__)


# Reduziert wiederholte netsh/nmcli-Aufrufe bei Seiten mit Auto-Refresh.
_WLAN_CACHE_TTL_SECONDS = 20.0
_wlan_info_cache_ts = 0.0
_wlan_info_cache_value: Tuple[Optional[str], Optional[str], bool] = (None, None, False)


def _run_command(cmd: list[str], timeout: int = 5) -> subprocess.CompletedProcess[str]:
    """
    Führt externe Kommandos aus.
    Unter Windows ohne sichtbares Konsolenfenster (gegen UI-Flackern bei pythonw/waitress).
    """
    kwargs = {
        "capture_output": True,
        "text": True,
        "timeout": timeout,
    }
    if platform.system() == "Windows":
        # netsh liefert oft OEM-kodierte Ausgabe; cp1252 kann dabei abstuerzen.
        kwargs["encoding"] = "oem"
        kwargs["errors"] = "replace"
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if creationflags:
            kwargs["creationflags"] = creationflags
        startupinfo_cls = getattr(subprocess, "STARTUPINFO", None)
        if startupinfo_cls:
            si = startupinfo_cls()
            si.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
            si.wShowWindow = 0
            kwargs["startupinfo"] = si
    else:
        kwargs["encoding"] = "utf-8"
        kwargs["errors"] = "replace"
    return subprocess.run(cmd, **kwargs)


def _escape_wifi_field(value: str) -> str:
    """
    Escaped Sonderzeichen nach WIFI-QR-Format.
    """
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace(";", r"\;")
    escaped = escaped.replace(",", r"\,")
    escaped = escaped.replace(":", r"\:")
    return escaped


def _is_open_auth_text(auth_text: Optional[str]) -> bool:
    if not auth_text:
        return False
    text = auth_text.strip().lower()
    return "open" in text or "offen" in text


def _parse_windows_profiles() -> set[str]:
    """
    Liest bekannte WLAN-Profile aus.
    """
    profiles: set[str] = set()
    try:
        result = _run_command(["netsh", "wlan", "show", "profiles"], timeout=5)
        if result.returncode != 0:
            return profiles

        for line in result.stdout.splitlines():
            if ":" not in line:
                continue
            left, right = line.split(":", 1)
            left_norm = left.strip().lower()
            # EN: All User Profile, DE: Alle Benutzerprofile
            if "profile" in left_norm:
                name = right.strip()
                if name:
                    profiles.add(name)
    except Exception as exc:
        logger.debug(f"WLAN-Profile konnten nicht gelesen werden: {exc}")
    return profiles


def _get_windows_profile_auth(profile_name: Optional[str]) -> Optional[str]:
    """
    Liefert den Authentifizierungstyp eines gespeicherten WLAN-Profils.
    """
    if not profile_name:
        return None
    try:
        result = _run_command(["netsh", "wlan", "show", "profile", f"name={profile_name}"], timeout=5)
        if result.returncode != 0:
            return None

        for line in result.stdout.splitlines():
            if ":" not in line:
                continue
            left, right = line.split(":", 1)
            left_norm = left.strip().lower()
            # EN: Authentication, DE: Authentifizierung
            if "auth" in left_norm:
                value = right.strip()
                if value:
                    return value
    except Exception as exc:
        logger.debug(f"Authentifizierung fuer Profil '{profile_name}' nicht lesbar: {exc}")
    return None


def _parse_windows_network_scan() -> list[tuple[str, Optional[str]]]:
    """
    Parse von "netsh wlan show networks mode=bssid".
    Ergebnis: Liste aus (ssid, auth_text).
    """
    networks: list[tuple[str, Optional[str]]] = []
    try:
        result = _run_command(["netsh", "wlan", "show", "networks", "mode=bssid"], timeout=5)
        if result.returncode != 0:
            return networks

        current_ssid: Optional[str] = None
        current_auth: Optional[str] = None

        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            ssid_match = re.match(r"^SSID\s+\d+\s*:\s*(.*)$", line, re.IGNORECASE)
            if ssid_match:
                if current_ssid:
                    networks.append((current_ssid, current_auth))
                candidate = ssid_match.group(1).strip()
                current_ssid = candidate if candidate else None
                current_auth = None
                continue

            if current_ssid and ":" in line:
                left, right = line.split(":", 1)
                left_norm = left.strip().lower()
                # EN: Authentication, DE: Authentifizierung
                if "auth" in left_norm:
                    current_auth = right.strip() or None

        if current_ssid:
            networks.append((current_ssid, current_auth))
    except Exception as exc:
        logger.debug(f"WLAN-Scan konnte nicht geparst werden: {exc}")

    # Duplikate entfernen, Reihenfolge beibehalten
    deduped: list[tuple[str, Optional[str]]] = []
    seen: set[str] = set()
    for ssid, auth in networks:
        if ssid in seen:
            continue
        seen.add(ssid)
        deduped.append((ssid, auth))
    return deduped


def get_wlan_info() -> Tuple[Optional[str], Optional[str], bool]:
    """
    Versucht, SSID und Password des verbundenen WLAN-Netzwerks auszulesen.
    
    Returns:
        (ssid, password, is_open_network) tuple
        - ssid: Der Name des verbundenen Netzwerks (kann None sein, wenn nicht verbunden)
        - password: Das Passwort des Netzwerks (kann None sein, wenn nicht verfügbar)
        - is_open_network: True nur fuer offene Netzwerke
    
    Unterstützt:
        - Windows (via netsh)
        - Linux (via nmcli)
        - macOS (via networksetup)
    """
    global _wlan_info_cache_ts, _wlan_info_cache_value

    now = time.monotonic()
    if (now - _wlan_info_cache_ts) <= _WLAN_CACHE_TTL_SECONDS:
        return _wlan_info_cache_value

    system = platform.system()
    
    if system == "Windows":
        value = _get_wlan_info_windows()
        _wlan_info_cache_value = value
        _wlan_info_cache_ts = now
        return value
    elif system == "Linux":
        value = _get_wlan_info_linux()
        _wlan_info_cache_value = value
        _wlan_info_cache_ts = now
        return value
    elif system == "Darwin":  # macOS
        value = _get_wlan_info_macos()
        _wlan_info_cache_value = value
        _wlan_info_cache_ts = now
        return value
    else:
        logger.warning(f"WLAN-Auslesen für {system} nicht unterstützt")
        value = (None, None, False)
        _wlan_info_cache_value = value
        _wlan_info_cache_ts = now
        return value


def _get_wlan_info_windows() -> Tuple[Optional[str], Optional[str], bool]:
    """
    Liest WLAN-Informationen unter Windows aus via netsh.
    
    Versucht zunächst, das verbundene WLAN auszulesen.
    Falls nicht verbunden, werden alle verfügbaren WLANs aufgelistet
    und das erste verwendet (z. B. wenn Server über LAN mit WLAN-Router verbunden ist).
    """
    try:
        # Schritt 1: Versuche verbundenes WLAN zu ermitteln
        result = _run_command(["netsh", "wlan", "show", "interfaces"], timeout=5)
        
        if result.returncode == 0:
            ssid = None
            profile_name = None
            
            # Suche nach SSID und Profile Name
            for line in result.stdout.splitlines():
                ssid_line = re.match(r"^\s*SSID\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
                if ssid_line:
                    # Format: "SSID                 : NetworkName"
                    ssid_candidate = ssid_line.group(1).strip()
                    # Nur nicht-leere SSIDs akzeptieren
                    if ssid_candidate:
                        ssid = ssid_candidate
                    continue

                # Format: "Profile              : ProfileName"
                match = re.search(r"Profile\s*:\s*(.+?)$", line, re.IGNORECASE)
                if match:
                    profile_name = match.group(1).strip()
            
            # Wenn ein verbundenes WLAN gefunden wurde, Passwort auslesen
            if ssid:
                password = _get_wlan_password_windows(profile_name)
                if password:
                    return ssid, password, False

                auth = _get_windows_profile_auth(profile_name or ssid)
                if _is_open_auth_text(auth):
                    return ssid, None, True

                # Gesichertes WLAN ohne Passwort: Trotzdem zurückgeben
                # (build_wifi_qr_data erstellt dann WIFI:T:WPA;S:SSID;;)
                # Der Benutzer wird aufgefordert, das Passwort manuell einzugeben
                logger.info(
                    f"Verbundenes WLAN '{ssid}' ist gesichert, aber Passwort nicht verfügbar. "
                    "QR wird ohne Passwort erstellt. "
                    "Starten Sie die Anwendung als Administrator für den vollständigen WLAN-QR-Code."
                )
                return ssid, None, False
        
        # Schritt 2: Kein verbundenes WLAN gefunden, verfügbare WLANs auflisten
        logger.debug("Kein verbundenes WLAN gefunden, versuche verfügbare WLANs zu finden...")
        return _get_available_wlan_windows()
        
    except Exception as e:
        logger.error(f"Fehler beim Auslesen von Windows WLAN: {e}")
        return None, None, False

def _get_available_wlan_windows() -> Tuple[Optional[str], Optional[str], bool]:
    """
    Listet alle verfügbaren WLAN-Netzwerke auf und wählt das erste aus.
    Versucht dann, das Passwort für dieses Netzwerk auszulesen.
    
    Dies ist nützlich, wenn der Server über LAN verbunden ist,
    aber WLAN-Netzwerke verfügbar sind (z. B. vom gleichen Router).
    """
    try:
        scanned = _parse_windows_network_scan()
        if not scanned:
            logger.debug("Keine verfügbaren WLAN-Netzwerke gefunden")
            return None, None, False

        known_profiles = _parse_windows_profiles()

        # 1) Beste Wahl: gescanntes WLAN mit vorhandenem Profil + Passwort
        for ssid, _auth in scanned:
            if ssid not in known_profiles:
                continue
            password = _get_wlan_password_windows(ssid)
            if password:
                logger.debug(f"Verwende WLAN-Profil mit Passwort: {ssid}")
                return ssid, password, False

        # 2) Fallback: offenes WLAN aus Scanliste
        for ssid, auth in scanned:
            if _is_open_auth_text(auth):
                logger.debug(f"Verwende offenes WLAN aus Scanliste: {ssid}")
                return ssid, None, True

        # 3) Fallback: bekanntes gesichertes Profil (auch ohne Passwort)
        # Dies ist nützlich für LAN-Szenarien, wo der Server über LAN verbunden ist,
        # aber trotzdem WLAN-Profile gespeichert hat
        for ssid, auth in scanned:
            if ssid in known_profiles and not _is_open_auth_text(auth):
                # Versuche nochmal Passwort zu lesen (mit Admin-Rechten fallback)
                password = _get_wlan_password_windows(ssid)
                if password:
                    logger.debug(f"Verwende bekanntes gesichertes WLAN mit Passwort: {ssid}")
                    return ssid, password, False
                else:
                    # Auch ohne Passwort zurückgeben (für LAN-Fallback)
                    logger.info(
                        f"Verwende bekanntes WLAN ohne Passwort: {ssid} "
                        "(Admin-Rechte können das Passwort bereitstellen)"
                    )
                    return ssid, None, False

        # 4) Kein geeignetes WLAN gefunden.
        logger.debug("Kein geeignetes WLAN fuer QR gefunden")
        return None, None, False
        
    except Exception as e:
        logger.error(f"Fehler beim Auflisten von verfügbaren WLANs: {e}")
        return None, None, False


def _get_wlan_password_windows(profile_name: Optional[str]) -> Optional[str]:
    """
    Versucht, das Passwort für ein WLAN-Profil auszulesen.
    
    WICHTIG: Benötigt Administrator-Berechtigung für key=clear Option!
    Ohne Admin-Rechte wird das Passwort nicht zurückgegeben, auch wenn es gespeichert ist.
    
    Args:
        profile_name: Name des WLAN-Profils (SSID oder Profilname)
    
    Returns:
        Das Passwort, oder None wenn nicht verfügbar oder keine Admin-Rechte
    """
    if not profile_name:
        return None
    
    try:
        pwd_result = _run_command(
            ["netsh", "wlan", "show", "profile", f"name={profile_name}", "key=clear"],
            timeout=5,
        )
        
        if pwd_result.returncode == 0:
            found_key_content = False
            for line in pwd_result.stdout.splitlines():
                if "Key Content" in line:
                    found_key_content = True
                    if ":" in line:
                        # Format: "Key Content          : Password123"
                        match = re.search(r"Key Content\s*:\s*(.+?)$", line)
                        if match:
                            password = match.group(1).strip()
                            if password:
                                return password
            
            # Wenn "Key Content" Feld nicht vorhanden -> wahrscheinlich keine Admin-Rechte
            if not found_key_content:
                logger.warning(
                    f"WLAN-Passwort für '{profile_name}' konnte nicht ausgelesen werden: "
                    "key=clear Option benötigt Administrator-Berechtigung. "
                    "Bitte starten Sie die Anwendung als Administrator."
                )
    except Exception as e:
        logger.debug(f"Fehler beim Auslesen des WLAN-Passworts für '{profile_name}': {e}")
    
    return None


def _get_wlan_info_linux() -> Tuple[Optional[str], Optional[str], bool]:
    """
    Liest WLAN-Informationen unter Linux aus via nmcli.
    
    Versucht zunächst, das verbundene WLAN auszulesen.
    Falls nicht verbunden, werden alle verfügbaren WLANs aufgelistet.
    """
    try:
        # Schritt 1: Versuche aktive WLAN-Verbindung zu ermitteln
        result = _run_command(["nmcli", "connection", "show", "--active"], timeout=5)
        
        if result.returncode == 0:
            ssid = None
            
            for line in result.stdout.splitlines():
                if "wireless.ssid" in line:
                    match = re.search(r"wireless\.ssid\s+:\s+(.+?)$", line)
                    if match:
                        ssid = match.group(1).strip()
                        break
            
            if ssid:
                # Verbundenes WLAN gefunden
                password = None  # Normalerweise keine Berechtigung auf Linux
                return ssid, password, False
        
        # Schritt 2: Kein verbundenes WLAN, versuche verfügbare zu finden
        logger.debug("Kein verbundenes WLAN gefunden, versuche verfügbare WLANs zu finden...")
        return _get_available_wlan_linux()
        
    except Exception as e:
        logger.debug(f"Fehler beim Auslesen von Linux WLAN: {e}")
        return None, None, False

def _get_available_wlan_linux() -> Tuple[Optional[str], Optional[str], bool]:
    """
    Listet alle verfügbaren WLAN-Netzwerke unter Linux auf.
    """
    try:
        result = _run_command(["nmcli", "device", "wifi", "list"], timeout=5)
        
        if result.returncode != 0:
            logger.debug("nmcli device wifi list fehlgeschlagen")
            return None, None, False
        
        # Erste SSID aus der Liste auslesen (wird meist zuerst angezeigt = beste Signal)
        lines = result.stdout.splitlines()
        for line in lines[1:]:  # Überspringe Header
            # Spalten sind normalerweise: SSID, BSSID, MODE, CHAN, RATE, SIGNAL, BARS, SECURITY
            parts = line.split()
            if len(parts) > 0:
                ssid = parts[0]
                if ssid and ssid != "--":
                    logger.debug(f"Verwende verfügbares WLAN: {ssid}")
                    # Sicherheit unbekannt: ohne Passwort keinen QR erzwingen.
                    return None, None, False
        
        logger.debug("Keine verfügbaren WLANs gefunden")
        return None, None, False
        
    except Exception as e:
        logger.error(f"Fehler beim Auflisten von verfügbaren WLANs (Linux): {e}")
        return None, None, False

def _get_wlan_info_macos() -> Tuple[Optional[str], Optional[str], bool]:
    """
    Liest WLAN-Informationen unter macOS aus.
    
    Versucht zunächst, das verbundene WLAN auszulesen.
    Falls nicht verbunden, werden alle verfügbaren WLANs aufgelistet.
    """
    try:
        # Schritt 1: SSID des verbundenen Netzwerks auslesen
        result = _run_command(["/usr/sbin/networksetup", "-getairportnetwork", "en0"], timeout=5)
        
        if result.returncode == 0:
            ssid = None
            # Format: "Current Wi-Fi Network: NetworkName"
            match = re.search(r"Current Wi-Fi Network:\s*(.+?)$", result.stdout)
            if match:
                ssid = match.group(1).strip()
            
            if ssid:
                # Verbundenes WLAN gefunden
                password = None  # Normalerweise nicht verfügbar
                return ssid, password, False
        
        # Schritt 2: Kein verbundenes WLAN, versuche verfügbare zu finden
        logger.debug("Kein verbundenes WLAN gefunden, versuche verfügbare WLANs zu finden...")
        return _get_available_wlan_macos()
        
    except Exception as e:
        logger.debug(f"Fehler beim Auslesen von macOS WLAN: {e}")
        return None, None, False

def _get_available_wlan_macos() -> Tuple[Optional[str], Optional[str], bool]:
    """
    Listet alle verfügbaren WLAN-Netzwerke unter macOS auf.
    """
    try:
        # Nutze airport CLI, um verfügbare Netzwerke zu scannen
        result = _run_command(
            ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-s"],
            timeout=5,
        )
        
        if result.returncode != 0:
            logger.debug("airport -s fehlgeschlagen")
            return None, None, False
        
        # Erste SSID aus der Liste auslesen
        lines = result.stdout.splitlines()
        for line in lines[1:]:  # Überspringe Header
            if line.strip():
                # Erste Spalte ist die SSID
                parts = line.split()
                if len(parts) > 0:
                    ssid = parts[0]
                    if ssid:
                        logger.debug(f"Verwende verfügbares WLAN: {ssid}")
                        # Sicherheit unbekannt: ohne Passwort keinen QR erzwingen.
                        return None, None, False
        
        logger.debug("Keine verfügbaren WLANs gefunden")
        return None, None, False
        
    except Exception as e:
        logger.error(f"Fehler beim Auflisten von verfügbaren WLANs (macOS): {e}")
        return None, None, False

def build_wifi_qr_data(
    ssid: str,
    password: Optional[str] = None,
    is_open_network: bool = False,
) -> str:
    """
    Erstellt WIFI-QR-Code-Daten im Format:
    WIFI:T:WPA;S:SSID;P:PASSWORD;;
    oder WIFI:T:nopass;S:SSID;;
    
    Args:
        ssid: Name des Netzwerks
        password: Passwort (erforderlich für WPA-Netzwerke!)
        is_open_network: True nur für offene Netzwerke
    
    Returns:
        WIFI-QR-String, oder leerer String wenn nicht generierbar
    
    Hinweis:
        - WPA-Netzwerke mit Passwort: WIFI:T:WPA;S:SSID;P:PASSWORD;;
        - Offene Netzwerke ohne Passwort: WIFI:T:nopass;S:SSID;;
        - Gesicherte Netzwerke ohne Passwort: WIFI:T:WPA;S:SSID;; (User muss Passwort eingeben)
        - Sonderzeichen werden escaped
    """
    if not ssid:
        return ""

    ssid_escaped = _escape_wifi_field(ssid)

    if password:
        password_escaped = _escape_wifi_field(password)
        return f"WIFI:T:WPA;S:{ssid_escaped};P:{password_escaped};;"

    if is_open_network:
        return f"WIFI:T:nopass;S:{ssid_escaped};;"

    # Gesichertes WLAN ohne Passwort: WPA ohne P-Feld
    # Dies ist nützlich für LAN-Fallback-Szenarien, wo der Server nicht direkt mit dem WLAN verbunden ist
    # aber das WLAN trotzdem kennt. Der Benutzer wird aufgefordert, das Passwort manuell einzugeben
    # (oder die App als Administrator zu starten, um das Passwort auszulesen)
    logger.info(
        f"Erstelle WLAN-QR für '{ssid}' ohne Passwort (LAN-Fallback). "
        "User wird aufgefordert, Passwort manuell einzugeben oder App als Administrator zu starten."
    )
    return f"WIFI:T:WPA;S:{ssid_escaped};;"


def get_effective_wlan_info() -> Tuple[str, Optional[str], Optional[str], bool]:
    """
    Liefert die effektiv genutzten WLAN-Daten.

    Priorität:
    1. Manuell gespeicherte WLAN-Konfiguration
    2. Automatisch erkannte WLAN-Konfiguration

    Returns:
        (source, ssid, password, is_open_network)
        source: "manual" | "auto"
    """
    manual_config = get_manual_wifi_config()
    if manual_config:
        ssid = (manual_config.get("ssid") or "").strip()
        if ssid:
            return (
                "manual",
                ssid,
                manual_config.get("password") or None,
                bool(manual_config.get("is_open_network", False)),
            )

    ssid, password, is_open_network = get_wlan_info()
    return "auto", ssid, password, is_open_network


def get_wifi_qr_string() -> Tuple[bool, str]:
    """
    Hauptfunktion für die Route.
    Versucht, WLAN-Informationen auszulesen und einen WIFI-QR-String zu generieren.
    
    Returns:
        (success, wifi_qr_string) tuple
        - success: True wenn WLAN-Informationen verfügbar sind
        - wifi_qr_string: Die QR-String-Daten (leer wenn fehlgeschlagen)
    """
    _source, ssid, password, is_open_network = get_effective_wlan_info()
    
    if not ssid:
        return False, ""

    # WPA-Netz ohne Passwort: QR wäre für iOS unbrauchbar.
    # wifi_available=True signalisiert dem Template, den Admin-Hinweis anzuzeigen.
    if not password and not is_open_network:
        logger.info(
            f"WLAN '{ssid}' ist gesichert, aber Passwort nicht verfügbar. "
            "QR-Ausgabe unterdrückt – Admin-Berechtigung oder manuelle Eingabe erforderlich."
        )
        return True, ""

    qr_data = build_wifi_qr_data(ssid, password, is_open_network=is_open_network)
    return bool(qr_data), qr_data


def get_all_available_wlans_debug() -> dict:
    """
    Gibt alle erkannten WLAN-Netzwerke mit Debug-Informationen zurück.
    Nur für Admin-Zwecke zu Kontrollzwecken.
    
    Returns:
        Dict mit:
        - "auto": (ssid, password, is_open) von auto-Erkennung
        - "scanned": Liste aller gescannten Netzwerke
        - "profiles": Liste aller gespeicherten Profile
    """
    if platform.system() != "Windows":
        return {"error": "Nur auf Windows verfügbar"}
    
    try:
        source, auto_ssid, auto_password, auto_is_open = get_effective_wlan_info()
        scanned = _parse_windows_network_scan()
        profiles = _parse_windows_profiles()
        manual_config = get_manual_wifi_config()
        
        return {
            "auto": {
                "ssid": auto_ssid,
                "password": auto_password,
                "is_open": auto_is_open,
                "source": source,
            },
            "manual": manual_config,
            "scanned": [
                {
                    "ssid": ssid,
                    "auth": auth,
                }
                for ssid, auth in scanned
            ],
            "profiles": list(profiles),
        }
    except Exception as e:
        logger.error(f"Fehler bei get_all_available_wlans_debug: {e}")
        return {"error": str(e)}


def build_wifi_qr_with_manual_ssid_password(
    ssid: str, password: Optional[str] = None
) -> str:
    """
    Erstellt einen WIFI-QR-Code mit manuell eingegebenen Werten.
    Wird für manuelle Eingaben auf der Connectivity-Seite verwendet.
    
    Args:
        ssid: Name des WLAN-Netzwerks
        password: Passwort des Netzwerks (optional)
    
    Returns:
        QR-String oder leerer String wenn ungültig
    """
    if not ssid or not ssid.strip():
        logger.warning("SSID ist leer")
        return ""
    
    ssid = ssid.strip()
    
    if password and password.strip():
        password = password.strip()
        # Mit Passwort: WPA
        qr = build_wifi_qr_data(ssid, password, is_open_network=False)
        if qr:
            logger.info(f"Manueller WLAN-QR erstellt für SSID: {ssid}")
            return qr
    else:
        # Ohne Passwort: Offenes Netzwerk (nopass)
        ssid_escaped = _escape_wifi_field(ssid)
        qr = f"WIFI:T:nopass;S:{ssid_escaped};;"
        logger.info(f"Manueller WLAN-QR (offen) erstellt für SSID: {ssid}")
        return qr
    
    return ""


def get_network_profile() -> dict:
    """
    Ermittelt das Windows-Netzwerkprofil des aktiven Netzwerks.

    Returns:
        {
          "profile": "Public" | "Private" | "DomainAuthenticated" | "Unknown",
          "is_public": bool,
          "interface_name": str | None,
        }
    """
    if platform.system() != "Windows":
        return {"profile": "Unknown", "is_public": False, "interface_name": None}

    try:
        result = _run_command(
            [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Get-NetConnectionProfile | Select-Object -First 1 Name,NetworkCategory,InterfaceAlias | "
                "ConvertTo-Csv -NoTypeInformation"
            ],
            timeout=6,
        )

        if result.returncode != 0 or not result.stdout.strip():
            logger.warning("get_network_profile: kein Ergebnis von Get-NetConnectionProfile")
            return {"profile": "Unknown", "is_public": False, "interface_name": None}

        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        if len(lines) < 2:
            return {"profile": "Unknown", "is_public": False, "interface_name": None}

        headers = [h.strip('"') for h in lines[0].split(",")]
        values = [v.strip('"') for v in lines[1].split(",")]
        row = dict(zip(headers, values))

        raw_category = row.get("NetworkCategory", "").strip()
        interface_name = row.get("InterfaceAlias", "").strip() or None

        # Windows liefert numerische Werte (0/1/2) oder Strings
        profile_map = {
            "0": "Public",
            "1": "Private",
            "2": "DomainAuthenticated",
            "Public": "Public",
            "Private": "Private",
            "DomainAuthenticated": "DomainAuthenticated",
        }
        profile = profile_map.get(raw_category, "Unknown")

        logger.debug(f"Netzwerkprofil: {profile} (Interface: {interface_name})")
        return {"profile": profile, "is_public": profile == "Public", "interface_name": interface_name}

    except Exception as e:
        logger.warning(f"get_network_profile fehlgeschlagen: {e}")
        return {"profile": "Unknown", "is_public": False, "interface_name": None}
