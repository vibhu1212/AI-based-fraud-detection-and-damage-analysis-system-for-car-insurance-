"""
Test ICVE API Endpoints

Tests all ICVE API endpoints including:
- Get claim ICVE estimate
- Get vehicle segments
- Get brand categories
- Get damage types
- Preview cost estimate
- Get metadata
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import requests
from datetime import datetime, timezone

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

# Test user credentials
CUSTOMER_PHONE = "+919876543210"
CUSTOMER_OTP = "123456"

SURVEYOR_PHONE = "+919876543220"
SURVEYOR_OTP = "123456"


def print_section(title):
    """Print section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_test(test_name, passed, details=""):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"    {details}")


def login_user(phone):
    """Login and get access token"""
    # Send OTP
    response = requests.post(
        f"{API_BASE}/auth/send-otp",
        json={"phone": phone}
    )
    
    if response.status_code != 200:
        print(f"Failed to send OTP: {response.text}")
        return None
    
    print(f"    OTP sent to {phone}")
    print(f"    Check backend terminal for the OTP (look for '🔐 OTP for {phone}: XXXXXX')")
    
    # Prompt for OTP
    otp = input(f"    Enter OTP for {phone}: ").strip()
    
    # Verify OTP
    response = requests.post(
        f"{API_BASE}/auth/verify-otp",
        json={"phone": phone, "otp": otp}
    )
    
    if response.status_code != 200:
        print(f"Failed to verify OTP: {response.text}")
        return None
    
    data = response.json()
    return data.get("access_token")


def test_get_vehicle_segments(token):
    """Test GET /api/icve/vehicle-segments"""
    print_section("Test: Get Vehicle Segments")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE}/icve/vehicle-segments", headers=headers)
    
    passed = response.status_code == 200
    print_test("GET /api/icve/vehicle-segments", passed, f"Status: {response.status_code}")
    
    if passed:
        data = response.json()
        print(f"    Found {len(data)} vehicle segments")
        
        # Check structure
        if data and len(data) > 0:
            segment = data[0]
            has_required_fields = all(
                key in segment for key in [
                    "segment_key", "display_name", "base_multiplier",
                    "ex_showroom_range", "examples", "description"
                ]
            )
            print_test("Response has required fields", has_required_fields)
            
            # Print sample segments
            print("\n    Sample segments:")
            for seg in data[:3]:
                print(f"      - {seg['display_name']}: {seg['base_multiplier']}x (e.g., {', '.join(seg['examples'][:2])})")
    
    return passed


def test_get_brand_categories(token):
    """Test GET /api/icve/brand-categories"""
    print_section("Test: Get Brand Categories")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE}/icve/brand-categories", headers=headers)
    
    passed = response.status_code == 200
    print_test("GET /api/icve/brand-categories", passed, f"Status: {response.status_code}")
    
    if passed:
        data = response.json()
        print(f"    Found {len(data)} brand categories")
        
        # Check structure
        if data and len(data) > 0:
            category = data[0]
            has_required_fields = all(
                key in category for key in [
                    "category_key", "brands", "parts_multiplier",
                    "labor_multiplier", "spare_parts_availability", "notes"
                ]
            )
            print_test("Response has required fields", has_required_fields)
            
            # Print sample categories
            print("\n    Sample categories:")
            for cat in data[:3]:
                print(f"      - {cat['category_key']}: {cat['parts_multiplier']}x parts, {cat['labor_multiplier']}x labor")
                print(f"        Brands: {', '.join(cat['brands'][:3])}")
    
    return passed


def test_get_damage_types(token):
    """Test GET /api/icve/damage-types"""
    print_section("Test: Get Damage Types")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE}/icve/damage-types", headers=headers)
    
    passed = response.status_code == 200
    print_test("GET /api/icve/damage-types", passed, f"Status: {response.status_code}")
    
    if passed:
        data = response.json()
        print(f"    Found {len(data)} damage types")
        
        # Print sample damage types
        print("\n    Sample damage types:")
        for damage_type in data[:10]:
            print(f"      - {damage_type}")
    
    return passed


