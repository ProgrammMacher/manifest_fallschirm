#!/usr/bin/env python3
"""Developer-only local UI for issuing MFS2 licenses."""

from __future__ import annotations

import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from developer_tools.lizenzgenerator.license_signing import generate_license_key, load_private_key


app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
app.config["JSON_SORT_KEYS"] = False


@app.get("/")
def index():
    return render_template("license_generator.html")


@app.post("/api/generate")
def generate():
    data = request.get_json(silent=True) or {}
    customer = str(data.get("customer", "")).strip()
    fingerprint = str(data.get("fingerprint", "")).strip().lower()
    tier = str(data.get("tier", "")).strip()

    if not customer:
        return jsonify({"error": "Kundenname erforderlich"}), 400
    if len(fingerprint) != 64 or any(char not in "0123456789abcdef" for char in fingerprint):
        return jsonify({"error": "Fingerprint muss aus 64 Hexadezimalzeichen bestehen"}), 400
    if tier not in ("3m", "12m", "unlimited"):
        return jsonify({"error": "Ungültige Lizenzstufe"}), 400

    try:
        load_private_key()
        license_key, payload = generate_license_key(
            customer=customer,
            fingerprint=fingerprint,
            tier=tier,
        )
    except Exception:
        app.logger.exception("MFS2 license generation failed")
        return jsonify({"error": "Signierschlüssel fehlt oder kann unter diesem Windows-Benutzer nicht geöffnet werden."}), 500

    expiry = payload.get("exp")
    exp_date = datetime.fromisoformat(expiry).astimezone().strftime("%d.%m.%Y") if expiry else "Unbegrenzt"
    return jsonify({
        "success": True,
        "license_key": license_key,
        "customer": customer,
        "tier": payload["tier"],
        "exp_date": exp_date,
        "fingerprint": fingerprint,
        "generated_at": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
    })


if __name__ == "__main__":
    load_private_key()
    print("MFS2-Lizenzgenerator: http://localhost:5555")
    threading.Timer(0.8, lambda: webbrowser.open("http://127.0.0.1:5555")).start()
    app.run(host="127.0.0.1", port=5555, debug=False)
