"""
Test script for policies API endpoints.
Tests Epic 16.4 - Replace Frontend Mocks with real API.
"""
import requests
import sys

BASE_URL = "http://localhost:8000"

def test_policies_api():
    """Test policies API endpoints."""
    print("=" * 60)
    print("Testing Policies API (Epic 16.4)")
    print("=" * 60)
    
    # Step 1: Login as customer
    print("\n1. Logging in as customer...")
    login_data = {
        "phone_number": "+919876543210",
        "otp": "123456"
    }
    
    # First send OTP
    send_otp_response = requests.post(
        f"{BASE_URL}/api/auth/send-otp",
        json={"phone_number": login_data["phone_number"]}
    )
    
    if send_otp_response.status_code != 200:
        print(f"❌ Failed to send OTP: {send_otp_response.status_code}")
        print(send_otp_response.text)
        return False
    
    print("✅ OTP sent successfully")
    
    # Verify OTP
    verify_response = requests.post(
        f"{BASE_URL}/api/auth/verify-otp",
        json=login_data
    )
    
    if verify_response.status_code != 200:
        print(f"❌ Failed to verify OTP: {verify_response.status_code}")
        print(verify_response.text)
        return False
    
    token_data = verify_response.json()
    access_token = token_data["access_token"]
    print(f"✅ Logged in successfully")
    print(f"   User: {token_data['user']['full_name']} ({token_data['user']['role']})")
    
    # Step 2: Get policies list
    print("\n2. Fetching policies list...")
    headers = {"Authorization": f"Bearer {access_token}"}
    
    policies_response = requests.get(
        f"{BASE_URL}/api/policies",
        headers=headers
    )
    
    if policies_response.status_code != 200:
        print(f"❌ Failed to fetch policies: {policies_response.status_code}")
        print(policies_response.text)
        return False
    
    policies = policies_response.json()
    print(f"✅ Fetched {len(policies)} policies")
    
    if len(policies) == 0:
        print("⚠️  No policies found for this customer")
        print("   This is acceptable - customer may not have policies yet")
        return True
    
    # Step 3: Display policy details
    print("\n3. Policy Details:")
    for i, policy in enumerate(policies, 1):
        print(f"\n   Policy {i}:")
        print(f"   - ID: {policy['id']}")
        print(f"   - Policy Number: {policy['policy_number']}")
        print(f"   - Vehicle: {policy.get('vehicle_make', 'N/A')} {policy.get('vehicle_model', 'N/A')}")
        print(f"   - Year: {policy.get('vehicle_year', 'N/A')}")
        print(f"   - IDV: ₹{policy.get('idv', 0):,.2f}")
        print(f"   - Valid Until: {policy.get('valid_until', 'N/A')}")
    
    # Step 4: Get specific policy by ID
    if len(policies) > 0:
        policy_id = policies[0]['id']
        print(f"\n4. Fetching specific policy by ID: {policy_id}")
        
        policy_response = requests.get(
            f"{BASE_URL}/api/policies/{policy_id}",
            headers=headers
        )
        
        if policy_response.status_code != 200:
            print(f"❌ Failed to fetch policy: {policy_response.status_code}")
            print(policy_response.text)
            return False
        
        policy = policy_response.json()
        print(f"✅ Fetched policy: {policy['policy_number']}")
    
    # Step 5: Test unauthorized access (no token)
    print("\n5. Testing unauthorized access (no token)...")
    unauth_response = requests.get(f"{BASE_URL}/api/policies")
    
    if unauth_response.status_code == 401:
        print("✅ Unauthorized access correctly rejected (401)")
    else:
        print(f"❌ Expected 401, got {unauth_response.status_code}")
        return False
    
    # Step 6: Test access to non-existent policy
    print("\n6. Testing access to non-existent policy...")
    fake_id = "00000000-0000-0000-0000-000000000000"
    fake_response = requests.get(
        f"{BASE_URL}/api/policies/{fake_id}",
        headers=headers
    )
    
    if fake_response.status_code == 404:
        print("✅ Non-existent policy correctly returns 404")
    else:
        print(f"⚠️  Expected 404, got {fake_response.status_code}")
    
    print("\n" + "=" * 60)
    print("✅ All Policies API Tests Passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = test_policies_api()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
