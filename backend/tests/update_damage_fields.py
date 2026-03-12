"""
Migration script to update existing damages with intelligent severity and vehicle_part fields.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.damage import DamageDetection
from app.config import settings

def calculate_intelligent_severity(damage):
    """Calculate severity based on bounding box size and confidence."""
    if not all([damage.bbox_x1, damage.bbox_y1, damage.bbox_x2, damage.bbox_y2]):
        return "MODERATE"  # Default if no bbox
    
    bbox_width = damage.bbox_x2 - damage.bbox_x1
    bbox_height = damage.bbox_y2 - damage.bbox_y1
    bbox_area = bbox_width * bbox_height
    confidence = float(damage.confidence) if damage.confidence else 0.5
    
    # Determine severity based on damage size and confidence
    if bbox_area > 50000 and confidence > 0.7:
        return "SEVERE"
    elif bbox_area > 50000 or confidence > 0.8:
        return "MODERATE"
    elif bbox_area > 20000:
        return "MODERATE"
    else:
        return "MINOR"

def extract_vehicle_part(damage):
    """Extract vehicle part from damage type."""
    damage_type_str = str(damage.damage_type).lower()
    
    # Map damage type to vehicle part
    # Since we don't have class names, we'll use damage type as a proxy
    if "glass" in damage_type_str or "windshield" in damage_type_str or "shatter" in damage_type_str:
        return "WINDSHIELD"
    elif "lamp" in damage_type_str or "light" in damage_type_str:
        return "HEADLIGHT_L"
    elif "bumper" in damage_type_str:
        return "FRONT_BUMPER"
    elif "door" in damage_type_str:
        return "DOOR_FL"
    elif "tire" in damage_type_str:
        return "TIRE_FL"
    elif "panel" in damage_type_str:
        return "DOOR_FL"  # Generic panel damage
    elif "dent" in damage_type_str:
        return "DOOR_FL"  # Dents often on doors
    elif "scratch" in damage_type_str:
        return "DOOR_FL"  # Scratches often on doors
    elif "crack" in damage_type_str:
        return "WINDSHIELD"  # Cracks often on glass
    
    return "OTHER"

def update_damage_fields():
    """Update existing damages with intelligent severity and vehicle_part values."""
    
    # Create engine
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Get ALL damages (we'll recalculate those with default values)
        all_damages = db.query(DamageDetection).all()
        
        print(f"Found {len(all_damages)} total damages")
        
        # Filter damages that need updating (NULL or default values)
        damages_to_update = []
        for d in all_damages:
            severity_str = str(d.severity) if d.severity else "NULL"
            part_str = str(d.vehicle_part) if d.vehicle_part else "NULL"
            
            # Check if severity is NULL or default MODERATE
            needs_severity_update = (
                d.severity is None or 
                severity_str == "SeverityLevel.MODERATE"
            )
            
            # Check if vehicle_part is NULL or default OTHER
            needs_part_update = (
                d.vehicle_part is None or 
                part_str == "OTHER"
            )
            
            if needs_severity_update or needs_part_update:
                damages_to_update.append(d)
        
        print(f"Found {len(damages_to_update)} damages needing intelligent recalculation")
        print()
        
        updated_count = 0
        severity_updated = 0
        part_updated = 0
        
        for damage in damages_to_update:
            severity_str = str(damage.severity) if damage.severity else "NULL"
            part_str = str(damage.vehicle_part) if damage.vehicle_part else "NULL"
            
            # Calculate intelligent severity if NULL or MODERATE
            if damage.severity is None or severity_str == "SeverityLevel.MODERATE":
                new_severity = calculate_intelligent_severity(damage)
                damage.severity = new_severity
                severity_updated += 1
                bbox_area = (damage.bbox_x2-damage.bbox_x1)*(damage.bbox_y2-damage.bbox_y1) if all([damage.bbox_x1, damage.bbox_y1, damage.bbox_x2, damage.bbox_y2]) else 0
                print(f"  - Set severity={new_severity} for damage {damage.id[:8]}... (area={bbox_area:.0f}, conf={damage.confidence:.2f})")
            
            # Extract intelligent vehicle_part if NULL or OTHER
            if damage.vehicle_part is None or part_str == "OTHER":
                new_part = extract_vehicle_part(damage)
                damage.vehicle_part = new_part
                part_updated += 1
                print(f"  - Set vehicle_part={new_part} for damage {damage.id[:8]}...")
            
            updated_count += 1
        
        # Commit changes
        db.commit()
        print()
        print(f"✅ Successfully updated {updated_count} damages")
        print(f"   - Severity updated: {severity_updated}")
        print(f"   - Vehicle part updated: {part_updated}")
        
    except Exception as e:
        print(f"❌ Error updating damages: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Updating Damage Fields Migration (Intelligent)")
    print("=" * 60)
    print()
    
    update_damage_fields()
    
    print()
    print("=" * 60)
    print("Migration Complete!")
    print("=" * 60)
