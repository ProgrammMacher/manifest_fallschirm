import sqlite3
import os

db_path = "data/manifest.db"
if not os.path.exists(db_path):
    print("DB_NOT_FOUND")
    exit()

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

try:
    # Check tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    print(f"Tables: {tables}")
    
    if "invoice" in tables and "person" in tables:
        c.execute("SELECT COUNT(*) FROM invoice")
        print(f"Invoices count: {c.fetchone()[0]}")
        
        c.execute("SELECT * FROM invoice LIMIT 1")
        row = c.fetchone()
        if row:
            print("Invoice columns:", row.keys())
            
        c.execute("SELECT * FROM person LIMIT 1")
        row = c.fetchone()
        if row:
            print("Person columns:", row.keys())
            
        # Try finding ANY invoice with ANY person
        query = """
        SELECT i.id, p.email, i.is_final, i.deleted_at
        FROM invoice i
        JOIN person p ON i.person_id = p.id
        """
        c.execute(query)
        rows = c.fetchall()
        print(f"Found {len(rows)} invoice-person pairs.")
        for r in rows[:5]:
            print(f"ID: {r['id']}, Email: {r['email']}, Final: {r['is_final']}, Deleted: {r['deleted_at']}")

except Exception as e:
    print(f"ERROR: {e}")
finally:
    conn.close()
