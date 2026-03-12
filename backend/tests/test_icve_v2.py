"""
Test Enhanced ICVE Calculation V2.0

Tests the integration of EnhancedCostEstimator with ICVE calculation task.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.tasks.icve_calculation_v2 import (
    extract_vehicle_info_from_claim,
    determine_vehicle_segment,
    determine_vehicle_type,
    classify_damage_severity,
    map_damage_type_to_cost_db,
    aggregate_damage_estimates
)
from app.services.cost_estimator_v2 import VehicleInfo, CostEstimate, get_cost_estimator
from app.models.damage import DamageDetection


def test_determine_vehicle_segment():
    """Test vehicle segment determination"""
    print("\n=== Testing Vehicle Segment Determination ===")
    
    test_cases = [
        ("Maruti Suzuki", "Alto", "micro"),
        ("Maruti Suzuki", "Swift", "hatchback"),
        ("Maruti Suzuki", "Dzire", "compact_sedan"),
        ("Hyundai", "Verna", "sedan"),
        ("Tata Motors", "Nexon", "compact_suv"),
        ("Hyundai", "Creta", "midsize_suv"),
        ("Toyota", "Fortuner", "fullsize_suv"),
        ("BMW", "3 Series", "luxury"),
        ("Ferrari", "F8", "super_luxury"),
    ]
    
    for brand, model, expected in test_cases:
        result = determine_vehicle_segment(brand, model)
        status = "✅" if result == expected else "❌"
        print(f"{status} {brand} {model}: {result} (expected: {expected})")
        assert result == expected, f"Expected {expected}, got {result}"
    
    print("✅ All vehicle segment tests passed!")


def test_determine_vehicle_type():
    """Test vehicle type determination"""
    print("\n=== Testing Vehicle Type Determination ===")
    
    test_cases = [
        ("Hero", "Splendor", "motorbike_economy"),
        ("Royal Enfield", "Classic", "motorbike_premium"),
        ("Kawasaki", "Ninja", "motorbike_superbike"),
        ("Bajaj", "Auto Rickshaw", "threewheel"),
        ("Maruti Suzuki", "Swift", "car"),
        ("Maruti Suzuki", "Ertiga", "van_passenger"),
        ("Tata Motors", "Ace", "van_cargo"),
        ("Force", "Traveller", "bus_mini"),
        ("Mahindra", "Bolero Pickup", "truck_light"),
    ]
    
    for brand, model, expected in test_cases:
        result = determine_vehicle_type(brand, model)
        status = "✅" if result == expected else "❌"
        print(f"{status} {brand} {model}: {result} (expected: {expected})")
        assert result == expected, f"Expected {expected}, got {result}"
    
    print("✅ All vehicle type tests passed!")


def test_classify_damage_severity():
    """Test damage severity classification"""
    print("\n=== Testing Damage Severity Classification ===")
    
    # Create mock damage objects
    class MockDamage:
        def __init__(self, confidence, bbox):
            self.confidence = confidence
            self.bbox = bbox
    
    test_cases = [
        (MockDamage(0.6, [0, 0, 100, 100]), "minor"),  # Small area, low confidence
        (MockDamage(0.8, [0, 0, 200, 200]), "moderate"),  # Medium area, medium confidence
        (MockDamage(0.95, [0, 0, 300, 300]), "severe"),  # Large area, high confidence
    ]
    
    for damage, expected in test_cases:
        result = classify_damage_severity(damage)
        bbox_area = damage.bbox[2] * damage.bbox[3]
        status = "✅" if result == expected else "❌"
        print(f"{status} Confidence: {damage.confidence:.2f}, Area: {bbox_area} → {result} (expected: {expected})")
        assert result == expected, f"Expected {expected}, got {result}"
    
    print("✅ All severity classification tests passed!")


def test_map_damage_type_to_cost_db():
    """Test damage type mapping"""
    print("\n=== Testing Damage Type Mapping ===")
    
    test_cases = [
        ("dent", "dent"),
        ("scratch", "scratch"),
        ("front-bumper-dent", "front-bumper-dent"),
        ("doorouter-dent", "doorouter-dent"),
        ("Headlight-Damage", "Headlight-Damage"),
        ("glass-shatter", "Front-Windscreen-Damage"),
        ("unknown_damage", "dent"),  # Default fallback
    ]
    
    for input_type, expected in test_cases:
        result = map_damage_type_to_cost_db(input_type)
        status = "✅" if result == expected else "❌"
        print(f"{status} {input_type} → {result} (expected: {expected})")
        assert result == expected, f"Expected {expected}, got {result}"
    
    print("✅ All damage type mapping tests passed!")


def test_aggregate_damage_estimates():
    """Test damage estimate aggregation"""
    print("\n=== Testing Damage Estimate Aggregation ===")
    
    # Create mock estimates
    estimator = get_cost_estimator()
    
    vehicle_info = VehicleInfo(
        brand="Maruti Suzuki",
        model="Swift",
        segment="hatchback",
        age_years=3.0,
        paint_type="standard_solid",
        vehicle_type="car"
    )
    
    # Create two damage estimates
    estimate1 = estimator.estimate_damage_cost(
        damage_type="front-bumper-dent",
        severity="moderate",
        vehicle_info=vehicle_info,
        location="tier2_cities"
    )
    
    estimate2 = estimator.estimate_damage_cost(
        damage_type="doorouter-scratch",
        severity="minor",
        vehicle_info=vehicle_info,
        location="tier2_cities"
    )
    
    # Aggregate
    result = aggregate_damage_estimates([estimate1, estimate2], vehicle_info)
    
    print(f"Estimate 1: ₹{estimate1.breakdown.total_with_gst:,}")
    print(f"Estimate 2: ₹{estimate2.breakdown.total_with_gst:,}")
    print(f"\nAggregated Results:")
    print(f"  Parts Subtotal: ₹{result['parts_subtotal']:,}")
    print(f"  Labour Subtotal: ₹{result['labour_subtotal']:,}")
    print(f"  GST Total: ₹{result['gst_total']:,}")
    print(f"  Total with GST: ₹{result['total_with_gst']:,}")
    print(f"  Depreciation ({result['depreciation_percent']}%): ₹{result['depreciation_amount']:,}")
    print(f"  Claim Settlement: ₹{result['claim_settlement']:,}")
    
    # Verify aggregation
    assert result['parts_subtotal'] > 0, "Parts subtotal should be positive"
    assert result['labour_subtotal'] > 0, "Labour subtotal should be positive"
    assert result['gst_total'] > 0, "GST should be positive"
    assert result['claim_settlement'] < result['total_with_gst'], "Settlement should be less than total (due to depreciation)"
    
    print("\n✅ Aggregation test passed!")


def test_full_cost_estimation_flow():
    """Test full cost estimation flow for different vehicle types"""
    print("\n=== Testing Full Cost Estimation Flow ===")
    
    estimator = get_cost_estimator()
    
    test_scenarios = [
        {
            "name": "Hatchback - Minor Damage",
            "vehicle": VehicleInfo(
                brand="Maruti Suzuki",
                model="Swift",
                segment="hatchback",
                age_years=2.0,
                vehicle_type="car"
            ),
            "damage_type": "front-bumper-scratch",
            "severity": "minor",
            "location": "tier2_cities"
        },
        {
            "name": "Luxury SUV - Severe Damage",
            "vehicle": VehicleInfo(
                brand="BMW",
                model="X5",
                segment="luxury",
                age_years=1.0,
                vehicle_type="car"
            ),
            "damage_type": "front-bumper-dent",
            "severity": "severe",
            "location": "metro_cities"
        },
        {
            "name": "Motorcycle - Moderate Damage",
            "vehicle": VehicleInfo(
                brand="Royal Enfield",
                model="Classic",
                segment="hatchback",  # Not used for motorcycles
                age_years=3.0,
                vehicle_type="motorbike_premium"
            ),
            "damage_type": "dent",
            "severity": "moderate",
            "location": "tier2_cities"
        },
    ]
    
    for scenario in test_scenarios:
        print(f"\n--- {scenario['name']} ---")
        
        estimate = estimator.estimate_damage_cost(
            damage_type=scenario['damage_type'],
            severity=scenario['severity'],
            vehicle_info=scenario['vehicle'],
            location=scenario['location']
        )
        
        print(f"Vehicle: {scenario['vehicle'].brand} {scenario['vehicle'].model}")
        print(f"Damage: {scenario['damage_type']} ({scenario['severity']})")
        print(f"Location: {scenario['location']}")
        print(f"\nCost Breakdown:")
        print(f"  Base Cost: ₹{estimate.breakdown.subtotal_before_gst:,}")
        print(f"  Multipliers: Segment={estimate.multipliers.vehicle_segment:.2f}, "
              f"Brand={estimate.multipliers.brand:.2f}, "
              f"Regional={estimate.multipliers.regional:.2f}")
        print(f"  Total with GST: ₹{estimate.breakdown.total_with_gst:,}")
        print(f"  Depreciation ({estimate.breakdown.depreciation_percent}%): ₹{estimate.breakdown.depreciation_amount:,}")
        print(f"  Claim Settlement: ₹{estimate.breakdown.claim_settlement_estimate:,}")
        
        assert estimate.breakdown.total_with_gst > 0, "Total should be positive"
        assert estimate.breakdown.claim_settlement_estimate <= estimate.breakdown.total_with_gst, \
            "Settlement should be <= total"
    
    print("\n✅ All full flow tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("ENHANCED ICVE CALCULATION V2.0 - TEST SUITE")
    print("=" * 70)
    
    try:
        test_determine_vehicle_segment()
        test_determine_vehicle_type()
        test_classify_damage_severity()
        test_map_damage_type_to_cost_db()
        test_aggregate_damage_estimates()
        test_full_cost_estimation_flow()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
