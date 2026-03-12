"""
Check actual damage values to see if they need intelligent recalculation
"""
from app.models.base import SessionLocal
from app.models.damage import DamageDetection

db = SessionLocal()
try:
    # Get all damages
    damages = db.query(DamageDetection).all()
    
    print('=' * 60)
    print('Damage Values Analysis')
    print('=' * 60)
    print(f'Total damages: {len(damages)}')
    print()
    
    # Count by severity
    severity_counts = {}
    for d in damages:
        severity_str = str(d.severity) if d.severity else "NULL"
        severity_counts[severity_str] = severity_counts.get(severity_str, 0) + 1
    
    print('Severity Distribution:')
    for severity, count in sorted(severity_counts.items()):
        print(f'  {severity}: {count}')
    print()
    
    # Count by vehicle part
    part_counts = {}
    for d in damages:
        part_str = str(d.vehicle_part) if d.vehicle_part else "NULL"
        part_counts[part_str] = part_counts.get(part_str, 0) + 1
    
    print('Vehicle Part Distribution:')
    for part, count in sorted(part_counts.items()):
        print(f'  {part}: {count}')
    print()
    
    # Check if all are MODERATE and OTHER
    all_moderate = all(str(d.severity) == "SeverityLevel.MODERATE" for d in damages)
    all_other = all(str(d.vehicle_part) == "OTHER" for d in damages)
    
    if all_moderate and all_other:
        print('⚠️  ALL damages are MODERATE + OTHER!')
        print('   This is the problem the user reported.')
        print('   Need to run intelligent recalculation.')
        print()
        print('   Run: python3 update_damage_fields.py')
    else:
        print('✅ Damages have varied severity and parts')
        
finally:
    db.close()
