#!/usr/bin/env python3
"""
Test script for Damage Hashing Task (P0 Lock 4)
Tests pHash and ORB descriptor generation for damage regions
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.models.base import SessionLocal
from app.models.claim import Claim
from app.models.damage import DamageDetection
from app.tasks.damage_hashing import generate_damage_hashes
from sqlalchemy import desc

def test_damage_hashing():
    """Test damage hashing on the most recent claim with damages"""
    print("=" * 80)
    print("DAMAGE HASHING TEST (P0 Lock 4)")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # Find most recent claim with damage detections
        claim = db.query(Claim).join(DamageDetection).order_by(desc(Claim.created_at)).first()
        
        if not claim:
            print("❌ No claims with damage detections found")
            print("   Run test_pipeline_4.1_to_4.3.py first to create test data")
            return False
            
        print(f"\n📋 Testing Claim: {claim.id}")
        print(f"   Status: {claim.status.value}")
        print(f"   P0 Locks Before:")
        print(f"      - quality_gate_passed: {claim.p0_locks.get('quality_gate_passed', False)}")
        print(f"      - vin_hash_generated: {claim.p0_locks.get('vin_hash_generated', False)}")
        print(f"      - damage_detected: {claim.p0_locks.get('damage_detected', False)}")
        print(f"      - damage_hash_generated: {claim.p0_locks.get('damage_hash_generated', False)}")
        
        # Get damage count before
        damages_before = db.query(DamageDetection).filter(
            DamageDetection.claim_id == claim.id
        ).all()
        print(f"\n🔍 Found {len(damages_before)} damage detections")
        
        # Check if any already have hashes
        hashed_before = sum(1 for d in damages_before if d.damage_hash_phash is not None)
        print(f"   {hashed_before} already have hashes")
        
        # Run damage hashing task
        print(f"\n⚙️  Running damage hashing task...")
        result = generate_damage_hashes(str(claim.id))
        
        print(f"\n✅ Task Result:")
        print(f"   Status: {result['status']}")
        print(f"   Total Damages: {result.get('total_damages', 0)}")
        print(f"   Total Hashed: {result.get('total_hashed', 0)}")
        print(f"   Failed Hashes: {result.get('failed_hashes', 0)}")
        
        # Refresh claim to see updated P0 locks
        db.refresh(claim)
        
        print(f"\n🔒 P0 Locks After:")
        print(f"      - quality_gate_passed: {claim.p0_locks.get('quality_gate_passed', False)}")
        print(f"      - vin_hash_generated: {claim.p0_locks.get('vin_hash_generated', False)}")
        print(f"      - damage_detected: {claim.p0_locks.get('damage_detected', False)}")
        print(f"      - damage_hash_generated: {claim.p0_locks.get('damage_hash_generated', False)} ✨")
        
        # Check damages after hashing
        damages_after = db.query(DamageDetection).filter(
            DamageDetection.claim_id == claim.id
        ).all()
        
        print(f"\n📊 Damage Hash Details:")
        for i, damage in enumerate(damages_after[:5], 1):  # Show first 5
            print(f"\n   Damage {i}:")
            print(f"      Type: {damage.damage_type.value}")
            print(f"      Confidence: {damage.confidence:.4f}")
            print(f"      BBox: ({damage.bbox_x1}, {damage.bbox_y1}) to ({damage.bbox_x2}, {damage.bbox_y2})")
            print(f"      pHash: {damage.damage_hash_phash if damage.damage_hash_phash else 'None'}")
            if damage.damage_hash_orb:
                print(f"      ORB Keypoints: {damage.damage_hash_orb.get('count', 0)}")
            if damage.relative_coords:
                print(f"      Relative Center: ({damage.relative_coords.get('center_x_rel', 0):.3f}, "
                      f"{damage.relative_coords.get('center_y_rel', 0):.3f})")
        
        if len(damages_after) > 5:
            print(f"\n   ... and {len(damages_after) - 5} more damages")
        
        # Validation
        print(f"\n{'=' * 80}")
        print("VALIDATION RESULTS:")
        print(f"{'=' * 80}")
        
        success = True
        
        # Check P0 lock is set
        if not claim.p0_locks.get('damage_hash_generated', False):
            print("❌ P0 Lock 'damage_hash_generated' NOT set")
            success = False
        else:
            print("✅ P0 Lock 'damage_hash_generated' is set")
        
        # Check all damages have hashes
        hashed_count = sum(1 for d in damages_after if d.damage_hash_phash is not None)
        if hashed_count == len(damages_after):
            print(f"✅ All {len(damages_after)} damages have pHash")
        else:
            print(f"⚠️  Only {hashed_count}/{len(damages_after)} damages have pHash")
            success = False
        
        # Check ORB descriptors
        orb_count = sum(1 for d in damages_after if d.damage_hash_orb is not None)
        if orb_count == len(damages_after):
            print(f"✅ All {len(damages_after)} damages have ORB descriptors")
        else:
            print(f"⚠️  Only {orb_count}/{len(damages_after)} damages have ORB descriptors")
            success = False
        
        # Check relative coordinates
        coords_count = sum(1 for d in damages_after if d.relative_coords is not None)
        if coords_count == len(damages_after):
            print(f"✅ All {len(damages_after)} damages have relative coordinates")
        else:
            print(f"⚠️  Only {coords_count}/{len(damages_after)} damages have relative coordinates")
            success = False
        
        if success:
            print(f"\n{'=' * 80}")
            print("🎉 DAMAGE HASHING TEST PASSED!")
            print(f"{'=' * 80}")
        else:
            print(f"\n{'=' * 80}")
            print("⚠️  DAMAGE HASHING TEST COMPLETED WITH WARNINGS")
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
    success = test_damage_hashing()
    sys.exit(0 if success else 1)
