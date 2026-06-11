"""One-time patch: add fallback logic to D.2 pricing block in load.py"""
import pathlib

file = pathlib.Path("c:/manifest_fallschirm/app/routes/load.py")
content = file.read_text(encoding="utf-8")

# Identify the block by unique start/end landmarks
START = "        # \u2705 D.2: PREISMODELL-FREEZE pro Load (MANUELL)\n"
END_MARKER = "            return redirect(url_for(\"pricing.pricing_matrix\", period_id=pricing_model_id))\n"

start_idx = content.find(START)
if start_idx == -1:
    print("ERROR: Start-Marker nicht gefunden")
    exit(1)

end_idx = content.find(END_MARKER, start_idx)
if end_idx == -1:
    print("ERROR: End-Marker nicht gefunden")
    exit(1)

end_idx += len(END_MARKER)

old_block = content[start_idx:end_idx]
print("Old block gefunden:")
print(repr(old_block[:80]), "...")

new_block = (
    "        # \u2705 D.2: PREISMODELL-FREEZE pro Load (MANUELL)\n"
    "        # ------------------------------------------------------------\n"
    "        pricing_model_id = None\n"
    "        try:\n"
    "            mid = session.get(\"active_pricing_model_id\")\n"
    "            pricing_model_id = int(mid) if mid is not None else None\n"
    "        except Exception:\n"
    "            pricing_model_id = None\n"
    "\n"
    "        # Validierung: existieren Preise f\u00fcr dieses Session-Modell?\n"
    "        if pricing_model_id is not None:\n"
    "            exists_price = (\n"
    "                db.session.query(BillingPrice.id)\n"
    "                .filter(BillingPrice.period_id == pricing_model_id)\n"
    "                .limit(1)\n"
    "                .first()\n"
    "            )\n"
    "            if not exists_price:\n"
    "                pricing_model_id = None\n"
    "\n"
    "        # Fallback: bestes g\u00fcltiges Modell am Datum ermitteln\n"
    "        if pricing_model_id is None:\n"
    "            row = (\n"
    "                db.session.query(BillingPricePeriod.id)\n"
    "                .join(BillingPrice, BillingPrice.period_id == BillingPricePeriod.id)\n"
    "                .filter(BillingPricePeriod.valid_from <= planned_dt.date())\n"
    "                .filter(\n"
    "                    (BillingPricePeriod.valid_to.is_(None)) |\n"
    "                    (BillingPricePeriod.valid_to >= planned_dt.date())\n"
    "                )\n"
    "                .order_by(BillingPricePeriod.valid_from.desc())\n"
    "                .limit(1)\n"
    "                .first()\n"
    "            )\n"
    "            if row:\n"
    "                pricing_model_id = int(row[0])\n"
    "                session[\"active_pricing_model_id\"] = pricing_model_id\n"
    "\n"
    "        if pricing_model_id is None:\n"
    "            flash(\n"
    "                \"Kein aktives Preismodell gesetzt. Bitte zuerst unter \u201ePreismatrix\u201c ein Preismodell aktiv setzen.\",\n"
    "                \"danger\"\n"
    "            )\n"
    "            return redirect(url_for(\"pricing.pricing_matrix\"))\n"
)

new_content = content[:start_idx] + new_block + content[end_idx:]
file.write_text(new_content, encoding="utf-8")
print("Patch erfolgreich angewendet.")
