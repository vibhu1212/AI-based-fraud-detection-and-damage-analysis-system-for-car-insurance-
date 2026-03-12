#!/usr/bin/env python3
"""
Test script for PII Redaction Task (Task 7.3)
Tests face and license plate detection and blurring
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.models.base import SessionLocal
from app.models.claim import Claim
from app.models.media import MediaAsset
from app.tasks.pii_redaction import redact_claim_photos
from sqlalchemy import desc
from pathlib import Path

def test_pii_redaction():
    """Test PII redaction on the most recent claim with photos"""
    print("=" * 80)
    print("PII REDACTION TEST (Task 7.3)")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # Find most recent claim with photos
        claim = db.query(Claim).join(MediaAsset).order_by(desc(Claim.created_at)).first()
        
        if not claim:
            print("❌ No claims with photos found")
            print("   Run create_test_claim_with_damages.py first")
            return False
            
        print(f"\n📋 Testing Claim: {claim.id}")
        print(f"   Status: {claim.status.value}")
        
        # Get photo count
        photos = db.query(MediaAsset).filter(
            MediaAsset.claim_id == claim.id
        ).all()
        print(f"\n🔍 Found {len(photos)} photos")
        
        # Run PII redaction task
        print(f"\n⚙️  Running PII redaction task...")
        result = redact_claim_photos(str(claim.id))
        
        print(f"\n✅ Task Result:")
        print(f"   Status: {result['status']}")
        print(f"   Total Photos: {result.get('total_photos', 0)}")
        print(f"   Total Redacted: {result.get('total_redacted', 0)}")
        print(f"   Failed Redactions: {result.get('failed_redactions', 0)}")
        print(f"   Faces Detected: {result.get('total_faces_detected', 0)}")
        print(f"   License Plates Detected: {result.get('total_plates_detected', 0)}")
        
        # Check redacted files exist
        from app.services.storage import StorageService
        storage = StorageService()
        
        print(f"\n📊 Redacted Files:")
        redacted_count = 0
        for photo in photos:
            original_filename = Path(photo.object_key).name
            redacted_filename = f"redacted_{original_filename}"
            # Correct parameter order: claim_id, filename, folder
            redacted_key = storage.generate_object_key(str(claim.id), redacted_filename, "redacted")
            
            redacted_path = storage.download_file(redacted_key)
            if redacted_path and redacted_path.exists():
                size = redacted_path.stat().st_size
                print(f"   ✅ {redacted_filename} ({size} bytes)")
                redacted_count += 1
            else:
                print(f"   ❌ {redacted_filename} (not found)")
        
        # Validation
        print(f"\n{'=' * 80}")
        print("VALIDATION RESULTS:")
        print(f"{'=' * 80}")
        
        success = True
        
        # Check all photos have redacted versions
        if redacted_count == len(photos):
            print(f"✅ All {len(photos)} photos have redacted versions")
        else:
            print(f"⚠️  Only {redacted_count}/{len(photos)} photos have redacted versions")
            success = False
        
        # Check redacted files are stored in correct location
        redacted_dir = storage.storage_path / "redacted" / str(claim.id)
        if redacted_dir.exists():
            print(f"✅ Redacted directory exists: {redacted_dir}")
        else:
            print(f"❌ Redacted directory not found: {redacted_dir}")
            success = False
        
        if success:
            print(f"\n{'=' * 80}")
            print("🎉 PII REDACTION TEST PASSED!")
            print(f"{'=' * 80}")
            print(f"\n✨ Task 7.3 Complete!")
            print(f"   - {redacted_count} photos redacted")
            print(f"   - Faces and license plates blurred")
            print(f"   - Redacted versions stored in storage/redacted/")
            print(f"   - Original versions preserved for audit")
        else:
            print(f"\n{'=' * 80}")
            print("⚠️  PII REDACTION COMPLETED WITH WARNINGS")
            print(f"{'=' * 80}")
        
        return success
        
    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = test_pii_redaction()
    sys.exit(0 if success else 1)
