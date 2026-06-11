import sqlite3

# Pfad zu deiner Datenbank
db_path = r"C:\manifest_fallschirm\data\manifest.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# --------------------------
# 1. Spalten hinzufügen
# --------------------------
try:
    cursor.execute("ALTER TABLE person ADD COLUMN is_aff_teacher INTEGER DEFAULT 0 NOT NULL")
    print("✅ Spalte is_aff_teacher hinzugefügt")
except Exception as e:
    print("⚠️ is_aff_teacher existiert evtl. schon:", e)

try:
    cursor.execute("ALTER TABLE person ADD COLUMN is_aff_student INTEGER DEFAULT 0 NOT NULL")
    print("✅ Spalte is_aff_student hinzugefügt")
except Exception as e:
    print("⚠️ is_aff_student existiert evtl. schon:", e)

# --------------------------
# 2. Status einfügen
# --------------------------
try:
    # AFF-Lehrer
    cursor.execute("""
        INSERT INTO status_definitions 
        (code, label, beschreibung, sort_order, preis_1500, preis_3000, preis_4000, vat_rate, is_active, valid_from)
        SELECT 
        'AFF-LEHRER', 'AFF-Lehrer', 'AFF-Lehrer (Instructor)', 41, 0, 0, 0, 19.00, 1, CURRENT_TIMESTAMP
        WHERE NOT EXISTS (
            SELECT 1 FROM status_definitions WHERE code = 'AFF-LEHRER'
        )
    """)

    # Schüler-AFF-2
    cursor.execute("""
        INSERT INTO status_definitions 
        (code, label, beschreibung, sort_order, preis_1500, preis_3000, preis_4000, vat_rate, is_active, valid_from)
        SELECT 
        'SCHUELER-AFF-2', 'Schüler-AFF-2-Lehrer', 'AFF-Schüler mit 2 Lehrern', 61, 0, 0, 0, 19.00, 1, CURRENT_TIMESTAMP
        WHERE NOT EXISTS (
            SELECT 1 FROM status_definitions WHERE code = 'SCHUELER-AFF-2'
        )
    """)

    # Schüler-AFF-1
    cursor.execute("""
        INSERT INTO status_definitions 
        (code, label, beschreibung, sort_order, preis_1500, preis_3000, preis_4000, vat_rate, is_active, valid_from)
        SELECT 
        'SCHUELER-AFF-1', 'Schüler-AFF-1-Lehrer', 'AFF-Schüler mit 1 Lehrer', 62, 0, 0, 0, 19.00, 1, CURRENT_TIMESTAMP
        WHERE NOT EXISTS (
            SELECT 1 FROM status_definitions WHERE code = 'SCHUELER-AFF-1'
        )
    """)

    print("✅ Status geprüft und ggf. eingefügt")

except Exception as e:
    print("❌ Fehler beim Einfügen der Status:", e)

# --------------------------
# Save & Close
# --------------------------
conn.commit()
conn.close()

print("✅ Migration abgeschlossen")