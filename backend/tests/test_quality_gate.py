"""
Test script for quality gate validation task.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.tasks.quality_gate import validate_claim_quality
from app.models.base import SessionLocal
from app.models.claim import Claim
from app.models.media import MediaAsset, QualityGateResult

def test_quality_gate():
    """Test quality gate validation"""
    db = SessionLocal()
    
    try:
        # Find a submitted claim with photos
        claim = db.query(Claim).filter(
            Claim.status.in_(["SUBMITTED", "CREATED"])
        ).first()
        
        if not claim:
            print("No claims found to test")
            return
        
        print(f"Testing quality gate for claim: {claim.id}")
        print(f"Current status: {claim.status}")
        print(f"Current P0 locks: {claim.p0_locks}")
        
        # Count photos
        photo_count = db.query(MediaAsset).filter(MediaAsset.claim_id == claim.id).count()
        print(f"Photos found: {photo_count}")
        
        if photo_count == 0:
            print("No photos to validate")
            return
        
        # Run quality gate validation
        print("\nRunning quality gate validation...")
        result = validate_claim_quality(str(claim.id))
        
        print("\nValidation Result:")
        print(f"Status: {result['status']}")
        print(f"All Passed: {result.get('all_passed', False)}")
        print(f"Total Photos: {result.get('total_photos', 0)}")
        
        if 'results' in result:
            print("\nPer-Photo Results:")
            for r in result['results']:
                print(f"  Photo {r['photo_id']} ({r.get('capture_angle', 'unknown')}): {'PASS' if r['passed'] else 'FAIL'}")
                if not r['passed']:
                    if 'failure_reasons' in r:
                        for reason in r['failure_reasons']:
                            print(f"    - {reason}")
                    if 'error' in r:
                        print(f"    ERROR: {r['error']}")
        
        # Check updated claim
        db.refresh(claim)
        print(f"\nUpdated claim status: {claim.status}")
        print(f"Updated P0 locks: {claim.p0_locks}")
        
        # Check quality gate results
        quality_results = db.query(QualityGateResult).filter(
            QualityGateResult.claim_id == claim.id
        ).all()
        print(f"\nQuality gate results stored: {len(quality_results)}")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_quality_gate()
