"""
Find the claim with 8 OTHER damages that the user is viewing
"""
from app.models.base import SessionLocal
from app.models.damage import DamageDetection
from app.models.enums import DamageType
from sqlalchemy import func

db = SessionLocal()
try:
    # Find claims with exactly 8 damages, all OTHER
    claims = db.query(
        DamageDetection.claim_id,
        func.count(DamageDetection.id).label('damage_count')
    ).group_by(
        DamageDetection.claim_id
    ).having(
        func.count(DamageDetection.id) == 8
    ).all()
    
    print('=' * 60)
    print('Claims with 8 Damages')
    print('=' * 60)
    
    for claim_id, damage_count in claims:
        # Check if all are OTHER
        damages = db.query(DamageDetection).filter(
            DamageDetection.claim_id == claim_id
        ).all()
        
        other_count = sum(1 for d in damages if d.damage_type == DamageType.OTHER)
        
        print(f'\nClaim: {claim_id[:8]}...')
        print(f'  Total damages: {damage_count}')
        print(f'  OTHER damages: {other_count}')
        
        if other_count == 8:
            print(f'  ⚠️  This is likely the claim the user is viewing!')
            print(f'\n  Sample damages:')
            for i, d in enumerate(damages, 1):
                print(f'    {i}. {d.damage_type.value} | {d.severity.value} | {d.vehicle_part} | {d.confidence:.2f}')
        
finally:
    db.close()
