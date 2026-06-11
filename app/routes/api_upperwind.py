from flask import Blueprint, jsonify
import requests

bp = Blueprint("api_upperwind", __name__, url_prefix="/api")

# ICAO-Station in deiner Region
STATION = "EDAD"

@bp.route("/upperwind")
def upperwind():
    default_payload = {
        "3000": None,
        "5000": None,
        "10000": None,
        "source": "offline",
        "offline": True,
    }

    try:
        url = "https://aviationweather.gov/api/data/windtemp?level=low"
        r = requests.get(url, timeout=2)
        r.raise_for_status()
        data = r.json()

        # Station finden
        station_data = next((s for s in data if s.get("station") == STATION), None)
        if not station_data:
            return jsonify(default_payload)

        # Höhen extrahieren
        result = {
            "3000": station_data.get("3000"),
            "5000": station_data.get("5000"),
            "10000": station_data.get("10000"),
            "source": "aviationweather",
            "offline": False,
        }

        return jsonify(result)

    except Exception:
        # Keine Fehlermeldung → einfach leere Felder
        return jsonify(default_payload)
