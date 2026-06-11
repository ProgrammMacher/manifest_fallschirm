#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simulation_betrieb.py
=====================
Simuliert einen realistischen Fallschirmsprung-Betrieb über mehrere Tage.

Testabdeckung:
  - Admin-Login
  - Personen anlegen (Mitglied, Lehrer, Schüler, Tandemmaster, Tandemgast, Gast)
  - Zusätzliches Flugzeug anlegen
  - Zweiten Flugplatz anlegen (Auswärtslocation)
  - Preismatrix prüfen (existierend / lesen)
  - Loads anlegen über 3 Betriebstage
  - Springer eintragen (verschiedene Status-Kombinationen)
  - Loads abschließen ("durchgeführt")
  - Statistikseite aufrufen
  - Rechnungen anlegen (KEIN E-Mail-Versand)

Aufruf:
  python simulation_betrieb.py

Voraussetzung:
  App muss bereits laufen: http://localhost:5000
  (setup_start_manifest.bat oder start_manifest_prod.bat ausführen)

Hinweis:
  Alle Test-Personen erhalten das Namenspräfix "[SIM]" für einfache
  Identifizierung. Die erzeugten Daten bleiben in der Datenbank
  und können manuell entfernt werden.
"""

import sys
import argparse
import json
import re
import time
import requests
from datetime import date, datetime, timedelta

# ─────────────────────────────────────────────────────────────────
# Konfiguration
# ─────────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:5000"
ADMIN_PASSWORD = "OU74#"          # Aus manifest_launcher.py / app/__init__.py
TIMEOUT = 15
REQUEST_RETRIES = 1
REQUEST_BACKOFF_SECONDS = 1.0
REQUEST_DELAY_SECONDS = 0.15
MAX_REQUESTS = 250
MAX_CONSECUTIVE_ERRORS = 20
TRACE_HTTP = False
MAX_INVOICES = 5
SKIP_BILLING = False
BILLING_ONLY = False
ASCII_OUTPUT = False

# Simulierte Betriebstage: 8, 5 und 2 Tage zurück
OPERATION_DATES = [
    (date.today() - timedelta(days=8)).strftime("%Y-%m-%d"),
    (date.today() - timedelta(days=5)).strftime("%Y-%m-%d"),
    (date.today() - timedelta(days=2)).strftime("%Y-%m-%d"),
]

# ─────────────────────────────────────────────────────────────────
# Globale Ergebnis-Sammlung
# ─────────────────────────────────────────────────────────────────
_results: list[tuple[bool, str, str]] = []   # (ok, category, message)
_created: dict = {
    "persons": [],
    "loads": [],
    "invoices": [],
    "aircraft": [],
    "airfields": [],
}

_http_total_requests = 0
_http_consecutive_errors = 0
_abort_reason: str | None = None



def out(*args, **kwargs):
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    flush = kwargs.get("flush", True)

    text = sep.join(str(a) for a in args) + end
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
    sys.stdout.write(safe_text)
    if flush:
        sys.stdout.flush()


def log(category: str, message: str, ok: bool = True):
    if ASCII_OUTPUT:
        icon = "+" if ok else "x"
    else:
        icon = "✓" if ok else "✗"
    line = f"  [{icon}] {category:20s} {message}"
    out(line)
    _results.append((ok, category, message))


# ─────────────────────────────────────────────────────────────────
# HTTP-Session
# ─────────────────────────────────────────────────────────────────
http = requests.Session()
http.headers.update({
    "User-Agent": "MANIFeST-Simulation/1.0",
    # Serverseitiger Guard: Mail-Versand für Simulations-Requests sperren.
    "X-Manifest-Simulation": "1",
})


# ─────────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────────────────────────────
def check_app_running() -> bool:
    try:
        r = http.get(f"{BASE_URL}/pwa", timeout=5, allow_redirects=True)
        return r.status_code < 500
    except Exception:
        return False


def _failed_response(path: str, error: str) -> requests.Response:
    r = requests.Response()
    r.status_code = 599
    r._content = error.encode("utf-8", errors="ignore")
    r.url = f"{BASE_URL}{path}"
    return r


def _set_abort(reason: str):
    global _abort_reason
    if _abort_reason:
        return
    _abort_reason = reason
    log("Sicherheitsabbruch", reason, ok=False)


def should_abort() -> bool:
    return _abort_reason is not None


def _request(method: str, path: str, **kwargs) -> requests.Response:
    global _http_total_requests, _http_consecutive_errors

    if should_abort():
        return _failed_response(path, _abort_reason or "Abbruch aktiviert")

    if MAX_REQUESTS > 0 and _http_total_requests >= MAX_REQUESTS:
        _set_abort(f"Maximale Request-Anzahl erreicht ({MAX_REQUESTS}).")
        return _failed_response(path, _abort_reason or "Request-Limit erreicht")

    last_error = "Unbekannter Fehler"
    attempts = max(1, REQUEST_RETRIES + 1)
    kwargs.setdefault("allow_redirects", True)

    for attempt in range(1, attempts + 1):
        if should_abort():
            return _failed_response(path, _abort_reason or "Abbruch aktiviert")

        if REQUEST_DELAY_SECONDS > 0:
            time.sleep(REQUEST_DELAY_SECONDS)

        try:
            _http_total_requests += 1
            if TRACE_HTTP:
                out(f"  [HTTP] {method} {path} (Versuch {attempt}/{attempts}, gesamt {_http_total_requests})")
            return http.request(
                method=method,
                url=f"{BASE_URL}{path}",
                timeout=TIMEOUT,
                **kwargs,
            )
        except requests.Timeout:
            _http_consecutive_errors += 1
            last_error = f"Timeout nach {TIMEOUT}s"
            log("HTTP", f"{method} {path} – {last_error} (Versuch {attempt}/{attempts})", ok=False)
        except requests.RequestException as exc:
            _http_consecutive_errors += 1
            last_error = str(exc)
            log("HTTP", f"{method} {path} – Request-Fehler: {last_error} (Versuch {attempt}/{attempts})", ok=False)

        if MAX_CONSECUTIVE_ERRORS > 0 and _http_consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            _set_abort(f"Zu viele aufeinanderfolgende HTTP-Fehler ({_http_consecutive_errors}).")
            return _failed_response(path, _abort_reason or last_error)

        if attempt < attempts:
            time.sleep(REQUEST_BACKOFF_SECONDS)

    return _failed_response(path, last_error)


def extract_id_from_redirect(response: requests.Response) -> int | None:
    """Extrahiert eine numerische ID aus der finalen URL nach Redirect."""
    url = response.url
    m = re.search(r"/(\d+)(?:/|$|\?)", url)
    if m:
        return int(m.group(1))
    return None


def find_id_in_html(html: str, search_text: str, edit_prefix: str) -> int | None:
    """
    Sucht search_text im HTML und gibt die numerische ID aus dem nächsten
    edit_prefix + <id> Link danach zurück.
    Fällt auf den letzten Treffer vor search_text zurück.
    """
    pos = html.find(search_text)
    if pos == -1:
        return None
    # Suche vorwärts ab der Fundstelle
    snippet_after = html[pos:]
    m = re.search(re.escape(edit_prefix) + r"(\d+)", snippet_after)
    if m:
        return int(m.group(1))
    # Rückwärts: letzter Treffer vor der Fundstelle
    matches = re.findall(re.escape(edit_prefix) + r"(\d+)", html[:pos])
    if matches:
        return int(matches[-1])
    return None


def post(path: str, data: dict, follow: bool = True) -> requests.Response:
    r = _request("POST", path, data=data, allow_redirects=follow)
    _track_response_status(r)
    return r


def get(path: str, params: dict | None = None) -> requests.Response:
    r = _request("GET", path, params=params)
    _track_response_status(r)
    return r


def _track_response_status(response: requests.Response):
    global _http_consecutive_errors

    if response.status_code < 400:
        _http_consecutive_errors = 0
        return

    _http_consecutive_errors += 1
    if MAX_CONSECUTIVE_ERRORS > 0 and _http_consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
        _set_abort(
            f"Zu viele aufeinanderfolgende fehlerhafte Antworten ({_http_consecutive_errors}, letzte HTTP {response.status_code})."
        )


def ok_or_redirect(r: requests.Response) -> bool:
    """True wenn HTTP 2xx oder 3xx (Redirect = meist Erfolg in dieser App)."""
    return r.status_code < 400


def flash_ok(html: str, keyword: str = "success") -> bool:
    """Prüft ob ein Flash-Message-Block mit keyword im HTML vorkommt."""
    return keyword in html.lower() or "alert-success" in html.lower()


def load_existing_sim_persons() -> int:
    """Lädt bestehende [SIM]-Personen aus der Personenliste in _created['persons']."""
    loaded: list[dict] = []

    for person in PERSONS:
        full_name = f"{person['first']} {person['last']}"
        response = get("/persons/", params={"search": full_name})
        if response.status_code != 200:
            log("Billing-Vorbereitung", f"Personensuche fehlgeschlagen für {full_name} – HTTP {response.status_code}", ok=False)
            continue

        person_id = find_id_in_html(response.text, full_name, "/persons/edit/")
        if not person_id:
            log("Billing-Vorbereitung", f"[SIM]-Person nicht gefunden: {full_name}", ok=False)
            continue

        loaded.append({"id": person_id, **person})

    _created["persons"] = loaded
    return len(loaded)


# ─────────────────────────────────────────────────────────────────
# SCHRITT 1 – App erreichbar prüfen
# ─────────────────────────────────────────────────────────────────
def step_check_app():
    out("\n═══ SCHRITT 1: App-Erreichbarkeit ═══")
    if check_app_running():
        log("Verbindung", f"App erreichbar unter {BASE_URL}")
        return True
    else:
        log("Verbindung", f"App NICHT erreichbar unter {BASE_URL}", ok=False)
        out("\n  Bitte zuerst die App starten:")
        out("  setup_start_manifest.bat  oder  start_manifest_prod.bat")
        return False


# ─────────────────────────────────────────────────────────────────
# SCHRITT 2 – Admin-Login
# ─────────────────────────────────────────────────────────────────
def step_login():
    out("\n═══ SCHRITT 2: Admin-Login ═══")
    r = post("/admin/login", {"password": ADMIN_PASSWORD})
    if ok_or_redirect(r) and ("admin" in r.url or "Admin" in r.text or "Datenbank" in r.text):
        log("Login", "Als Voll-Admin eingeloggt")
        return True
    # Zweiter Versuch: direkte Prüfung der Session via Loads-Seite
    r2 = get("/loads/")
    if r2.status_code == 200:
        log("Login", "Session aktiv (Loads-Seite zugänglich)")
        return True
    log("Login", f"Login fehlgeschlagen – HTTP {r.status_code}", ok=False)
    return False


# ─────────────────────────────────────────────────────────────────
# SCHRITT 3 – Personen anlegen
# ─────────────────────────────────────────────────────────────────
PERSONS = [
    # (Vorname, Nachname, Gewicht, Rolle-Flags)
    # Flags: member, teacher, student, tandemmaster, tandguest, partner_verein
    {"first": "[SIM] Anna",    "last": "Berger",    "weight": 68, "phone": "01701000001",
     "member": True,  "teacher": True,  "teacher_exp": "2027-06-30",
     "student": False, "tandemmaster": False, "tandem_guest": False},

    {"first": "[SIM] Bernd",   "last": "Schuster",  "weight": 82, "phone": "01701000002",
     "member": True,  "teacher": True,  "teacher_exp": "2026-12-31",
     "student": False, "tandemmaster": False, "tandem_guest": False},

    {"first": "[SIM] Carla",   "last": "Wirth",     "weight": 61, "phone": "01701000003",
     "member": True,  "teacher": False, "teacher_exp": None,
     "student": True,  "tandemmaster": False, "tandem_guest": False},

    {"first": "[SIM] Dieter",  "last": "Koch",      "weight": 88, "phone": "01701000004",
     "member": True,  "teacher": False, "teacher_exp": None,
     "student": True,  "tandemmaster": False, "tandem_guest": False},

    {"first": "[SIM] Eva",     "last": "Müller",    "weight": 70, "phone": "01701000005",
     "member": True,  "teacher": False, "teacher_exp": None,
     "student": False, "tandemmaster": True,  "tandem_guest": False},

    {"first": "[SIM] Frank",   "last": "Hoffmann",  "weight": 79, "phone": "01701000006",
     "member": True,  "teacher": False, "teacher_exp": None,
     "student": False, "tandemmaster": True,  "tandem_guest": False},

    {"first": "[SIM] Gabi",    "last": "Schulz",    "weight": 65, "phone": "01701000007",
     "member": True,  "teacher": False, "teacher_exp": None,
     "student": False, "tandemmaster": False, "tandem_guest": False},

    {"first": "[SIM] Hans",    "last": "Braun",     "weight": 90, "phone": "01701000008",
     "member": True,  "teacher": False, "teacher_exp": None,
     "student": False, "tandemmaster": False, "tandem_guest": False},

    {"first": "[SIM] Ines",    "last": "Wagner",    "weight": 72, "phone": "01701000009",
     "member": True,  "teacher": False, "teacher_exp": None,
     "student": False, "tandemmaster": False, "tandem_guest": False},

    {"first": "[SIM] Jochen",  "last": "Fischer",   "weight": 85, "phone": "01701000010",
     "member": True,  "teacher": False, "teacher_exp": None,
     "student": False, "tandemmaster": False, "tandem_guest": False},

    # Gäste (keine Mitglieder)
    {"first": "[SIM] Karl",    "last": "Tandem",    "weight": 75, "phone": "01701000011",
     "member": False, "teacher": False, "teacher_exp": None,
     "student": False, "tandemmaster": False, "tandem_guest": True},

    {"first": "[SIM] Lisa",    "last": "Tandem",    "weight": 58, "phone": "01701000012",
     "member": False, "teacher": False, "teacher_exp": None,
     "student": False, "tandemmaster": False, "tandem_guest": True},

    {"first": "[SIM] Marc",    "last": "Gast",      "weight": 80, "phone": "01701000013",
     "member": False, "teacher": False, "teacher_exp": None,
     "student": False, "tandemmaster": False, "tandem_guest": False},
]


def step_create_persons():
    out("\n═══ SCHRITT 3: Personen anlegen ═══")
    for p in PERSONS:
        if should_abort():
            break
        form = {
            "first_name":        p["first"],
            "last_name":         p["last"],
            "phone":             p["phone"],
            "email":             "",
            "weight_kg":         str(p["weight"]),
            "height_cm":         "",
            "birthdate":         "",
            "is_member":         "true" if p["member"] else "false",
            "is_partner_verein": "false",
            "is_tandem_guest":   "true" if p["tandem_guest"] else "false",
            "is_tandemmaster":   "true" if p["tandemmaster"] else "false",
            "is_student":        "true" if p["student"] else "false",
            "is_teacher":        "true" if p["teacher"] else "false",
            "teacher_license_expires": p.get("teacher_exp") or "",
            "liability_waiver_given":  "false",
            "liability_waiver_date":   "",
            "street_and_number": "",
            "zip_code":          "",
            "city":              "",
            "license_number":    "",
            "insurance_provider":"",
            "insurance_number":  "",
            "iban":              "",
            "bic":               "",
            "account_holder":    "",
            "emergency_name":    "",
            "emergency_relation":"",
            "emergency_phone":   "",
            "emergency_email":   "",
            "comment":           "Testdaten Simulation",
            "notes":             "",
        }
        r = post("/persons/new", form)
        if ok_or_redirect(r):
            full_name = f"{p['first']} {p['last']}"
            pid = find_id_in_html(r.text, full_name, "/persons/edit/")
            if not pid:
                # Fallback: separate Suche auf Listenseite
                r_list = get("/persons/", params={"search": full_name})
                pid = find_id_in_html(r_list.text, full_name, "/persons/edit/")
            role = "Mitglied" if p["member"] else ("Tandemgast" if p["tandem_guest"] else "Gast")
            if p["teacher"]:
                role = "Lehrer+Mitglied"
            elif p["student"]:
                role = "Schüler+Mitglied"
            elif p["tandemmaster"]:
                role = "Tandemmaster+Mitglied"
            log("Person anlegen", f"{p['first']} {p['last']} ({role}) → ID {pid}")
            if pid:
                _created["persons"].append({"id": pid, **p})
        else:
            log("Person anlegen", f"{p['first']} {p['last']} – HTTP {r.status_code}", ok=False)


# ─────────────────────────────────────────────────────────────────
# SCHRITT 4 – Zusätzliches Flugzeug anlegen
# ─────────────────────────────────────────────────────────────────
def step_create_aircraft():
    out("\n═══ SCHRITT 4: Flugzeug anlegen ═══")
    form = {
        "type":           "Cessna 206",
        "registration":   "D-ESIM",
        "seats":          "6",
        "default_height": "3000",
        "active":         "on",
    }
    r = post("/aircraft/new", form)
    if ok_or_redirect(r):
        # URL-Muster: /aircraft/<id>/edit
        r_list = get("/aircraft/")
        pos = r_list.text.find("D-ESIM")
        aid = None
        if pos >= 0:
            m = re.search(r"/aircraft/(\d+)/edit", r_list.text[pos:])
            if not m:
                m = re.search(r"/aircraft/(\d+)/edit", r_list.text[:pos])
            if m:
                aid = int(m.group(1))
        log("Flugzeug", f"Cessna 206 / D-ESIM → ID {aid}")
        if aid:
            _created["aircraft"].append({"id": aid, "reg": "D-ESIM"})
    else:
        log("Flugzeug", f"Anlage fehlgeschlagen – HTTP {r.status_code}", ok=False)


# ─────────────────────────────────────────────────────────────────
# SCHRITT 5 – Zweiten Flugplatz anlegen (Auswärts-Location)
# ─────────────────────────────────────────────────────────────────
def step_create_airfield():
    out("\n═══ SCHRITT 5: Auswärts-Flugplatz anlegen ═══")
    form = {
        "name":   "[SIM] Auswärts-Flugplatz Testenbach",
        "active": "on",
    }
    r = post("/flugplatz/new", form)
    if ok_or_redirect(r):
        af_name = "[SIM] Auswärts-Flugplatz Testenbach"
        # URL-Muster: /flugplatz/<id>/edit
        r_list = get("/flugplatz/")
        pos = r_list.text.find(af_name)
        fid = None
        if pos >= 0:
            m = re.search(r"/flugplatz/(\d+)/edit", r_list.text[pos:])
            if not m:
                # Rückwärts suchen
                m = re.search(r"/flugplatz/(\d+)/edit", r_list.text[:pos])
            if m:
                fid = int(m.group(1))
        log("Flugplatz", f"Auswärts-Flugplatz → ID {fid}")
        if fid:
            _created["airfields"].append({"id": fid})
    else:
        log("Flugplatz", f"Anlage fehlgeschlagen – HTTP {r.status_code}", ok=False)


# ─────────────────────────────────────────────────────────────────
# SCHRITT 6 – Preismatrix und Stammdaten lesen
# ─────────────────────────────────────────────────────────────────
def step_check_pricing():
    out("\n═══ SCHRITT 6: Preismatrix prüfen ═══")
    r = get("/pricing/")
    if r.status_code == 200:
        log("Preismatrix", "Seite zugänglich (HTTP 200)")
        if "Preisperiode" in r.text or "Preismodell" in r.text or "Standard" in r.text:
            log("Preismatrix", "Preisperioden-Einträge gefunden")
        else:
            log("Preismatrix", "Keine Preisperioden sichtbar – Loads könnten fehlschlagen", ok=False)
    else:
        log("Preismatrix", f"HTTP {r.status_code}", ok=False)


# ─────────────────────────────────────────────────────────────────
# SCHRITT 7 – Bestehende Stammdaten lesen (Flugplatz/Flugzeug IDs)
# ─────────────────────────────────────────────────────────────────
def get_first_active_airfield_and_aircraft() -> tuple[int | None, int | None]:
    """Liest aktive Stammdaten aus den Listenseiten für Flugplätze und Flugzeuge."""
    airfield_id = None
    aircraft_id = None

    # Flugplatz-Liste parsen
    r_af = get("/flugplatz/")
    if r_af.status_code == 200:
        ids = re.findall(r"/flugplatz/(\d+)/edit", r_af.text)
        if ids:
            airfield_id = int(ids[0])

    # Flugzeug-Liste parsen
    r_ac = get("/aircraft/")
    if r_ac.status_code == 200:
        ids = re.findall(r"/aircraft/(\d+)/edit", r_ac.text)
        if ids:
            aircraft_id = int(ids[0])

    return airfield_id, aircraft_id


# ─────────────────────────────────────────────────────────────────
# SCHRITT 8 – Loads anlegen und befüllen
# ─────────────────────────────────────────────────────────────────
def create_load(airfield_id: int, aircraft_id: int, op_date: str, start_time: str) -> int | None:
    """Legt einen neuen Load per POST (manueller Modus) an. Liefert die Load-ID."""
    form = {
        "airfield_id":        str(airfield_id),
        "aircraft_id":        str(aircraft_id),
        "height_m":           "3000",
        "max_payload_kg":     "900",
        "planned_date":       op_date,
        "planned_start_time": start_time,
    }
    r = post("/loads/new", form)
    if ok_or_redirect(r):
        load_id = extract_id_from_redirect(r)
        return load_id
    return None


def save_load_entries(load_id: int, op_date: str, op_time: str, entries: list[dict]) -> bool:
    """
    Speichert Springer-Einträge in einem Load.
    entries: [{"seat": 1, "person_id": 5, "status": "Verein", "height": 3000}, ...]
    """
    form: dict[str, str] = {
        "height_m":        "3000",
        "actual_date":     op_date,
        "actual_time_hm":  op_time,
        "fuel_required":   "0",
        "return_to":       "",
    }
    for e in entries:
        seat = str(e["seat"])
        form[f"seat_{seat}_person"]      = str(e["person_id"])
        form[f"seat_{seat}_status_code"] = e["status"]
        form[f"seat_{seat}_height_m"]    = str(e.get("height", 3000))

    r = post(f"/loads/{load_id}/save", form)
    return ok_or_redirect(r)


def complete_load(load_id: int) -> bool:
    r = post(f"/loads/{load_id}/complete", {"show": "active"})
    return ok_or_redirect(r)


def step_simulate_operations():
    out("\n═══ SCHRITT 7–9: Sprungbetrieb simulieren ═══")

    if should_abort():
        return

    # Stammdaten ermitteln
    airfield_id, aircraft_id = get_first_active_airfield_and_aircraft()
    if not airfield_id or not aircraft_id:
        log("Stammdaten", "Kein aktiver Flugplatz oder Flugzeug gefunden", ok=False)
        return

    log("Stammdaten", f"Verwende Flugplatz-ID {airfield_id}, Flugzeug-ID {aircraft_id}")

    # Personen aus vorangegangenem Schritt
    persons = _created["persons"]
    if not persons:
        log("Personen", "Keine Test-Personen verfügbar – überspringe Load-Simulation", ok=False)
        return

    # Personen nach Rollen aufteilen
    def find(role_key: str, value: bool = True, n: int = 1):
        return [p for p in persons if p.get(role_key) == value][:n]

    members   = find("member", True, 10)
    teachers  = find("teacher", True, 2)
    students  = find("student", True, 2)
    tdmasters = find("tandemmaster", True, 2)
    tdguests  = find("tandem_guest", True, 2)

    def pid(person):
        return person["id"]

    # ── Betriebstag 1: reiner Vereinsbetrieb ──────────────────────
    op_date = OPERATION_DATES[0]
    out(f"\n  ─── Betriebstag 1: {op_date} (Vereinsbetrieb) ───")

    # Load 1.1: 4 Vereinsmitglieder
    if len(members) >= 4:
        lid = create_load(airfield_id, aircraft_id, op_date, "09:00")
        if lid:
            entries = [
                {"seat": 1, "person_id": pid(members[0]), "status": "Verein", "height": 3000},
                {"seat": 2, "person_id": pid(members[1]), "status": "Verein", "height": 3000},
                {"seat": 3, "person_id": pid(members[2]), "status": "Verein", "height": 3000},
                {"seat": 4, "person_id": pid(members[3]), "status": "Verein", "height": 3000},
            ]
            ok = save_load_entries(lid, op_date, "09:00", entries)
            log("Load 1.1", f"ID {lid} – 4× Verein – Eintragen: {'OK' if ok else 'Fehler'}", ok)
            if complete_load(lid):
                log("Load 1.1", f"ID {lid} – Abgeschlossen")
                _created["loads"].append(lid)
        else:
            log("Load 1.1", "Anlage fehlgeschlagen", ok=False)

    # Load 1.2: Lehrer + 2 Schüler (Nahfeld-Regel beachten: Sitze 1,2,3)
    if teachers and len(students) >= 1:
        lid = create_load(airfield_id, aircraft_id, op_date, "10:30")
        if lid:
            entries = [
                {"seat": 1, "person_id": pid(teachers[0]),  "status": "Lehrer",  "height": 3000},
                {"seat": 2, "person_id": pid(students[0]),  "status": "Schüler", "height": 3000},
            ]
            if len(students) >= 2:
                entries.append(
                    {"seat": 3, "person_id": pid(students[1]), "status": "Schüler", "height": 3000}
                )
            ok = save_load_entries(lid, op_date, "10:30", entries)
            log("Load 1.2", f"ID {lid} – Lehrer+Schüler – Eintragen: {'OK' if ok else 'Fehler'}", ok)
            if complete_load(lid):
                log("Load 1.2", f"ID {lid} – Abgeschlossen")
                _created["loads"].append(lid)
        else:
            log("Load 1.2", "Anlage fehlgeschlagen", ok=False)

    # Load 1.3: Tandem (TD + G-TD Paar)
    if tdmasters and tdguests:
        lid = create_load(airfield_id, aircraft_id, op_date, "12:00")
        if lid:
            entries = [
                {"seat": 1, "person_id": pid(tdmasters[0]), "status": "TD",   "height": 3000},
                {"seat": 2, "person_id": pid(tdguests[0]),  "status": "G-TD", "height": 3000},
            ]
            if len(members) >= 5:
                entries.append(
                    {"seat": 3, "person_id": pid(members[4]), "status": "Verein", "height": 3000}
                )
            ok = save_load_entries(lid, op_date, "12:00", entries)
            log("Load 1.3", f"ID {lid} – Tandem + Verein – Eintragen: {'OK' if ok else 'Fehler'}", ok)
            if complete_load(lid):
                log("Load 1.3", f"ID {lid} – Abgeschlossen")
                _created["loads"].append(lid)
        else:
            log("Load 1.3", "Anlage fehlgeschlagen", ok=False)

    # ── Betriebstag 2: Auswärtsgelände ────────────────────────────
    op_date = OPERATION_DATES[1]
    out(f"\n  ─── Betriebstag 2: {op_date} (Gemischter Betrieb) ───")

    # Auswärts-Flugplatz falls angelegt, sonst Heimat
    away_af_id = airfield_id
    if _created["airfields"]:
        away_af_id = _created["airfields"][0]["id"]
        log("Flugplatz", f"Wechsel auf Auswärts-Flugplatz ID {away_af_id}")

    # Load 2.1: Mitglieder + Gast
    if len(members) >= 3:
        lid = create_load(away_af_id, aircraft_id, op_date, "08:30")
        if lid:
            entries = [
                {"seat": 1, "person_id": pid(members[5]), "status": "Verein", "height": 3000},
                {"seat": 2, "person_id": pid(members[6]), "status": "Verein", "height": 3000},
                {"seat": 3, "person_id": pid(members[7]), "status": "Verein", "height": 4000},
            ]
            ok = save_load_entries(lid, op_date, "08:30", entries)
            log("Load 2.1", f"ID {lid} – 3× Verein – {'OK' if ok else 'Fehler'}", ok)
            if complete_load(lid):
                log("Load 2.1", f"ID {lid} – Abgeschlossen")
                _created["loads"].append(lid)
        else:
            log("Load 2.1", "Anlage fehlgeschlagen", ok=False)

    # Load 2.2: Zweites Tandem-Paar (falls zwei TDmaster + zwei Gäste)
    if len(tdmasters) >= 2 and len(tdguests) >= 2:
        lid = create_load(away_af_id, aircraft_id, op_date, "10:00")
        if lid:
            entries = [
                {"seat": 1, "person_id": pid(tdmasters[0]), "status": "TD",   "height": 3000},
                {"seat": 2, "person_id": pid(tdguests[0]),  "status": "G-TD", "height": 3000},
                {"seat": 3, "person_id": pid(tdmasters[1]), "status": "TD",   "height": 3000},
                {"seat": 4, "person_id": pid(tdguests[1]),  "status": "G-TD", "height": 3000},
            ]
            ok = save_load_entries(lid, op_date, "10:00", entries)
            log("Load 2.2", f"ID {lid} – 2× Tandem – {'OK' if ok else 'Fehler'}", ok)
            if complete_load(lid):
                log("Load 2.2", f"ID {lid} – Abgeschlossen")
                _created["loads"].append(lid)
        else:
            log("Load 2.2", "Anlage fehlgeschlagen", ok=False)

    # Load 2.3: Lehrer + Schüler + weitere Vereinsmitglieder
    if teachers and students and len(members) >= 8:
        lid = create_load(away_af_id, aircraft_id, op_date, "11:30")
        if lid:
            entries = [
                {"seat": 1, "person_id": pid(teachers[0]),  "status": "Lehrer",  "height": 3000},
                {"seat": 2, "person_id": pid(students[0]),  "status": "Schüler", "height": 3000},
                {"seat": 3, "person_id": pid(members[8]),   "status": "Verein",  "height": 3000},
            ]
            ok = save_load_entries(lid, op_date, "11:30", entries)
            log("Load 2.3", f"ID {lid} – Lehrer+Schüler+Verein – {'OK' if ok else 'Fehler'}", ok)
            if complete_load(lid):
                log("Load 2.3", f"ID {lid} – Abgeschlossen")
                _created["loads"].append(lid)
        else:
            log("Load 2.3", "Anlage fehlgeschlagen", ok=False)

    # ── Betriebstag 3: Intensiver Tag – viele Loads ───────────────
    op_date = OPERATION_DATES[2]
    out(f"\n  ─── Betriebstag 3: {op_date} (Intensiver Betrieb) ───")

    loads_day3 = [
        ("09:00", [
            (1, members[0], "Verein",  3000),
            (2, members[1], "Verein",  3000),
            (3, members[2], "Verein",  4000),
            (4, members[3], "Verein",  3000),
        ]),
        ("10:30", [
            (1, tdmasters[0] if tdmasters else members[0], "TD" if tdmasters else "Verein", 3000),
            (2, tdguests[0]  if tdguests  else members[1], "G-TD" if tdguests else "Verein", 3000),
            (3, members[4], "Verein", 3000),
            (4, members[5], "Verein", 3000),
        ]),
        ("12:00", [
            (1, teachers[0]  if teachers  else members[0], "Lehrer"  if teachers  else "Verein", 3000),
            (2, students[0]  if students  else members[1], "Schüler" if students  else "Verein", 3000),
            (3, members[6], "Verein", 3000),
        ]),
        ("14:00", [
            (1, members[7], "Verein", 3000),
            (2, members[8], "Verein", 4000),
            (3, members[9] if len(members) >= 10 else members[0], "Verein", 3000),
        ]),
    ]

    for start_time, seats in loads_day3:
        lid = create_load(airfield_id, aircraft_id, op_date, start_time)
        if lid:
            entries = [
                {"seat": seat, "person_id": pid(person), "status": status, "height": height}
                for seat, person, status, height in seats
            ]
            ok = save_load_entries(lid, op_date, start_time, entries)
            log(f"Load 3/{start_time}", f"ID {lid} – {len(entries)} Springer – {'OK' if ok else 'Fehler'}", ok)
            if complete_load(lid):
                log(f"Load 3/{start_time}", f"ID {lid} – Abgeschlossen")
                _created["loads"].append(lid)
        else:
            log(f"Load 3/{start_time}", "Anlage fehlgeschlagen", ok=False)


# ─────────────────────────────────────────────────────────────────
# SCHRITT 10 – Statistik aufrufen
# ─────────────────────────────────────────────────────────────────
def step_check_statistics():
    out("\n═══ SCHRITT 10: Statistik prüfen ═══")

    # Hauptseite Statistik
    r = get("/loads/statistics")
    if r.status_code == 200:
        log("Statistik", "Statistikseite zugänglich (HTTP 200)")
        if "Gesamt" in r.text or "Sprünge" in r.text or "Loads" in r.text:
            log("Statistik", "Inhalt sieht plausibel aus")
        else:
            log("Statistik", "Inhalt unklar (kein erwarteter Begriff)", ok=False)
    else:
        log("Statistik", f"HTTP {r.status_code}", ok=False)

    # Statistik mit Datumsfilter: letzten 10 Tage
    from_date = (date.today() - timedelta(days=10)).strftime("%Y-%m-%d")
    to_date   = date.today().strftime("%Y-%m-%d")
    r2 = get("/loads/statistics", {"from": from_date, "to": to_date})
    if r2.status_code == 200:
        log("Statistik-Filter", f"Zeitraum {from_date} – {to_date}: HTTP 200")
    else:
        log("Statistik-Filter", f"HTTP {r2.status_code}", ok=False)

    # CSV-Export
    r3 = get("/loads/statistics/export.csv", {"from": from_date, "to": to_date})
    if r3.status_code == 200 and len(r3.content) > 10:
        log("Statistik CSV", f"{len(r3.content)} Bytes empfangen")
    else:
        log("Statistik CSV", f"HTTP {r3.status_code} / {len(r3.content)} Bytes", ok=r3.status_code == 200)


# ─────────────────────────────────────────────────────────────────
# SCHRITT 11 – Rechnungen anlegen (KEIN E-Mail-Versand)
# ─────────────────────────────────────────────────────────────────
def step_create_invoices():
    out("\n═══ SCHRITT 11: Rechnungen anlegen ═══")

    members_with_id = [p for p in _created["persons"] if p.get("member")]
    if not members_with_id:
        log("Rechnung", "Keine Mitglieder verfügbar", ok=False)
        return

    invoiced = 0
    for person in members_with_id[:MAX_INVOICES]:
        if should_abort():
            break
        pid = person["id"]
        name = f"{person['first']} {person['last']}"

        # Billing-Übersicht der Person prüfen
        r = get(f"/billing/person/{pid}")
        if r.status_code != 200:
            log("Rechnung", f"{name} – Person-Billing-Seite: HTTP {r.status_code}", ok=False)
            continue

        # Rechnung erstellen
        r2 = post(f"/billing/person/{pid}/create_invoice", {})
        if ok_or_redirect(r2):
            inv_id = extract_id_from_redirect(r2)
            if inv_id and "invoice" in r2.url:
                log("Rechnung", f"{name} → Rechnung-ID {inv_id}")
                _created["invoices"].append(inv_id)
                invoiced += 1
            elif "Keine offenen Sprünge" in r2.text or "warning" in r2.text.lower():
                log("Rechnung", f"{name} – Keine abrechenbaren Sprünge (noch offen/bereits abgerechnet)")
            else:
                log("Rechnung", f"{name} – Ergebnis unklar (URL: {r2.url})")
        else:
            log("Rechnung", f"{name} – HTTP {r2.status_code}", ok=False)

    if invoiced > 0:
        log("Rechnung", f"{invoiced} Rechnungen erfolgreich erstellt (kein E-Mail-Versand)")


# ─────────────────────────────────────────────────────────────────
# SCHRITT 12 – Billing-Übersichten prüfen
# ─────────────────────────────────────────────────────────────────
def step_check_billing():
    out("\n═══ SCHRITT 12: Billing-Übersicht prüfen ═══")

    r = get("/billing/invoices")
    if r.status_code == 200:
        log("Billing", "Rechnungsliste zugänglich (HTTP 200)")
    else:
        log("Billing", f"HTTP {r.status_code}", ok=False)

    r2 = get("/billing/persons")
    if r2.status_code == 200:
        log("Billing", "Personenübersicht zugänglich (HTTP 200)")
    else:
        log("Billing", f"HTTP {r2.status_code}", ok=False)

    r3 = get("/billing/overview")
    if r3.status_code == 200:
        log("Billing", "Übersichtsseite zugänglich (HTTP 200)")
    else:
        log("Billing", f"HTTP {r3.status_code}", ok=False)


# ─────────────────────────────────────────────────────────────────
# ZUSAMMENFASSUNG
# ─────────────────────────────────────────────────────────────────
def print_summary():
    out("\n" + "═" * 60)
    out("  ZUSAMMENFASSUNG")
    out("═" * 60)

    total = len(_results)
    passed = sum(1 for ok, _, _ in _results if ok)
    failed = total - passed

    out(f"\n  Tests gesamt:  {total}")
    out(f"  Bestanden:     {passed}  ✓")
    out(f"  Fehlgeschlagen:{failed}  ✗")

    out(f"\n  Angelegte Personen: {len(_created['persons'])}")
    out(f"  Angelegte Loads:    {len(_created['loads'])}")
    out(f"  Angelegte Rechnungen: {len(_created['invoices'])}")
    out(f"  Angelegte Flugzeuge: {len(_created['aircraft'])}")
    out(f"  Angelegte Flugplätze: {len(_created['airfields'])}")

    if failed:
        out(f"\n  ── Fehlgeschlagene Tests ──")
        for ok, cat, msg in _results:
            if not ok:
                out(f"  [✗] {cat:20s} {msg}")

    out()
    if failed == 0:
        out("  ✓ Alle Tests bestanden – App funktioniert korrekt.")
    elif failed <= 3:
        out("  ⚠ Wenige Fehler – Details oben prüfen.")
    else:
        out("  ✗ Mehrere Fehler – Logs und Konsolenausgabe prüfen.")

    out("\n  Hinweis: Testdaten (Prefix '[SIM]') sind in der DB gespeichert.")
    out("  Sie können manuell über die Admin-Oberfläche entfernt werden.")
    out("═" * 60 + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simuliert den MANIFeST-Betrieb mit robustem HTTP-Handling.")
    parser.add_argument("--base-url", default=BASE_URL, help="Basis-URL der laufenden App (Standard: http://localhost:5000)")
    parser.add_argument("--timeout", type=int, default=TIMEOUT, help="HTTP Timeout pro Request in Sekunden (Standard: 15)")
    parser.add_argument("--retries", type=int, default=REQUEST_RETRIES, help="Zusätzliche HTTP-Retries pro Request (Standard: 1)")
    parser.add_argument("--request-delay", type=float, default=REQUEST_DELAY_SECONDS, help="Pause zwischen Requests in Sekunden (Standard: 0.15)")
    parser.add_argument("--max-requests", type=int, default=MAX_REQUESTS, help="Maximale Anzahl HTTP-Requests vor Sicherheitsabbruch (Standard: 250, 0=unbegrenzt)")
    parser.add_argument("--max-consecutive-errors", type=int, default=MAX_CONSECUTIVE_ERRORS, help="Maximale Anzahl aufeinanderfolgender HTTP-Fehler (Standard: 20, 0=deaktiviert)")
    parser.add_argument("--trace-http", action="store_true", help="Zeigt jeden HTTP-Request inkl. Versuchszähler")
    parser.add_argument("--skip-billing", action="store_true", help="Überspringt Schritte 11/12 (Rechnungen/Billing)")
    parser.add_argument("--billing-only", action="store_true", help="Führt nur Admin-Login sowie Schritte 11/12 auf vorhandenen [SIM]-Daten aus")
    parser.add_argument("--max-invoices", type=int, default=MAX_INVOICES, help="Maximale Anzahl Rechnungen in Schritt 11 (Standard: 5)")
    parser.add_argument("--ascii", action="store_true", help="Nur ASCII-Ausgabe (kein Unicode in Logs)")
    return parser.parse_args()


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
def main():
    global BASE_URL, TIMEOUT, REQUEST_RETRIES, REQUEST_DELAY_SECONDS, MAX_REQUESTS, MAX_CONSECUTIVE_ERRORS, TRACE_HTTP, SKIP_BILLING, BILLING_ONLY, MAX_INVOICES, ASCII_OUTPUT

    args = parse_args()
    BASE_URL = args.base_url.rstrip("/")
    TIMEOUT = max(2, int(args.timeout))
    REQUEST_RETRIES = max(0, int(args.retries))
    REQUEST_DELAY_SECONDS = max(0.0, float(args.request_delay))
    MAX_REQUESTS = max(0, int(args.max_requests))
    MAX_CONSECUTIVE_ERRORS = max(0, int(args.max_consecutive_errors))
    TRACE_HTTP = bool(args.trace_http)
    SKIP_BILLING = bool(args.skip_billing)
    BILLING_ONLY = bool(args.billing_only)
    MAX_INVOICES = max(0, int(args.max_invoices))
    stdout_encoding = (getattr(sys.stdout, "encoding", "") or "").lower()
    auto_ascii = "utf" not in stdout_encoding
    ASCII_OUTPUT = bool(args.ascii or auto_ascii)

    out()
    out("╔══════════════════════════════════════════════════════════╗")
    out("║   MANIFeST OU – Sprungbetrieb-Simulation                 ║")
    out(f"║   Datum: {datetime.now().strftime('%d.%m.%Y %H:%M')}                              ║")
    out("╚══════════════════════════════════════════════════════════╝")
    out(f"  URL: {BASE_URL} | Timeout: {TIMEOUT}s | Retries: {REQUEST_RETRIES} | Delay: {REQUEST_DELAY_SECONDS:.2f}s")
    out(f"  Schutz: max_requests={MAX_REQUESTS} | max_consecutive_errors={MAX_CONSECUTIVE_ERRORS}")
    if SKIP_BILLING:
        out("  Hinweis: Billing-Schritte (11/12) werden übersprungen (--skip-billing).")
    if BILLING_ONLY:
        out("  Hinweis: Es werden nur Billing-Schritte auf vorhandenen [SIM]-Daten ausgeführt (--billing-only).")

    if not step_check_app():
        sys.exit(1)

    if not step_login():
        out("\n  Simulation abgebrochen – Admin-Login fehlgeschlagen.")
        sys.exit(1)

    if BILLING_ONLY:
        loaded = load_existing_sim_persons()
        if loaded == 0:
            log("Billing-Vorbereitung", "Keine vorhandenen [SIM]-Personen gefunden", ok=False)
            print_summary()
            sys.exit(1)

        log("Billing-Vorbereitung", f"{loaded} vorhandene [SIM]-Personen geladen")
        step_create_invoices()
        if should_abort():
            print_summary()
            sys.exit(1)
        step_check_billing()
        print_summary()
        return

    step_create_persons()
    if should_abort():
        print_summary()
        sys.exit(1)
    step_create_aircraft()
    if should_abort():
        print_summary()
        sys.exit(1)
    step_create_airfield()
    if should_abort():
        print_summary()
        sys.exit(1)
    step_check_pricing()
    if should_abort():
        print_summary()
        sys.exit(1)
    step_simulate_operations()
    if should_abort():
        print_summary()
        sys.exit(1)
    step_check_statistics()
    if should_abort():
        print_summary()
        sys.exit(1)
    if SKIP_BILLING:
        log("Billing", "Schritte 11/12 übersprungen (CLI-Option --skip-billing)")
    else:
        step_create_invoices()
        step_check_billing()
    print_summary()


if __name__ == "__main__":
    main()
