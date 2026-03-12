"""
Quick script to check inbox status after surveyor inbox fix
"""
from app.models.base import SessionLocal
from app.models.claim import Claim
from app.models.enums import ClaimStatus

db = SessionLocal()
try:
    # Count claims by status
    draft_ready = db.query(Claim).filter(Claim.status == ClaimStatus.DRAFT_READY).count()
    surveyor_review = db.query(Claim).filter(Claim.status == ClaimStatus.SURVEYOR_REVIEW).count()
    
    print('=' * 60)
    print('Claims Status Summary')
    print('=' * 60)
    print(f'  DRAFT_READY: {draft_ready}')
    print(f'  SURVEYOR_REVIEW: {surveyor_review}')
    print(f'  Total in inbox: {draft_ready + surveyor_review}')
    
    # Show some claim details
    claims = db.query(Claim).filter(
        Claim.status.in_([ClaimStatus.DRAFT_READY, ClaimStatus.SURVEYOR_REVIEW])
    ).limit(5).all()
    
    if claims:
        print(f'\nRecent Claims:')
        for c in claims:
            print(f'  - {c.id[:8]}... | Status: {c.status.value} | Policy: {c.policy_id}')
    else:
        print('\n⚠️  No claims found in inbox statuses')
        print('   You may need to create a test claim first.')
        
finally:
    db.close()
