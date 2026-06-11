
import sqlite3
db_path = "data/manifest.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(person)")
cols = cursor.fetchall()
for col in cols:
    print(col[1])
conn.close()

