#!/usr/bin/env python3
"""
Test script for customer dashboard API endpoint.
Tests Epic 15.1 - Dashboard Backend implementation.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.models.base import SessionLocal
from app.models.user import User
from app.models.claim import Claim
from app.models.enums import UserRole, ClaimStatus, RiskLevel
from app.services.auth import AuthService
import requests

def test_dashboard_endpoint():
    """Test the customer dashboard endpoint"""
    print("=" * 60)
    print("Testing Customer Dashboard API (Epic 15.1)")
    print("=" * 60)
    
    db = SessionLocal()
    auth_service = AuthService(db)
    
    try:
        # Find a customer user
        customer = db.query(User).filter(User.role == UserRole.CUSTOMER).first()
        
        if not customer:
            print("❌ No customer user found in database")
            print("   Run seed_data.py first to create test users")
            return False
        
        print(f"\n✅ Found customer: {customer.name} ({customer.phone})")
        
        # Generate JWT token for customer
        access_token = auth_service.create_access_token(customer.id, customer.role)
        print(f"✅ Generated access token")
        
        # Get customer's claims count
        claims_count = db.query(Claim).filter(Claim.customer_id == customer.id).count()
        print(f"✅ Customer has {claims_count} claims in database")
        
        # Test dashboard endpoint
        print("\n" + "-" * 60)
        print("Testing GET /api/claims/dashboard")
        print("-" * 60)
        
        response = requests.get(
            "http://localhost:8000/api/claims/dashboard",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code != 200:
            print(f"❌ Dashboard endpoint failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        data = response.json()
        print(f"✅ Dashboard endpoint returned 200 OK")
        
        # Validate response structure
        print("\n" + "-" * 60)
        print("Validating Response Structure")
        print("-" * 60)
        
        required_keys = ['stats', 'recent_claims', 'pending_claims', 'approved_claims', 'rejected_claims']
        for key in required_keys:
            if key not in data:
                print(f"❌ Missing key: {key}")
                return False
            print(f"✅ Found key: {key}")
        
        # Validate stats
        stats = data['stats']
        print(f"\n📊 Statistics:")
        print(f"   Total Claims: {stats['total_claims']}")
        print(f"   Pending: {stats['pending_claims']}")
        print(f"   Approved: {stats['approved_claims']}")
        print(f"   Rejected: {stats['rejected_claims']}")
        
        # Validate stats add up
        calculated_total = stats['pending_claims'] + stats['approved_claims'] + stats['rejected_claims']
        if calculated_total != stats['total_claims']:
            print(f"⚠️  Warning: Stats don't add up ({calculated_total} != {stats['total_claims']})")
            print(f"   This is expected if there are claims in other statuses")
        
        # Validate recent claims
        recent_claims = data['recent_claims']
        print(f"\n📋 Recent Claims: {len(recent_claims)}")
        if len(recent_claims) > 10:
            print(f"❌ Too many recent claims (should be max 10)")
            return False
        print(f"✅ Recent claims count is valid (≤10)")
        
        # Validate claim structure
        if recent_claims:
            claim = recent_claims[0]
            required_claim_keys = ['id', 'policy_id', 'status', 'risk_level', 'has_updates']
            for key in required_claim_keys:
                if key not in claim:
                    print(f"❌ Missing claim key: {key}")
                    return False
            print(f"✅ Claim structure is valid")
            
            # Display first claim
            print(f"\n📄 Sample Claim:")
            print(f"   ID: {claim['id'][:8]}...")
            print(f"   Status: {claim['status']}")
            print(f"   Risk Level: {claim['risk_level']}")
            print(f"   Has Updates: {claim['has_updates']}")
            if claim.get('estimated_amount'):
                print(f"   Estimated Amount: ₹{claim['estimated_amount']:,.2f}")
        
        # Validate grouped claims
        print(f"\n📊 Grouped Claims:")
        print(f"   Pending: {len(data['pending_claims'])}")
        print(f"   Approved: {len(data['approved_claims'])}")
        print(f"   Rejected: {len(data['rejected_claims'])}")
        
        # Verify pending claims have correct statuses
        pending_statuses = ['CREATED', 'SUBMITTED', 'ANALYZING', 'DRAFT_READY', 'SURVEYOR_REVIEW', 'NEEDS_MORE_INFO']
        for claim in data['pending_claims']:
            if claim['status'] not in pending_statuses:
                print(f"❌ Invalid pending claim status: {claim['status']}")
                return False
        print(f"✅ All pending claims have valid statuses")
        
        # Verify approved claims
        for claim in data['approved_claims']:
            if claim['status'] != 'APPROVED':
                print(f"❌ Invalid approved claim status: {claim['status']}")
                return False
        print(f"✅ All approved claims have APPROVED status")
        
        # Verify rejected claims
        for claim in data['rejected_claims']:
            if claim['status'] != 'REJECTED':
                print(f"❌ Invalid rejected claim status: {claim['status']}")
                return False
        print(f"✅ All rejected claims have REJECTED status")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - Dashboard API Working Correctly!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_dashboard_endpoint()
    sys.exit(0 if success else 1)