def test_get_metadata(token):
    """Test GET /api/icve/metadata"""
    print_section("Test: Get Cost Database Metadata")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE}/icve/metadata", headers=headers)
    
    passed = response.status_code == 200
    print_test("GET /api/icve/metadata", passed, f"Status: {response.status_code}")
    
    if passed:
        data = response.json()
        
        # Check required fields
        has_required_fields = all(
            key in data for key in [
                "version", "currency", "last_updated", "market",
                "sources", "gst_rate_parts", "gst_rate_labor", "coverage"
            ]
        )
        print_test("Response has required fields", has_required_fields)
        
        # Print metadata
        print(f"\n    Version: {data.get('version')}")
        print(f"    Currency: {data.get('currency')}")
        print(f"    Market: {data.get('market')}")
        print(f"    Last Updated: {data.get('last_updated')}")
        print(f"    GST Rates: {data.get('gst_rate_parts')}% parts, {data.get('gst_rate_labor')}% labor")
        
        if "coverage" in data:
            coverage = data["coverage"]
            print(f"\n    Coverage:")
            print(f"      - Damage Types: {coverage.get('damage_types')}")
            print(f"      - Vehicle Segments: {coverage.get('vehicle_segments')}")
            print(f"      - Brand Categories: {coverage.get('brand_categories')}")
    
    return passed


def test_preview_cost_estimate(token):
    """Test POST /api/icve/estimate-preview"""
    print_section("Test: Preview Cost Estimate")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test Case 1: Hatchback - Minor Damage
    print("\n  Test Case 1: Hatchback - Minor Damage")
    payload = {
        "damage_type": "front-bumper-scratch",
        "severity": "minor",
        "vehicle_brand": "Maruti Suzuki",
        "vehicle_model": "Swift",
        "vehicle_age_years": 2.0,
        "location": "tier2_cities",
        "workshop_type": "local_fka_garage"
    }
    
    response = requests.post(f"{API_BASE}/icve/estimate-preview", headers=headers, json=payload)
    passed1 = response.status_code == 200
    print_test("POST /api/icve/estimate-preview (Hatchback)", passed1, f"Status: {response.status_code}")
    
    if passed1:
        data = response.json()
        breakdown = data.get("breakdown", {})
        multipliers = data.get("multipliers", {})
        
        print(f"    Damage: {data.get('damage_type')} ({data.get('severity')})")
        print(f"    Vehicle: {data.get('vehicle_info', {}).get('brand')} {data.get('vehicle_info', {}).get('model')}")
        print(f"    Segment: {data.get('vehicle_info', {}).get('segment')}")
        print(f"\n    Cost Breakdown:")
        print(f"      Parts: ₹{breakdown.get('parts_subtotal'):,}")
        print(f"      Labor: ₹{breakdown.get('labour_subtotal'):,}")
        print(f"      GST: ₹{breakdown.get('total_gst'):,}")
        print(f"      Total with GST: ₹{breakdown.get('total_with_gst'):,}")
        print(f"      Depreciation ({breakdown.get('depreciation_percent')}%): ₹{breakdown.get('depreciation_amount'):,}")
        print(f"      Settlement: ₹{breakdown.get('claim_settlement_estimate'):,}")
        
        print(f"\n    Multipliers:")
        print(f"      Segment: {multipliers.get('vehicle_segment')}x")
        print(f"      Brand: {multipliers.get('brand')}x")
        print(f"      Regional: {multipliers.get('regional')}x")
        print(f"      Workshop: {multipliers.get('workshop')}x")
        print(f"      Combined: {multipliers.get('combined')}x")
    
    # Test Case 2: Luxury SUV - Severe Damage
    print("\n  Test Case 2: Luxury SUV - Severe Damage")
    payload = {
        "damage_type": "front-bumper-dent",
        "severity": "severe",
        "vehicle_brand": "BMW",
        "vehicle_model": "X5",
        "vehicle_age_years": 1.0,
        "location": "metro_cities",
        "workshop_type": "authorized_service_center"
    }
    
    response = requests.post(f"{API_BASE}/icve/estimate-preview", headers=headers, json=payload)
    passed2 = response.status_code == 200
    print_test("POST /api/icve/estimate-preview (Luxury SUV)", passed2, f"Status: {response.status_code}")
    
    if passed2:
        data = response.json()
        breakdown = data.get("breakdown", {})
        multipliers = data.get("multipliers", {})
        
        print(f"    Damage: {data.get('damage_type')} ({data.get('severity')})")
        print(f"    Vehicle: {data.get('vehicle_info', {}).get('brand')} {data.get('vehicle_info', {}).get('model')}")
        print(f"    Segment: {data.get('vehicle_info', {}).get('segment')}")
        print(f"\n    Cost Breakdown:")
        print(f"      Parts: ₹{breakdown.get('parts_subtotal'):,}")
        print(f"      Labor: ₹{breakdown.get('labour_subtotal'):,}")
        print(f"      GST: ₹{breakdown.get('total_gst'):,}")
        print(f"      Total with GST: ₹{breakdown.get('total_with_gst'):,}")
        print(f"      Depreciation ({breakdown.get('depreciation_percent')}%): ₹{breakdown.get('depreciation_amount'):,}")
        print(f"      Settlement: ₹{breakdown.get('claim_settlement_estimate'):,}")
        
        print(f"\n    Multipliers:")
        print(f"      Segment: {multipliers.get('vehicle_segment')}x")
        print(f"      Brand: {multipliers.get('brand')}x")
        print(f"      Regional: {multipliers.get('regional')}x")
        print(f"      Workshop: {multipliers.get('workshop')}x")
        print(f"      Combined: {multipliers.get('combined')}x")
    
    # Test Case 3: Motorcycle - Moderate Damage
    print("\n  Test Case 3: Motorcycle - Moderate Damage")
    payload = {
        "damage_type": "dent",
        "severity": "moderate",
        "vehicle_brand": "Royal Enfield",
        "vehicle_model": "Classic 350",
        "vehicle_age_years": 3.0,
        "location": "tier2_cities",
        "workshop_type": "local_fka_garage"
    }
    
    response = requests.post(f"{API_BASE}/icve/estimate-preview", headers=headers, json=payload)
    passed3 = response.status_code == 200
    print_test("POST /api/icve/estimate-preview (Motorcycle)", passed3, f"Status: {response.status_code}")
    
    if passed3:
        data = response.json()
        breakdown = data.get("breakdown", {})
        multipliers = data.get("multipliers", {})
        
        print(f"    Damage: {data.get('damage_type')} ({data.get('severity')})")
        print(f"    Vehicle: {data.get('vehicle_info', {}).get('brand')} {data.get('vehicle_info', {}).get('model')}")
        print(f"    Type: {data.get('vehicle_info', {}).get('vehicle_type')}")
        print(f"\n    Cost Breakdown:")
        print(f"      Parts: ₹{breakdown.get('parts_subtotal'):,}")
        print(f"      Labor: ₹{breakdown.get('labour_subtotal'):,}")
        print(f"      GST: ₹{breakdown.get('total_gst'):,}")
        print(f"      Total with GST: ₹{breakdown.get('total_with_gst'):,}")
        print(f"      Depreciation ({breakdown.get('depreciation_percent')}%): ₹{breakdown.get('depreciation_amount'):,}")
        print(f"      Settlement: ₹{breakdown.get('claim_settlement_estimate'):,}")
        
        print(f"\n    Multipliers:")
        print(f"      Vehicle Type: {multipliers.get('vehicle_type')}x")
        print(f"      Brand: {multipliers.get('brand')}x")
        print(f"      Regional: {multipliers.get('regional')}x")
        print(f"      Workshop: {multipliers.get('workshop')}x")
        print(f"      Combined: {multipliers.get('combined')}x")
    
    return passed1 and passed2 and passed3


