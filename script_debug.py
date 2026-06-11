import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db
from app.models.load import Load
from app.models.load_entry import LoadEntry
from sqlalchemy import func

app = create_app()
with app.app_context():
    # Alle unterschiedlichen Load-Status-Werte
    statuses = db.session.query(Load.status, func.count(Load.id)).group_by(Load.status).all()
    print("Load-Statuswerte:")
    for s, c in statuses:
        print(f"  status='{s}': {c} Loads")
    
    # Unbilled LoadEntries - zeige welche Load-Status sie haben
    entries = db.session.query(LoadEntry, Load).join(Load, LoadEntry.load_id == Load.id).filter(LoadEntry.billed == False).all()
    print(f"\nUnbilled LoadEntries: {len(entries)}")
    for le, ld in entries:
        print(f"  Person: {le.person_id}, Load #{ld.load_number}, Load.status={ld.status}, Load.actual_time={ld.actual_time}")
