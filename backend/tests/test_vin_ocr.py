"""
Test script for VIN OCR extraction task.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.tasks.vin_ocr import extract_vin_and_hash
from app.models.base import SessionLocal
from app.models.claim import Claim
from app.models.media import MediaAsset
from app.models.report import AIArtifact

def test_vin_ocr():
    """Test VIN OCR extraction"""
    db = SessionLocal()
    
    try:
        # Find a claim with quality gate passed
        claim = db.query(Claim).filter(
            Claim.status == "ANALYZING"
        ).first()
        
        if not claim:
            print("❌ No claims in ANALYZING status found")
            print("   Run quality gate validation first")
            return
        
        print(f"Testing VIN OCR for claim: {claim.id}")
        print(f"Current status: {claim.status}")
        print(f"Current P0 locks: {claim.p0_locks}")
        
        # Check if VIN photo exists
        vin_photo = db.query(MediaAsset).filter(
            MediaAsset.claim_id == claim.id,
            MediaAsset.capture_angle == "VIN"
        ).first()
        
        if not vin_photo:
            print("❌ No VIN photo found")
            return
        
        print(f"VIN photo: {vin_photo.id}")
        
        # Run VIN OCR extraction
        print("\nRunning VIN OCR extraction...")
        result = extract_vin_and_hash(str(claim.id))
        
        print("\nExtraction Result:")
        print(f"Status: {result['status']}")
        
        if result['status'] == 'completed':
            print(f"VIN: {result['vin']}")
            print(f"VIN Hash: {result['vin_hash'][:16]}...")
            print(f"Confidence: {result['confidence']:.2f}%")
        elif result['status'] == 'failed':
            print(f"Error: {result.get('error')}")
            print(f"Raw Text: {result.get('raw_text')}")
        
        # Check updated claim
        db.refresh(claim)
        print(f"\nUpdated claim:")
        print(f"  VIN Hash: {claim.vin_hash[:16] if claim.vin_hash else 'None'}...")
        print(f"  P0 Locks: {claim.p0_locks}")
        print(f"  VIN Hash Generated: {claim.p0_locks.get('vin_hash_generated')}")
        
        # Check AI artifacts
        artifacts = db.query(AIArtifact).filter(
            AIArtifact.claim_id == claim.id,
            AIArtifact.artifact_type.like('vin_ocr%')
        ).all()
        print(f"\nAI Artifacts stored: {len(artifacts)}")
        for artifact in artifacts:
            print(f"  Type: {artifact.artifact_type}")
            print(f"  Model: {artifact.model_name} v{artifact.model_version}")
            if artifact.artifact_json:
                print(f"  Data: {list(artifact.artifact_json.keys())}")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_vin_ocr()
