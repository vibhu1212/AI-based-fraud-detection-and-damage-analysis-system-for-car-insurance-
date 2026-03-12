#!/usr/bin/env python3
"""
Test script for Demo Data Seeding (Task 10.2)
Verifies seed data is created correctly
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.models.base import SessionLocal
from app.models import User, Policy, Claim, UserRole, ClaimStatus
from app.models.damage import DamageDetection
from app.models.report import AIArtifact
from app.models.icve import ICVEEstimate
from app.seed_data import seed_database

def test_seed_data():
    """Test that seed data is created correctly"""
    print("=" * 80)
    print("DEMO DATA SEEDING TEST (Task 10.2)")
    print("=" * 80)
    
    # Run seed
    print("\n🌱 Running seed script...")
    try:
        seed_database()
    except Exception as e:
        print(f"❌ Seed failed: {e}")
        return False
    
    # Verify data
    print("\n🔍 Verifying seeded data...")
    db = SessionLocal()
    
    try:
        # Check users
        users = db.query(User).all()
        customers = [u for u in users if u.role == UserRole.CUSTOMER]
        surveyors = [u for u in users if u.role == UserRole.SURVEYOR]
        admins = [u for u in users if u.role == UserRole.ADMIN]
        
        print(f"\n👥 Users:")
        print(f"   Total: {len(users)}")
        print(f"   Customers: {len(customers)}")
        print(f"   Surveyors: {len(surveyors)}")
        print(f"   Admins: {len(admins)}")
        
        # Check policies
        policies = db.query(Policy).all()
        print(f"\n📄 Policies: {len(policies)}")
        for policy in policies:
            print(f"   - {policy.policy_number}: {policy.vehicle_make} {policy.vehicle_model}")
        
        # Check claims
        claims = db.query(Claim).all()
        print(f"\n📋 Claims: {len(claims)}")
        
        status_counts = {}
        for claim in claims:
            status = claim.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            # Extract location from description
            desc_preview = claim.incident_description[:50] + "..." if len(claim.incident_description) > 50 else claim.incident_description
            print(f"   - {claim.id[:8]}... | {status.upper()} | {desc_preview}")
        
        print(f"\n   Status Breakdown:")
        for status, count in status_counts.items():
            print(f"   - {status}: {count}")
        
        # Check damages
        damages = db.query(DamageDetection).all()
        print(f"\n🔧 Damage Detections: {len(damages)}")
        
        # Check ICVE estimates
        icve_estimates = db.query(ICVEEstimate).all()
        print(f"\n💰 ICVE Estimates: {len(icve_estimates)}")
        for icve in icve_estimates:
            print(f"   - Claim {icve.claim_id[:8]}... | ₹{icve.total_estimate:,.2f}")
        
        # Check AI artifacts
        artifacts = db.query(AIArtifact).all()
        print(f"\n🤖 AI Artifacts: {len(artifacts)}")
        
        artifact_types = {}
        for artifact in artifacts:
            artifact_types[artifact.artifact_type] = artifact_types.get(artifact.artifact_type, 0) + 1
        
        for artifact_type, count in artifact_types.items():
            print(f"   - {artifact_type}: {count}")
        
        # Validation
        print(f"\n{'=' * 80}")
        print("VALIDATION RESULTS:")
        print(f"{'=' * 80}")
        
        success = True
        checks = []
        
        # Check user counts
        if len(customers) == 2:
            checks.append(("✅", f"2 customers created"))
        else:
            checks.append(("❌", f"Expected 2 customers, got {len(customers)}"))
            success = False
        
        if len(surveyors) == 2:
            checks.append(("✅", f"2 surveyors created"))
        else:
            checks.append(("❌", f"Expected 2 surveyors, got {len(surveyors)}"))
            success = False
        
        if len(admins) == 1:
            checks.append(("✅", f"1 admin created"))
        else:
            checks.append(("❌", f"Expected 1 admin, got {len(admins)}"))
            success = False
        
        # Check policies
        if len(policies) == 2:
            checks.append(("✅", f"2 policies created"))
        else:
            checks.append(("❌", f"Expected 2 policies, got {len(policies)}"))
            success = False
        
        # Check claims
        if len(claims) == 5:
            checks.append(("✅", f"5 sample claims created"))
        else:
            checks.append(("❌", f"Expected 5 claims, got {len(claims)}"))
            success = False
        
        # Check claim statuses
        expected_statuses = {
            ClaimStatus.APPROVED.value: 1,
            ClaimStatus.SURVEYOR_REVIEW.value: 1,
            ClaimStatus.ANALYZING.value: 1,
            ClaimStatus.REJECTED.value: 1,
            ClaimStatus.SUBMITTED.value: 1
        }
        
        statuses_match = True
        for status, expected_count in expected_statuses.items():
            actual_count = status_counts.get(status, 0)
            if actual_count != expected_count:
                statuses_match = False
                break
        
        if statuses_match:
            checks.append(("✅", f"Claims in various states (approved, surveyor review, analyzing, rejected, submitted)"))
        else:
            checks.append(("❌", f"Claim statuses don't match expected distribution"))
            success = False
        
        # Check damages (optional - we skip them without media assets)
        checks.append(("ℹ️ ", f"Damage detections skipped (requires media assets)"))
        
        # Check ICVE estimates
        if len(icve_estimates) >= 2:
            checks.append(("✅", f"{len(icve_estimates)} ICVE estimates created"))
        else:
            checks.append(("❌", f"Expected at least 2 ICVE estimates, got {len(icve_estimates)}"))
            success = False
        
        # Check AI artifacts
        if len(artifacts) > 0:
            checks.append(("✅", f"{len(artifacts)} AI artifacts created"))
        else:
            checks.append(("❌", f"No AI artifacts created"))
            success = False
        
        # Print all checks
        for icon, message in checks:
            print(f"{icon} {message}")
        
        if success:
            print(f"\n{'=' * 80}")
            print("🎉 DEMO DATA SEEDING TEST PASSED!")
            print(f"{'=' * 80}")
            print(f"\n✨ Task 10.2 Complete!")
            print(f"   - Demo users, policies, and claims created")
            print(f"   - Sample data covers all claim states")
            print(f"   - Ready for demo scenarios")
        else:
            print(f"\n{'=' * 80}")
            print("⚠️  DEMO DATA SEEDING COMPLETED WITH WARNINGS")
            print(f"{'=' * 80}")
        
        return success
        
    except Exception as e:
        print(f"\n❌ Error during verification: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = test_seed_data()
    sys.exit(0 if success else 1)
