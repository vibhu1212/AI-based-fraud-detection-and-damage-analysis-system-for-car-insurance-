"""
Check what damage types are actually in the database
"""
from app.models.base import SessionLocal
from app.models.damage import DamageDetection

db = SessionLocal()
try:
    # Get all damages
    damages = db.query(DamageDetection).all()
    
    print('=' * 60)
    print('Damage Type Analysis')
    print('=' * 60)
    print(f'Total damages: {len(damages)}')
    print()
    
    # Count by damage type
    type_counts = {}
    for d in damages:
        type_str = str(d.damage_type) if d.damage_type else "NULL"
        type_counts[type_str] = type_counts.get(type_str, 0) + 1
    
    print('Damage Type Distribution:')
    for dtype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f'  {dtype}: {count}')
    print()
    
    # Show sample damages with all fields
    print('Sample Damages (first 5):')
    for d in damages[:5]:
        print(f'  ID: {d.id[:8]}...')
        print(f'    damage_type: {d.damage_type}')
        print(f'    severity: {d.severity}')
        print(f'    vehicle_part: {d.vehicle_part}')
        print(f'    confidence: {d.confidence:.2f}')
        print()
        
finally:
    db.close()
