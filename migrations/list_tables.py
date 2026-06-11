import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
db_path = PROJECT_ROOT / "data" / "manifest.db"

con = sqlite3.connect(str(db_path))
cur = con.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()

print("Tabellen in der DB:")
for (name,) in tables:
    print("-", name)

con.close()