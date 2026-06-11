import sqlite3
import os
import io
import sys

# Try to import pypdf, but don't fail immediately if missing
try:
    import pypdf
except ImportError:
    pypdf = None

from app import create_app

db_path = 'data/manifest.db'

def get_ids():
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check columns
    cursor.execute("PRAGMA table_info(person)")
    columns = [row[1] for row in cursor.fetchall()]
    
    has_deleted_at = 'deleted_at' in columns
    has_is_tandem = 'is_tandem_guest' in columns
    
    if not has_is_tandem:
        print("Error: is_tandem_guest column missing from person table")
        sys.exit(1)
        
    def fetch_id(is_tandem):
        query = f"SELECT id FROM person WHERE is_tandem_guest = {is_tandem}"
        if has_deleted_at:
            query += " AND deleted_at IS NULL"
        query += " ORDER BY id LIMIT 1"
        cursor.execute(query)
        row = cursor.fetchone()
        return row[0] if row else None

    tandem_id = fetch_id(1)
    skydiver_id = fetch_id(0)
    
    conn.close()
    return tandem_id, skydiver_id

def extract_text(pdf_bytes):
    text = ""
    if pypdf:
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                text += page.extract_text() or ""
        except Exception as e:
            text = "" # Fallback
    
    if not text:
        # Fallback Byte-Suche
        try:
            text = pdf_bytes.decode('latin-1', errors='ignore')
        except:
            text = ""
    return text

def test_waiver(client, id, is_tandem):
    if id is None:
        return "NOT_FOUND", "N/A"
    
    url = f"/persons/{id}/waiver.pdf"
    response = client.get(url)
    
    status = response.status_code
    content_type = response.content_type
    length = len(response.data)
    
    info = f"URL {url} status={status} content_type={content_type} bytes={length}"
    
    if status != 200:
        return f"FAIL (Status {status})", info
    
    text = extract_text(response.data)
    
    if is_tandem:
        keywords = ['Tandemgast', 'Tandem-Fallschirmsprung', 'Tandemmaster']
        decision = "PASS" if any(k in text for k in keywords) else "FAIL (Missing Tandem keywords)"
    else:
        keywords = ['Fallschirmspringer', 'Lizenznummer', 'Eigenerklärung zu Voraussetzungen']
        decision = "PASS" if any(k in text for k in keywords) else "FAIL (Missing Skydiver keywords)"
        
    return decision, info

def main():
    tandem_id, skydiver_id = get_ids()
    print(f"TANDEM_ID={tandem_id}, SKYDIVER_ID={skydiver_id}")
    
    app = create_app()
    client = app.test_client()
    
    with app.app_context():
        t_decision, t_info = test_waiver(client, tandem_id, True)
        s_decision, s_info = test_waiver(client, skydiver_id, False)
        
        if tandem_id:
            print(t_info)
            print(f"TANDEM_DECISION={t_decision}")
        else:
            print("TANDEM_ID not found in DB.")
            
        if skydiver_id:
            print(s_info)
            print(f"SKYDIVER_DECISION={s_decision}")
        else:
            print("SKYDIVER_ID not found in DB.")

if __name__ == "__main__":
    main()