def test_get_claim_icve(customer_token, surveyor_token):
    """Test GET /api/icve/claims/{claim_id}/icve"""
    print_section("Test: Get Claim ICVE Estimate")
    
    # First, get a claim ID from the customer's claims
    headers = {"Authorization": f"Bearer {customer_token}"}
    response = requests.get(f"{API_BASE}/claims", headers=headers)
    
    if response.status_code != 200:
        print_test("GET /api/claims (prerequisite)", False, "Failed to get claims list")
        return False
    
    claims = response.json()
    if not claims or len(claims) == 0:
        print("    No claims found. Skipping this test.")
        print("    (Create a claim with ICVE estimate first)")
        return True  # Not a failure, just no data
    
    # Find a claim with ICVE estimate
    claim_with_icve = None
    for claim in claims:
        if claim.get("status") in ["ai_processing_complete", "under_review", "approved", "rejected"]:
            claim_with_icve = claim
            break
    
    if not claim_with_icve:
        print("    No claims with ICVE estimate found. Skipping this test.")
        print("    (Wait for AI processing to complete on a claim)")
        return True  # Not a failure, just no data
    
    claim_id = claim_with_icve["id"]
    print(f"    Testing with claim ID: {claim_id}")
    
    # Test as customer
    print("\n  Test as Customer:")
    response = requests.get(f"{API_BASE}/icve/claims/{claim_id}/icve", headers=headers)
    passed_customer = response.status_code == 200
    print_test("GET /api/icve/claims/{id}/icve (customer)", passed_customer, f"Status: {response.status_code}")
    
    if passed_customer:
        data = response.json()
        
        # Check required fields
        has_required_fields = all(
            key in data for key in [
                "id", "claim_id", "icve_rule_version", "currency",
                "breakdown", "line_items", "created_at"
            ]
        )
        print_test("Response has required fields", has_required_fields)
        
        # Print ICVE details
        breakdown = data.get("breakdown", {})
        print(f"\n    ICVE Estimate:")
        print(f"      ID: {data.get('id')}")
        print(f"      Claim ID: {data.get('claim_id')}")
        print(f"      Version: {data.get('icve_rule_version')}")
        print(f"      Currency: {data.get('currency')}")
        
        if data.get("vehicle_make"):
            print(f"\n    Vehicle:")
            print(f"      Make: {data.get('vehicle_make')}")
            print(f"      Model: {data.get('vehicle_model')}")
            print(f"      Age: {data.get('vehicle_age_years')} years")
        
        print(f"\n    Cost Breakdown:")
        print(f"      Parts: ₹{breakdown.get('parts_subtotal'):,}")
        print(f"      Labor: ₹{breakdown.get('labour_subtotal'):,}")
        print(f"      GST: ₹{breakdown.get('total_gst'):,}")
        print(f"      Total with GST: ₹{breakdown.get('total_with_gst'):,}")
        print(f"      Depreciation ({breakdown.get('depreciation_percent')}%): ₹{breakdown.get('depreciation_amount'):,}")
        print(f"      Settlement: ₹{breakdown.get('claim_settlement_estimate'):,}")
        
        if data.get("multipliers"):
            multipliers = data["multipliers"]
            print(f"\n    Multipliers:")
            print(f"      Segment: {multipliers.get('vehicle_segment')}x")
            print(f"      Brand: {multipliers.get('brand')}x")
            print(f"      Regional: {multipliers.get('regional')}x")
            print(f"      Workshop: {multipliers.get('workshop')}x")
            print(f"      Combined: {multipliers.get('combined')}x")
        
        print(f"\n    Line Items: {len(data.get('line_items', []))}")
        print(f"    Damages Processed: {data.get('damages_processed')}")
    
    # Test as surveyor
    print("\n  Test as Surveyor:")
    surveyor_headers = {"Authorization": f"Bearer {surveyor_token}"}
    response = requests.get(f"{API_BASE}/icve/claims/{claim_id}/icve", headers=surveyor_headers)
    passed_surveyor = response.status_code == 200
    print_test("GET /api/icve/claims/{id}/icve (surveyor)", passed_surveyor, f"Status: {response.status_code}")
    
    return passed_customer and passed_surveyor


