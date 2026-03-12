"""
Test script for logout API endpoint.
"""
import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_logout():
    """Test the logout endpoint."""
    print("\n" + "="*60)
    print("Testing Logout API Endpoint")
    print("="*60)
    
    # Step 1: Login first to get a token
    print("\n1. Logging in to get access token...")
    
    # Send OTP
    send_otp_response = requests.post(
        f"{BASE_URL}/auth/send-otp",
        json={"phone": "+919876543210"}  # Surveyor from seed data
    )
    
    if send_otp_response.status_code != 200:
        print(f"❌ Failed to send OTP: {send_otp_response.text}")
        return
    
    print("✅ OTP sent successfully")
    print(f"   Check console for OTP")
    
    # Get OTP from user
    otp = input("\nEnter OTP: ")
    
    # Verify OTP
    verify_response = requests.post(
        f"{BASE_URL}/auth/verify-otp",
        json={"phone": "+919876543210", "otp": otp}
    )
    
    if verify_response.status_code != 200:
        print(f"❌ Failed to verify OTP: {verify_response.text}")
        return
    
    token_data = verify_response.json()
    access_token = token_data["access_token"]
    user_id = token_data["user_id"]
    
    print("✅ Login successful")
    print(f"   User ID: {user_id}")
    print(f"   Access Token: {access_token[:20]}...")
    
    # Step 2: Test logout endpoint
    print("\n2. Testing logout endpoint...")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    logout_response = requests.post(
        f"{BASE_URL}/auth/logout",
        headers=headers
    )
    
    if logout_response.status_code == 200:
        print("✅ Logout successful")
        print(f"   Response: {json.dumps(logout_response.json(), indent=2)}")
    else:
        print(f"❌ Logout failed: {logout_response.status_code}")
        print(f"   Response: {logout_response.text}")
        return
    
    # Step 3: Verify token is still valid (JWT tokens can't be invalidated server-side)
    print("\n3. Verifying token behavior after logout...")
    
    profile_response = requests.get(
        f"{BASE_URL}/users/profile",
        headers=headers
    )
    
    if profile_response.status_code == 200:
        print("⚠️  Token still valid (expected for stateless JWT)")
        print("   Client must clear tokens locally")
    else:
        print(f"✅ Token invalidated: {profile_response.status_code}")
    
    # Step 4: Check audit log
    print("\n4. Checking audit log...")
    
    audit_response = requests.get(
        f"{BASE_URL}/audit/events",
        headers=headers,
        params={"action": "LOGOUT", "limit": 1}
    )
    
    if audit_response.status_code == 200:
        events = audit_response.json()
        if events:
            print("✅ Logout event logged in audit trail")
            print(f"   Event: {json.dumps(events[0], indent=2)}")
        else:
            print("⚠️  No logout event found in audit log")
    else:
        print(f"⚠️  Could not fetch audit log: {audit_response.status_code}")
    
    print("\n" + "="*60)
    print("Logout API Test Complete")
    print("="*60)


if __name__ == "__main__":
    try:
        test_logout()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
