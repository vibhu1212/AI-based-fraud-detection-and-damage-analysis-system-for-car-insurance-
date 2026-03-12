"""
Check if damages need migration for severity and vehicle_part fields
"""
from app.models.base import SessionLocal
from app.models.damage import DamageDetection

db = SessionLocal()
try:
    # Count total damages
    total_damages = db.query(DamageDetection).count()
    
    # Count damages with NULL severity or vehicle_part
    null_severity = db.query(DamageDetection).filter(DamageDetection.severity == None).count()
    null_part = db.query(DamageDetection).filter(DamageDetection.vehicle_part == None).count()
    
    print('=' * 60)
    print('Damage Fields Status')
    print('=' * 60)
    print(f'  Total damages: {total_damages}')
    print(f'  Missing severity: {null_severity}')
    print(f'  Missing vehicle_part: {null_part}')
    print()
    
    if null_severity > 0 or null_part > 0:
        print('⚠️  Migration needed!')
        print('   Run: python3 update_damage_fields.py')
    else:
        print('✅ All damages have severity and vehicle_part')
        
        # Show sample damages
        damages = db.query(DamageDetection).limit(5).all()
        if damages:
            print('\nSample Damages:')
            for d in damages:
                print(f'  - {d.id[:8]}... | Severity: {d.severity} | Part: {d.vehicle_part} | Conf: {d.confidence:.2f}')
        
finally:
    db.close()
