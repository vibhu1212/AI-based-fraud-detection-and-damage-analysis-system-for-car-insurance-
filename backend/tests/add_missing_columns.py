#!/usr/bin/env python3
"""Add missing columns to claims table."""
import sqlite3

conn = sqlite3.connect('insurai.db')
cursor = conn.cursor()

try:
    # Check if columns exist
    cursor.execute("PRAGMA table_info(claims)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Add report_pdf_url if missing
    if 'report_pdf_url' not in columns:
        print("Adding report_pdf_url column...")
        cursor.execute("ALTER TABLE claims ADD COLUMN report_pdf_url VARCHAR(700)")
        print("✅ Added report_pdf_url column")
    else:
        print("✅ report_pdf_url column already exists")
    
    # Add extra_data if missing
    if 'extra_data' not in columns:
        print("Adding extra_data column...")
        cursor.execute("ALTER TABLE claims ADD COLUMN extra_data JSON DEFAULT '{}'")
        print("✅ Added extra_data column")
    else:
        print("✅ extra_data column already exists")
    
    conn.commit()
    print("\n✅ Database schema updated successfully!")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    conn.rollback()
finally:
    conn.close()
