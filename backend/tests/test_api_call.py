"""
Test API call to surveyor endpoint
"""
import requests
import json

# Get a surveyor token first
login_response = requests.post(
    'http://localhost:8000/api/auth/send-otp',
    json={'phone': '+919876543220'}
)
print(f"Send OTP: {login_response.status_code}")

# Use a test OTP (you'll need to check what OTP was sent or use a known one)
# For now, let's just test with an existing token if we have one

# Try to get the claim details
claim_id = 'd99db613-b060-4c39-8375-762e41759f94'

# First, let's try without auth to see the error
response = requests.get(f'http://localhost:8000/api/surveyor/claims/{claim_id}')
print(f"\nWithout auth: {response.status_code}")
print(response.text[:500])

# Now let's try to login and get a token
# We'll use the surveyor phone number
print("\n" + "="*60)
print("To test with authentication, you need to:")
print("1. Send OTP to +919876543220")
print("2. Get the OTP from the backend logs or database")
print("3. Verify OTP to get a token")
print("4. Use that token to call the endpoint")
print("="*60)
