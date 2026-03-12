"""
Fix missing vehicle_part column in damage_detections table
"""
import sqlite3

# Connect to database
conn = sqlite3.connect('backend/insurai.db')
cursor = conn.cursor()

# Check if column exists
cursor.execute("PRAGMA table_info(damage_detections)")
columns = [row[1] for row in cursor.fetchall()]

if 'vehicle_part' not in columns:
    print("Adding vehicle_part column...")
    cursor.execute("""
        ALTER TABLE damage_detections 
        ADD COLUMN vehicle_part VARCHAR(50)
    """)
    conn.commit()
    print("✅ Column added successfully")
else:
    print("✅ Column already exists")

conn.close()
print("\nDone!")
