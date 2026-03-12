"""
Find a claim that has damages
"""
from app.models.base import SessionLocal
from app.models.claim import Claim
from app.models.damage import DamageDetection
from sqlalchemy import func

db = SessionLocal()
try:
    # Find claims with damages
    claims_with_damages = db.query(
        Claim.id,
        Claim.status,
        func.count(DamageDetection.id).label('damage_count')
    ).join(
        DamageDetection, Claim.id == DamageDetection.claim_id
    ).group_by(
        Claim.id, Claim.status
    ).having(
        func.count(DamageDetection.id) > 0
    ).all()
    
    print('=' * 60)
    print('Claims with Damages')
    print('=' * 60)
    print(f'Found {len(claims_with_damages)} claims with damages')
    print()
    
    for claim_id, status, damage_count in claims_with_damages[:10]:
        print(f'Claim: {claim_id[:8]}... | Status: {status.value} | Damages: {damage_count}')
    
    if claims_with_damages:
        print()
        print('=' * 60)
        print(f'Sample Damages from First Claim')
        print('=' * 60)
        
        first_claim_id = claims_with_damages[0][0]
        damages = db.query(DamageDetection).filter(
            DamageDetection.claim_id == first_claim_id
        ).limit(8).all()
        
        for i, d in enumerate(damages, 1):
            print(f'\nDamage {i}:')
            print(f'  damage_type: {d.damage_type.value if d.damage_type else None}')
            print(f'  severity: {d.severity.value if d.severity else None}')
            print(f'  vehicle_part: {d.vehicle_part}')
            print(f'  confidence: {d.confidence:.2f}')
        
finally:
    db.close()