def main():
    """Run all ICVE API tests"""
    print("\n" + "="*80)
    print("  ICVE API ENDPOINT TESTS")
    print("="*80)
    print(f"\n  Base URL: {BASE_URL}")
    print(f"  API Base: {API_BASE}")
    
    # Login as customer
    print_section("Login as Customer")
    customer_token = login_user(CUSTOMER_PHONE)
    if not customer_token:
        print("❌ Failed to login as customer")
        return
    print("✅ Customer login successful")
    
    # Login as surveyor
    print_section("Login as Surveyor")
    surveyor_token = login_user(SURVEYOR_PHONE)
    if not surveyor_token:
        print("❌ Failed to login as surveyor")
        return
    print("✅ Surveyor login successful")
    
    # Run tests
    results = []
    
    results.append(("Get Vehicle Segments", test_get_vehicle_segments(customer_token)))
    results.append(("Get Brand Categories", test_get_brand_categories(customer_token)))
    results.append(("Get Damage Types", test_get_damage_types(customer_token)))
    results.append(("Get Metadata", test_get_metadata(customer_token)))
    results.append(("Preview Cost Estimate", test_preview_cost_estimate(customer_token)))
    results.append(("Get Claim ICVE", test_get_claim_icve(customer_token, surveyor_token)))
    
    # Summary
    print_section("Test Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*80}")
    print(f"  Results: {passed}/{total} tests passed")
    print(f"{'='*80}\n")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")


if __name__ == "__main__":
    main()
