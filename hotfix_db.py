import sqlite3
import os

db_path = 'data/manifest.db'
if not os.path.exists(db_path):
    print(f'Error: {db_path} not found')
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('PRAGMA table_info(billing_config)')
columns = [row[1] for row in cursor.fetchall()]

added = []
if 'waiver_text_skydiver' not in columns:
    cursor.execute('ALTER TABLE billing_config ADD COLUMN waiver_text_skydiver TEXT')
    added.append('waiver_text_skydiver')
if 'waiver_text_tandem' not in columns:
    cursor.execute('ALTER TABLE billing_config ADD COLUMN waiver_text_tandem TEXT')
    added.append('waiver_text_tandem')

conn.commit()
conn.close()

if added:
    print(f'Hotfix executed: Added columns: {", ".join(added)}')
else:
    print('Hotfix executed: Columns already exist')
