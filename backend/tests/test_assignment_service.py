"""
Test script for Surveyor Assignment Service

Tests:
1. Get available surveyors
2. Calculate surveyor workload
3. Round-robin assignment
4. Senior surveyor assignment for RED risk claims
"""

import sys
from sqlalchemy.orm import Session

from app.models.base import SessionLocal
from app.services.assignment import SurveyorAssignmentService
from app.models.user import User, UserRole
from app.models.claim import Claim, ClaimStatus


def test_assignment_service():
    """Test the surveyor assignment service"""
    db: Session = SessionLocal()
    
    try:
        print("=" * 60)
        print("Testing Surveyor Assignment Service")
        print("=" * 60)
        
        # Initialize service
        service = SurveyorAssignmentService(db)
        
        # Test 1: Get available surveyors
        print("\n1. Testing get_available_surveyors()...")
        surveyors = service.get_available_surveyors()
        print(f"   Found {len(surveyors)} surveyors:")
        for surveyor in surveyors:
            print(f"   - {surveyor.name} ({surveyor.id})")
        
        if not surveyors:
            print("   ⚠️  No surveyors found in database")
            print("   Run seed_data.py to create test surveyors")
            return
        
        # Test 2: Calculate workload for each surveyor
        print("\n2. Testing get_surveyor_workload()...")
        for surveyor in surveyors:
            workload = service.get_surveyor_workload(surveyor.id)
            print(f"   {surveyor.name}: {workload} active claims")
        
        # Test 3: Round-robin assignment
        print("\n3. Testing round_robin_assign()...")
        assigned_id = service.round_robin_assign()
        if assigned_id:
            assigned_surveyor = db.query(User).filter(User.id == assigned_id).first()
            print(f"   ✅ Assigned to: {assigned_surveyor.name} ({assigned_id})")
            print(f"   Current workload: {service.get_surveyor_workload(assigned_id)}")
        else:
            print("   ❌ No surveyor available for assignment")
        
        # Test 4: Senior surveyor assignment
        print("\n4. Testing assign_to_senior_surveyor()...")
        if service.senior_surveyor_ids:
            print(f"   Senior surveyor IDs configured: {service.senior_surveyor_ids}")
            senior_id = service.assign_to_senior_surveyor()
            if senior_id:
                senior_surveyor = db.query(User).filter(User.id == senior_id).first()
                print(f"   ✅ Assigned to senior: {senior_surveyor.name} ({senior_id})")
            else:
                print("   ❌ No senior surveyor available")
        else:
            print("   ⚠️  No senior surveyors configured in SENIOR_SURVEYOR_IDS")
            print("   Add surveyor IDs to .env to test senior assignment")
        
        # Test 5: Assign a test claim
        print("\n5. Testing assign_claim() with different risk levels...")
        
        # Get a test claim or create one
        test_claim = db.query(Claim).filter(
            Claim.status == ClaimStatus.DRAFT_READY
        ).first()
        
        if test_claim:
            print(f"   Using existing claim: {test_claim.id}")
            print(f"   Risk level: {test_claim.risk_level}")
            
            assigned_id = service.assign_claim(test_claim)
            if assigned_id:
                assigned_surveyor = db.query(User).filter(User.id == assigned_id).first()
                print(f"   ✅ Would assign to: {assigned_surveyor.name} ({assigned_id})")
            else:
                print("   ❌ Assignment failed")
        else:
            print("   ⚠️  No DRAFT_READY claims found for testing")
            print("   Submit a claim to test assignment")
        
        print("\n" + "=" * 60)
        print("✅ Assignment Service Tests Complete")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_assignment_service()
