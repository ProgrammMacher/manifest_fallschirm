import sqlite3
conn = sqlite3.connect("data/manifest.db")
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print("Tables:", tables)
if ("person",) in tables or ("persons",) in tables:
    table = "person" if ("person",) in tables else "persons"
    c.execute(f"SELECT id FROM {table} WHERE is_tandem_guest = 1 ORDER BY id ASC LIMIT 1")
    t = c.fetchone()
    c.execute(f"SELECT id FROM {table} WHERE is_tandem_guest = 0 ORDER BY id ASC LIMIT 1")
    s = c.fetchone()
    print(f"TANDEM_ID={t[0] if t else 'None'}")
    print(f"SKYDIVER_ID={s[0] if s else 'None'}")
