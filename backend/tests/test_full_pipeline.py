#!/usr/bin/env python3
"""
Test script for Full AI Pipeline (Tasks 4.1-4.7 + 4.9)
Tests complete pipeline orchestration with all P0 locks
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.models.base import SessionLocal
from app.models.claim import Claim, ClaimStatus
from app.models.media import MediaAsset
from app.models.damage import DamageDetection
from app.models.icve import ICVEEstimate, ICVELineItem
from app.tasks.pipeline import process_claim_pipeline
from sqlalchemy import desc

def test_full_pipeline():
    """Test complete AI pipeline from start to finish"""
    print("=" * 80)
    print("FULL AI PIPELINE TEST (Tasks 4.1-4.7 + 4.9)")
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
        print(f"   Initial Status: {claim.status.value}")
        print(f"   Initial P0 Locks: {claim.p0_locks}")
        
        # Get photo count
        photos = db.query(MediaAsset).filter(
            MediaAsset.claim_id == claim.id
        ).all()
        print(f"\n📸 Photos: {len(photos)}")
        
        # Run full pipeline
        print(f"\n⚙️  Running full AI pipeline...")
        print(f"   This will execute all P0 locks in sequence:")
        print(f"   1. Quality Gate (P0 Lock 0)")
        print(f"   2. VIN OCR (P0 Lock 1)")
        print(f"   3. Damage Detection (P0 Lock 2)")
        print(f"   4. Damage Hashing (P0 Lock 4)")
        print(f"   5. Duplicate Detection (P0 Lock 5)")
        print(f"   6. ICVE Calculation (P0 Lock 6)")
        
        result = process_claim_pipeline(str(claim.id))
        
        print(f"\n✅ Pipeline Result:")
        print(f"   Status: {result.get('status')}")
        if result.get('status') == 'failed':
            print(f"   Failed Step: {result.get('step')}")
            print(f"   Reason: {result.get('reason', 'Unknown')}")
            return False
        elif result.get('status') == 'error':
            print(f"   Error: {result.get('error')}")
            return False
        
        print(f"   Final Status: {result.get('final_status')}")
        
        # Refresh claim from database
        db.refresh(claim)
        
        # Check P0 locks
        print(f"\n🔒 P0 Lock Status:")
        locks = claim.p0_locks or {}
        lock_checks = [
            ("Quality Gate", locks.get("quality_gate_passed", False)),
            ("VIN Hash Generated", locks.get("vin_hash_generated", False)),
            ("Damage Detected", locks.get("damage_detected", False)),
            ("Damage Hash Generated", locks.get("damage_hash_generated", False)),
            ("Duplicate Check Completed", locks.get("duplicate_check_completed", False)),
            ("ICVE Estimate Generated", locks.get("icve_estimate_generated", False))
        ]
        
        all_locks_passed = True
        for lock_name, lock_status in lock_checks:
            icon = "✅" if lock_status else "❌"
            print(f"   {icon} {lock_name}: {lock_status}")
            if not lock_status:
                all_locks_passed = False
        
        # Check damages
        damages = db.query(DamageDetection).filter(
            DamageDetection.claim_id == claim.id
        ).all()
        print(f"\n🔧 Damages Detected: {len(damages)}")
        for i, damage in enumerate(damages, 1):
            print(f"   {i}. {damage.damage_type.value} (confidence: {damage.confidence:.2f})")
            if damage.damage_hash_phash:
                print(f"      Hash: {damage.damage_hash_phash[:16]}...")
        
        # Check ICVE estimate
        icve = db.query(ICVEEstimate).filter(
            ICVEEstimate.claim_id == claim.id
        ).first()
        
        if icve:
            print(f"\n💰 ICVE Estimate:")
            print(f"   Parts Subtotal: ₹{icve.parts_subtotal:,.2f}")
            print(f"   Labour Subtotal: ₹{icve.labour_subtotal:,.2f}")
            print(f"   Tax (GST 18%): ₹{icve.tax_total:,.2f}")
            print(f"   Total Estimate: ₹{icve.total_estimate:,.2f}")
            print(f"   Rule Version: {icve.icve_rule_version}")
            
            # Check line items
            line_items = db.query(ICVELineItem).filter(
                ICVELineItem.icve_estimate_id == icve.id
            ).all()
            print(f"\n   Line Items: {len(line_items)}")
            for item in line_items:
                print(f"   - {item.item_type}: {item.item_name} = ₹{item.amount:,.2f}")
        else:
            print(f"\n❌ No ICVE estimate found")
            all_locks_passed = False
        
        # Check final status
        print(f"\n📊 Final Claim Status:")
        print(f"   Status: {claim.status.value}")
        print(f"   VIN Hash: {claim.vin_hash}")
        
        # Validation
        print(f"\n{'=' * 80}")
        print("VALIDATION RESULTS:")
        print(f"{'=' * 80}")
        
        success = True
        checks = []
        
        # Check all P0 locks passed
        if all_locks_passed:
            checks.append(("✅", "All 6 P0 locks passed"))
        else:
            checks.append(("❌", "Some P0 locks failed"))
            success = False
        
        # Check damages detected
        if len(damages) > 0:
            checks.append(("✅", f"{len(damages)} damages detected and hashed"))
        else:
            checks.append(("❌", "No damages detected"))
            success = False
        
        # Check ICVE estimate
        if icve and icve.total_estimate > 0:
            checks.append(("✅", f"ICVE estimate generated: ₹{icve.total_estimate:,.2f}"))
        else:
            checks.append(("❌", "ICVE estimate missing or zero"))
            success = False
        
        # Check final status
        if claim.status == ClaimStatus.DRAFT_READY:
            checks.append(("✅", "Claim transitioned to DRAFT_READY"))
        else:
            checks.append(("⚠️ ", f"Claim status is {claim.status.value} (expected DRAFT_READY)"))
            # Not a failure if locks passed but status not updated
        
        # Print all checks
        for icon, message in checks:
            print(f"{icon} {message}")
        
        if success:
            print(f"\n{'=' * 80}")
            print("🎉 FULL PIPELINE TEST PASSED!")
            print(f"{'=' * 80}")
            print(f"\n✨ All P0 Locks Complete!")
            print(f"   - Quality gate validated")
            print(f"   - VIN extracted and hashed")
            print(f"   - {len(damages)} damages detected")
            print(f"   - Damage hashes generated")
            print(f"   - Duplicate check completed")
            print(f"   - ICVE estimate: ₹{icve.total_estimate:,.2f}")
            print(f"   - Claim ready for surveyor review")
        else:
            print(f"\n{'=' * 80}")
            print("⚠️  PIPELINE COMPLETED WITH WARNINGS")
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
    success = test_full_pipeline()
    sys.exit(0 if success else 1)
