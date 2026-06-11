"""
Archive-Export Utilities für Load-Daten.
Extrahiert aus routes/load.py.
"""

from datetime import datetime, date
from sqlalchemy import or_
from app import db
from app.models.load import Load


def parse_archive_period_args(args: dict) -> dict:
    """
    Parst Archive-Filterparameter aus Request-Args.
    Rückgabe: {start_date, end_date, airfield_id, fluggebiet}
    """
    try:
        start_date = datetime.strptime(args.get("start_date", ""), "%Y-%m-%d").date()
    except Exception:
        start_date = None

    try:
        end_date = datetime.strptime(args.get("end_date", ""), "%Y-%m-%d").date()
    except Exception:
        end_date = None

    airfield_id = args.get("airfield_id")
    if airfield_id:
        try:
            airfield_id = int(airfield_id)
        except Exception:
            airfield_id = None

    fluggebiet = args.get("fluggebiet")

    return {
        "start_date": start_date,
        "end_date": end_date,
        "airfield_id": airfield_id,
        "fluggebiet": fluggebiet,
    }


def apply_archive_period_filter(q, archive_period: dict):
    """Wendet Archive-Filter auf Query an."""
    from app.models.load import Load

    start_date = archive_period.get("start_date")
    end_date = archive_period.get("end_date")
    airfield_id = archive_period.get("airfield_id")
    fluggebiet = archive_period.get("fluggebiet")

    if start_date:
        q = q.filter(
            or_(
                db.func.date(Load.actual_time) >= start_date,
                (Load.actual_time.is_(None) & (db.func.date(Load.created_at) >= start_date)),
            )
        )
    if end_date:
        q = q.filter(
            or_(
                db.func.date(Load.actual_time) <= end_date,
                (Load.actual_time.is_(None) & (db.func.date(Load.created_at) <= end_date)),
            )
        )
    if airfield_id:
        q = q.filter(Load.airfield_id == airfield_id)
    # fluggebiet war eine alte Legacy-Spalte und wird hier bewusst ignoriert.

    return q


def build_archive_load_query(args: dict):
    """
    Baut Archive-Query für Loads auf.
    Nutzt parse_archive_period_args + apply_archive_period_filter.
    """
    archive_period = parse_archive_period_args(args)

    q = (
        db.session.query(Load)
        .filter(Load.status == "completed")
    )

    q = apply_archive_period_filter(q, archive_period)
    q = q.order_by(Load.actual_time.desc(), Load.created_at.desc(), Load.airfield_id, Load.load_number)

    return q


def build_archive_entry_rows(loads: list) -> list[dict]:
    """
    Konvertiert Loads zu Export-Reihen für CSV/XLSX/PDF.
    """
    rows = []
    for load in loads:
        for entry in load.entries:
            row = {
                "Flugplatz": load.airfield.name if load.airfield else "",
                "Datum": load.operation_date.strftime("%d.%m.%Y") if load.operation_date else "",
                "FlugNr": load.load_number,
                "Person": entry.person.name if entry.person else entry.pilot_name or "",
                "Status": entry.status,
                "Höhe": entry.height,
                "Flugzeit": f"{entry.flight_duration}" if entry.flight_duration else "",
            }
            rows.append(row)
    return rows


# Hinzugefügt: Unterstützung für Verwendungszweck-Daten

def extract_airfield_and_dates(loads):
    """
    Extrahiert den Flugplatz und die Datumsangaben aus den Loads.
    """
    airfield = loads[0].airfield.name if loads and loads[0].airfield else None
    start_date = min(load.operation_date for load in loads if load.operation_date)
    end_date = max(load.operation_date for load in loads if load.operation_date)
    return airfield, start_date, end_date
