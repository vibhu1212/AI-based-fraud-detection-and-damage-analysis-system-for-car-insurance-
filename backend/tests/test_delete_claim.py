#!/usr/bin/env python3
"""
Test script to verify claim deletion functionality
"""
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
CUSTOMER_PHONE = "+919876543210"  # Test customer

def test_delete_claim():
    """Test the delete claim endpoint"""
    
    print("=" * 60)
    print("Testing Claim Deletion Functionality")
    print("=" * 60)
    
    # Step 1: Login as customer
    print("\n1. Logging in as customer...")
    login_response = requests.post(
        f"{BASE_URL}/api/auth/send-otp",
        json={"phone": CUSTOMER_PHONE}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Failed to send OTP: {login_response.text}")
        return
    
    print("✅ OTP sent (check backend console for OTP)")
    otp = input("Enter OTP from backend console: ").strip()
    
    verify_response = requests.post(
        f"{BASE_URL}/api/auth/verify-otp",
        json={"phone": CUSTOMER_PHONE, "otp": otp}
    )
    
    if verify_response.status_code != 200:
        print(f"❌ Failed to verify OTP: {verify_response.text}")
        return
    
    token = verify_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Logged in successfully")
    
    # Step 2: Get list of claims
    print("\n2. Fetching claims...")
    claims_response = requests.get(
        f"{BASE_URL}/api/claims/dashboard",
        headers=headers
    )
    
    if claims_response.status_code != 200:
        print(f"❌ Failed to fetch claims: {claims_response.text}")
        return
    
    claims_data = claims_response.json()
    recent_claims = claims_data.get("recent_claims", [])
    
    print(f"✅ Found {len(recent_claims)} claims")
    
    # Find CREATED claims
    created_claims = [c for c in recent_claims if c["status"] == "CREATED"]
    
    if not created_claims:
        print("\n⚠️  No claims in CREATED status found")
        print("Creating a test claim...")
        
        # Create a test claim
        create_response = requests.post(
            f"{BASE_URL}/api/claims",
            headers=headers,
            json={
                "policy_id": "test-policy-id",
                "incident_date": "2026-01-28",
                "incident_description": "Test claim for deletion",
                "incident_location_lat": 12.9716,
                "incident_location_lng": 77.5946
            }
        )
        
        if create_response.status_code != 201:
            print(f"❌ Failed to create test claim: {create_response.text}")
            return
        
        test_claim = create_response.json()
        claim_id = test_claim["id"]
        print(f"✅ Created test claim: {claim_id}")
    else:
        claim_id = created_claims[0]["id"]
        print(f"\n3. Found CREATED claim to delete: {claim_id}")
    
    # Step 3: Delete the claim
    print(f"\n4. Deleting claim {claim_id}...")
    delete_response = requests.delete(
        f"{BASE_URL}/api/claims/{claim_id}",
        headers=headers
    )
    
    if delete_response.status_code == 204:
        print("✅ Claim deleted successfully!")
    else:
        print(f"❌ Failed to delete claim: {delete_response.status_code}")
        print(f"Response: {delete_response.text}")
        return
    
    # Step 4: Verify deletion
    print("\n5. Verifying deletion...")
    verify_response = requests.get(
        f"{BASE_URL}/api/claims/{claim_id}",
        headers=headers
    )
    
    if verify_response.status_code == 404:
        print("✅ Claim successfully deleted (404 Not Found)")
    else:
        print(f"⚠️  Unexpected response: {verify_response.status_code}")
    
    print("\n" + "=" * 60)
    print("✅ DELETE CLAIM TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_delete_claim()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
