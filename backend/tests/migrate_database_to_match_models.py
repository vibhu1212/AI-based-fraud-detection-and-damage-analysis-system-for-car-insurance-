"""
Comprehensive database migration to match current models.
Adds all missing columns to existing tables.
"""
import sqlite3
import sys

def get_table_columns(cursor, table_name):
    """Get list of column names for a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]

def migrate_database():
    """Add missing columns to all tables."""
    conn = sqlite3.connect('insurai.db')
    cursor = conn.cursor()
    
    changes_made = []
    errors = []
    
    try:
        print("Analyzing database schema...")
        print()
        
        # ===== CLAIMS TABLE =====
        print("Checking claims table...")
        claims_columns = get_table_columns(cursor, 'claims')
        
        if 'report_pdf_url' not in claims_columns:
            print("  Adding report_pdf_url...")
            cursor.execute("ALTER TABLE claims ADD COLUMN report_pdf_url VARCHAR(700)")
            changes_made.append("✓ Added claims.report_pdf_url")
        
        # ===== DAMAGE_DETECTIONS TABLE =====
        print("Checking damage_detections table...")
        damage_columns = get_table_columns(cursor, 'damage_detections')
        
        # Add surveyor modification fields
        if 'vehicle_part' not in damage_columns:
            print("  Adding vehicle_part...")
            cursor.execute("ALTER TABLE damage_detections ADD COLUMN vehicle_part VARCHAR(120)")
            changes_made.append("✓ Added damage_detections.vehicle_part")
        
        if 'is_ai_generated' not in damage_columns:
            print("  Adding is_ai_generated...")
            cursor.execute("ALTER TABLE damage_detections ADD COLUMN is_ai_generated BOOLEAN DEFAULT 1")
            changes_made.append("✓ Added damage_detections.is_ai_generated")
        
        if 'surveyor_modified' not in damage_columns:
            print("  Adding surveyor_modified...")
            cursor.execute("ALTER TABLE damage_detections ADD COLUMN surveyor_modified BOOLEAN DEFAULT 0")
            changes_made.append("✓ Added damage_detections.surveyor_modified")
        
        if 'surveyor_id' not in damage_columns:
            print("  Adding surveyor_id...")
            cursor.execute("ALTER TABLE damage_detections ADD COLUMN surveyor_id VARCHAR(36)")
            changes_made.append("✓ Added damage_detections.surveyor_id")
        
        if 'cost_override' not in damage_columns:
            print("  Adding cost_override...")
            cursor.execute("ALTER TABLE damage_detections ADD COLUMN cost_override NUMERIC(12, 2)")
            changes_made.append("✓ Added damage_detections.cost_override")
        
        if 'surveyor_notes' not in damage_columns:
            print("  Adding surveyor_notes...")
            cursor.execute("ALTER TABLE damage_detections ADD COLUMN surveyor_notes VARCHAR(1000)")
            changes_made.append("✓ Added damage_detections.surveyor_notes")
        
        # ===== REPORT_DRAFTS TABLE =====
        print("Checking report_drafts table...")
        report_columns = get_table_columns(cursor, 'report_drafts')
        
        if 'report_sections' not in report_columns:
            print("  Adding report_sections...")
            cursor.execute("ALTER TABLE report_drafts ADD COLUMN report_sections JSON")
            changes_made.append("✓ Added report_drafts.report_sections")
        
        if 'surveyor_version' not in report_columns:
            print("  Adding surveyor_version...")
            cursor.execute("ALTER TABLE report_drafts ADD COLUMN surveyor_version JSON")
            changes_made.append("✓ Added report_drafts.surveyor_version")
        
        if 'ai_version' not in report_columns:
            print("  Adding ai_version...")
            cursor.execute("ALTER TABLE report_drafts ADD COLUMN ai_version JSON")
            changes_made.append("✓ Added report_drafts.ai_version")
        
        if 'version' not in report_columns:
            print("  Adding version...")
            cursor.execute("ALTER TABLE report_drafts ADD COLUMN version INTEGER DEFAULT 1")
            changes_made.append("✓ Added report_drafts.version")
        
        if 'surveyor_id' not in report_columns:
            print("  Adding surveyor_id...")
            cursor.execute("ALTER TABLE report_drafts ADD COLUMN surveyor_id VARCHAR(36)")
            changes_made.append("✓ Added report_drafts.surveyor_id")
        
        if 'updated_at' not in report_columns:
            print("  Adding updated_at...")
            cursor.execute("ALTER TABLE report_drafts ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            changes_made.append("✓ Added report_drafts.updated_at")
        
        # Commit all changes
        conn.commit()
        
        print()
        print("="*70)
        print("DATABASE MIGRATION COMPLETE")
        print("="*70)
        print()
        
        if changes_made:
            print(f"✅ Successfully applied {len(changes_made)} changes:")
            for change in changes_made:
                print(f"   {change}")
        else:
            print("✅ No changes needed - database schema is already up to date")
        
        if errors:
            print()
            print(f"⚠️  {len(errors)} warnings:")
            for error in errors:
                print(f"   {error}")
        
        print()
        return True
        
    except Exception as e:
        print()
        print(f"❌ Migration failed: {e}")
        print()
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("="*70)
    print("DATABASE MIGRATION - Sync Schema with Models")
    print("="*70)
    print()
    print("This will add missing columns to match the current model definitions.")
    print("Existing data will be preserved.")
    print()
    
    success = migrate_database()
    
    if success:
        print("="*70)
        print("✅ Migration completed successfully!")
        print("="*70)
    else:
        print("="*70)
        print("❌ Migration failed - please check errors above")
        print("="*70)
    
    sys.exit(0 if success else 1)
