from flask import Blueprint, jsonify
import requests

bp = Blueprint("api_weather", __name__, url_prefix="/api")

# Beispiel: METAR + Wind + Temperatur für EDAD (Dessau)
STATION = "EDAD"

@bp.route("/weather")
def weather():
    default_payload = {
        "temp": None,
        "wind_speed": None,
        "wind_dir": None,
        "flight_rules": None,
        "raw": None,
        "source": "offline",
        "offline": True,
    }

    try:
        # METAR von AVWX (kostenlos, ohne Key für Basic)
        url = f"https://avwx.rest/api/metar/{STATION}?format=json"
        r = requests.get(url, timeout=2)
        r.raise_for_status()
        data = r.json()

        result = {
            "temp": data.get("temperature", {}).get("value"),
            "wind_speed": data.get("wind_speed", {}).get("value"),
            "wind_dir": data.get("wind_direction", {}).get("value"),
            "flight_rules": data.get("flight_rules"),
            "raw": data.get("raw"),
            "source": "avwx",
            "offline": False,
        }

        return jsonify(result)

    except Exception:
        # Offline/Netzwerkfehler sollen die App nicht stören.
        return jsonify(default_payload), 200
