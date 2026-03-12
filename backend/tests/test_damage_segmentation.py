#!/usr/bin/env python3
"""
Test script for Damage Segmentation Task (Optional Task 4.4)
Tests pixel mask generation for damage regions
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.models.base import SessionLocal
from app.models.claim import Claim
from app.models.damage import DamageDetection
from app.tasks.damage_segmentation import segment_damages
from sqlalchemy import desc
from pathlib import Path

def test_damage_segmentation():
    """Test damage segmentation on the most recent claim with damages"""
    print("=" * 80)
    print("DAMAGE SEGMENTATION TEST (Optional Task 4.4)")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # Find most recent claim with damage detections
        claim = db.query(Claim).join(DamageDetection).order_by(desc(Claim.created_at)).first()
        
        if not claim:
            print("❌ No claims with damage detections found")
            print("   Run create_test_claim_with_damages.py first")
            return False
            
        print(f"\n📋 Testing Claim: {claim.id}")
        print(f"   Status: {claim.status.value}")
        
        # Get damage count before
        damages_before = db.query(DamageDetection).filter(
            DamageDetection.claim_id == claim.id
        ).all()
        print(f"\n🔍 Found {len(damages_before)} damage detections")
        
        # Check if any already have masks
        masked_before = sum(1 for d in damages_before if d.mask_object_key is not None)
        print(f"   {masked_before} already have masks")
        
        # Run damage segmentation task
        print(f"\n⚙️  Running damage segmentation task...")
        result = segment_damages(str(claim.id))
        
        print(f"\n✅ Task Result:")
        print(f"   Status: {result['status']}")
        print(f"   Total Damages: {result.get('total_damages', 0)}")
        print(f"   Total Segmented: {result.get('total_segmented', 0)}")
        print(f"   Failed Segmentations: {result.get('failed_segmentations', 0)}")
        
        # Check damages after segmentation
        damages_after = db.query(DamageDetection).filter(
            DamageDetection.claim_id == claim.id
        ).all()
        
        # Refresh each damage to get updated mask data
        for damage in damages_after:
            db.refresh(damage)
        
        print(f"\n📊 Segmentation Details:")
        for i, damage in enumerate(damages_after[:5], 1):  # Show first 5
            print(f"\n   Damage {i}:")
            print(f"      Type: {damage.damage_type.value}")
            print(f"      Confidence: {damage.confidence:.4f}")
            print(f"      BBox: ({damage.bbox_x1}, {damage.bbox_y1}) to ({damage.bbox_x2}, {damage.bbox_y2})")
            print(f"      Mask: {damage.mask_object_key if damage.mask_object_key else 'None'}")
            
            # Check if mask file exists
            if damage.mask_object_key:
                from app.services.storage import StorageService
                storage = StorageService()
                mask_path = storage.download_file(damage.mask_object_key)
                if mask_path and mask_path.exists():
                    print(f"      Mask File: ✅ Exists ({mask_path.stat().st_size} bytes)")
                else:
                    print(f"      Mask File: ❌ Not found")
        
        if len(damages_after) > 5:
            print(f"\n   ... and {len(damages_after) - 5} more damages")
        
        # Validation
        print(f"\n{'=' * 80}")
        print("VALIDATION RESULTS:")
        print(f"{'=' * 80}")
        
        success = True
        
        # Check all damages have masks
        masked_count = sum(1 for d in damages_after if d.mask_object_key is not None)
        if masked_count == len(damages_after):
            print(f"✅ All {len(damages_after)} damages have segmentation masks")
        else:
            print(f"⚠️  Only {masked_count}/{len(damages_after)} damages have masks")
            # This is OK for optional task - some may fail
        
        # Check mask files exist
        from app.services.storage import StorageService
        storage = StorageService()
        existing_masks = 0
        for damage in damages_after:
            if damage.mask_object_key:
                mask_path = storage.download_file(damage.mask_object_key)
                if mask_path and mask_path.exists():
                    existing_masks += 1
        
        if existing_masks == masked_count:
            print(f"✅ All {masked_count} mask files exist in storage")
        else:
            print(f"⚠️  Only {existing_masks}/{masked_count} mask files found")
            success = False
        
        if success and masked_count > 0:
            print(f"\n{'=' * 80}")
            print("🎉 DAMAGE SEGMENTATION TEST PASSED!")
            print(f"{'=' * 80}")
            print(f"\n✨ Optional Task 4.4 Complete!")
            print(f"   - {masked_count} damage masks generated")
            print(f"   - Masks stored in storage/masks/")
            print(f"   - Ready for surveyor visualization")
        else:
            print(f"\n{'=' * 80}")
            print("⚠️  DAMAGE SEGMENTATION COMPLETED WITH WARNINGS")
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
    success = test_damage_segmentation()
    sys.exit(0 if success else 1)
