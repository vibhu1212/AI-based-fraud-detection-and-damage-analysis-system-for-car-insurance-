"""
Test what the API actually returns for damages
"""
import requests
import json

# Get a claim ID from the database first
from app.models.base import SessionLocal
from app.models.claim import Claim
from app.models.enums import ClaimStatus

db = SessionLocal()
try:
    # Get a claim in SURVEYOR_REVIEW status
    claim = db.query(Claim).filter(
        Claim.status == ClaimStatus.SURVEYOR_REVIEW
    ).first()
    
    if not claim:
        print("No claims found in SURVEYOR_REVIEW status")
        exit(1)
    
    claim_id = claim.id
    print(f"Testing API for claim: {claim_id}")
    print()
    
finally:
    db.close()

# Now test the API
# Note: You'll need a valid surveyor token
# For now, let's just show what the database has

from app.models.damage import DamageDetection

db = SessionLocal()
try:
    damages = db.query(DamageDetection).filter(
        DamageDetection.claim_id == claim_id
    ).all()
    
    print(f"Found {len(damages)} damages for claim {claim_id}")
    print()
    
    for i, d in enumerate(damages[:5], 1):
        print(f"Damage {i}:")
        print(f"  damage_type: {d.damage_type} -> {d.damage_type.value if d.damage_type else None}")
        print(f"  severity: {d.severity} -> {d.severity.value if d.severity else None}")
        print(f"  vehicle_part: {d.vehicle_part}")
        print(f"  confidence: {d.confidence}")
        print()
        
finally:
    db.close()
