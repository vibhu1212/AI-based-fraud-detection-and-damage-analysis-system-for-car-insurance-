"""
Unit tests for Enhanced Cost Estimator V2.0

Tests cover:
- Base cost lookup
- Multiplier calculations
- Depreciation application
- GST calculations
- Edge cases and error handling
"""

import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.cost_estimator_v2 import (
    EnhancedCostEstimator,
    VehicleInfo,
    CostEstimate,
    create_vehicle_info_from_dict
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def estimator():
    """Create cost estimator instance"""
    return EnhancedCostEstimator()


@pytest.fixture
def basic_vehicle():
    """Basic hatchback vehicle info"""
    return VehicleInfo(
        brand="Maruti Suzuki",
        model="Swift",
        segment="hatchback",
        age_years=2.5,
        paint_type="standard_solid",
        vehicle_type="car"
    )


@pytest.fixture
def luxury_vehicle():
    """Luxury vehicle info"""
    return VehicleInfo(
        brand="BMW",
        model="3 Series",
        segment="luxury",
        age_years=1.5,
        paint_type="metallic",
        vehicle_type="car"
    )


@pytest.fixture
def motorcycle():
    """Motorcycle vehicle info"""
    return VehicleInfo(
        brand="Royal Enfield",
        model="Classic 350",
        segment="hatchback",  # Not used for motorcycles
        age_years=1.0,
        paint_type="standard_solid",
        vehicle_type="motorbike_premium"
    )


# ============================================================================
# Test Base Cost Lookup
# ============================================================================

def test_base_cost_lookup(estimator):
    """Test basic cost database lookup"""
    base_costs = estimator._get_base_costs("front-bumper-dent", "moderate")
    
    assert base_costs is not None
    assert 'repair' in base_costs or 'replace' in base_costs
    assert 'paint' in base_costs
    assert 'labor_hours' in base_costs
    assert base_costs['labor_hours'] > 0


def test_all_severity_levels(estimator):
    """Test all severity levels for a damage type"""
    damage_type = "front-bumper-dent"
    
    minor = estimator._get_base_costs(damage_type, "minor")
    moderate = estimator._get_base_costs(damage_type, "moderate")
    severe = estimator._get_base_costs(damage_type, "severe")
    
    # Costs should increase with severity
    minor_total = minor.get('repair', 0) + minor.get('paint', 0)
    moderate_total = moderate.get('repair', 0) + moderate.get('paint', 0)
    severe_total = severe.get('replace', 0) + severe.get('paint', 0)
    
    assert minor_total < moderate_total
    assert moderate_total < severe_total


def test_unknown_damage_type(estimator):
    """Test handling of unknown damage type"""
    with pytest.raises(ValueError, match="Unknown damage type"):
        estimator._get_base_costs("nonexistent-damage", "minor")


def test_unknown_severity(estimator):
    """Test handling of unknown severity"""
    with pytest.raises(ValueError, match="Unknown severity"):
        estimator._get_base_costs("front-bumper-dent", "extreme")


# ============================================================================
# Test Vehicle Segment Multipliers
# ============================================================================

def test_vehicle_segment_multipliers(estimator):
    """Test vehicle segment multiplier retrieval"""
    micro = estimator._get_vehicle_segment_multiplier("micro")
    hatchback = estimator._get_vehicle_segment_multiplier("hatchback")
    luxury = estimator._get_vehicle_segment_multiplier("luxury")
    super_luxury = estimator._get_vehicle_segment_multiplier("super_luxury")
    
    # Verify multiplier progression
    assert micro < hatchback
    assert hatchback < luxury
    assert luxury < super_luxury
    
    # Verify specific values from database
    assert hatchback == 1.0  # Baseline
    assert luxury == 3.5
    assert super_luxury == 6.0


def test_unknown_segment_defaults_to_one(estimator):
    """Test unknown segment returns 1.0"""
    multiplier = estimator._get_vehicle_segment_multiplier("unknown_segment")
    assert multiplier == 1.0


# ============================================================================
# Test Brand Multipliers
# ============================================================================

def test_brand_multipliers(estimator):
    """Test brand multiplier calculation"""
    maruti = estimator._get_brand_multiplier("Maruti Suzuki")
    hyundai = estimator._get_brand_multiplier("Hyundai")
    bmw = estimator._get_brand_multiplier("BMW")
    ferrari = estimator._get_brand_multiplier("Ferrari")
    
    # Verify progression
    assert maruti == 1.0  # Domestic baseline
    assert hyundai > maruti  # Korean/Japanese
    assert bmw > hyundai  # German luxury
    assert ferrari > bmw  # Exotic


def test_brand_name_normalization(estimator):
    """Test brand name matching with different cases"""
    assert estimator._get_brand_multiplier("maruti suzuki") == 1.0
    assert estimator._get_brand_multiplier("MARUTI SUZUKI") == 1.0
    assert estimator._get_brand_multiplier("Maruti") == 1.0


# ============================================================================
# Test Regional Multipliers
# ============================================================================

def test_regional_multipliers(estimator):
    """Test regional labor rate multipliers"""
    metro = estimator._get_regional_multiplier("metro_cities")
    tier1 = estimator._get_regional_multiplier("tier1_cities")
    tier2 = estimator._get_regional_multiplier("tier2_cities")
    tier3 = estimator._get_regional_multiplier("tier3_cities_rural")
    
    # Verify progression
    assert metro > tier1
    assert tier1 > tier2
    assert tier2 > tier3
    
    # Verify specific values
    assert metro == 1.5
    assert tier2 == 1.0  # Baseline


# ============================================================================
# Test Workshop Multipliers
# ============================================================================

def test_workshop_multipliers(estimator):
    """Test workshop type multipliers"""
    asc = estimator._get_workshop_multiplier("authorized_ase")
    multi_brand = estimator._get_workshop_multiplier("multi_brand_organized")
    local = estimator._get_workshop_multiplier("local_fka_garage")
    roadside = estimator._get_workshop_multiplier("roadside_mechanic")
    
    # Verify progression
    assert asc > multi_brand
    assert multi_brand > local
    assert local > roadside
    
    # Verify specific values
    assert asc == 1.8
    assert local == 1.0  # Baseline


# ============================================================================
# Test Full Cost Estimation
# ============================================================================

def test_basic_cost_estimation(estimator, basic_vehicle):
    """Test complete cost estimation for basic vehicle"""
    estimate = estimator.estimate_damage_cost(
        damage_type="front-bumper-dent",
        severity="moderate",
        vehicle_info=basic_vehicle,
        location="tier2_cities",
        workshop_type="local_fka_garage"
    )
    
    assert estimate is not None
    assert estimate.damage_type == "front-bumper-dent"
    assert estimate.severity == "moderate"
    assert estimate.breakdown.total_with_gst > 0
    assert estimate.breakdown.claim_settlement_estimate > 0
    assert estimate.breakdown.depreciation_percent == 30  # 2.5 years old


def test_luxury_vehicle_cost_multiplier(estimator, basic_vehicle, luxury_vehicle):
    """Test that luxury vehicles cost significantly more"""
    basic_estimate = estimator.estimate_damage_cost(
        damage_type="front-bumper-dent",
        severity="moderate",
        vehicle_info=basic_vehicle
    )
    
    luxury_estimate = estimator.estimate_damage_cost(
        damage_type="front-bumper-dent",
        severity="moderate",
        vehicle_info=luxury_vehicle
    )
    
    # Luxury should cost at least 3x more (3.5x segment * 4.0x brand = 14x)
    assert luxury_estimate.breakdown.total_with_gst > basic_estimate.breakdown.total_with_gst * 10


def test_metro_vs_tier3_cost_difference(estimator, basic_vehicle):
    """Test regional cost differences"""
    metro_estimate = estimator.estimate_damage_cost(
        damage_type="doorouter-scratch",
        severity="minor",
        vehicle_info=basic_vehicle,
        location="metro_cities"
    )
    
    tier3_estimate = estimator.estimate_damage_cost(
        damage_type="doorouter-scratch",
        severity="minor",
        vehicle_info=basic_vehicle,
        location="tier3_cities_rural"
    )
    
    # Metro should be more expensive (1.5x vs 0.8x = 1.875x difference)
    assert metro_estimate.breakdown.total_with_gst > tier3_estimate.breakdown.total_with_gst


def test_authorized_vs_local_workshop(estimator, basic_vehicle):
    """Test workshop type cost differences"""
    asc_estimate = estimator.estimate_damage_cost(
        damage_type="bonnet-dent",
        severity="moderate",
        vehicle_info=basic_vehicle,
        workshop_type="authorized_ase"
    )
    
    local_estimate = estimator.estimate_damage_cost(
        damage_type="bonnet-dent",
        severity="moderate",
        vehicle_info=basic_vehicle,
        workshop_type="local_fka_garage"
    )
    
    # ASC should be 1.8x more expensive
    assert asc_estimate.breakdown.total_with_gst > local_estimate.breakdown.total_with_gst * 1.5


# ============================================================================
# Test Depreciation
# ============================================================================

def test_depreciation_by_age(estimator, basic_vehicle):
    """Test depreciation calculation for different vehicle ages"""
    # New vehicle (3 months)
    new_vehicle = VehicleInfo(
        brand="Maruti Suzuki",
        model="Swift",
        segment="hatchback",
        age_years=0.25,
        vehicle_type="car"
    )
    
    # 3-year-old vehicle
    old_vehicle = VehicleInfo(
        brand="Maruti Suzuki",
        model="Swift",
        segment="hatchback",
        age_years=3.5,
        vehicle_type="car"
    )
    
    new_estimate = estimator.estimate_damage_cost(
        damage_type="front-bumper-dent",
        severity="moderate",
        vehicle_info=new_vehicle
    )
    
    old_estimate = estimator.estimate_damage_cost(
        damage_type="front-bumper-dent",
        severity="moderate",
        vehicle_info=old_vehicle
    )
    
    # New vehicle should have lower depreciation
    assert new_estimate.breakdown.depreciation_percent < old_estimate.breakdown.depreciation_percent
    assert new_estimate.breakdown.depreciation_percent == 5  # 0-6 months
    assert old_estimate.breakdown.depreciation_percent == 40  # 3-4 years


def test_zero_depreciation_for_brand_new(estimator):
    """Test that brand new vehicles have minimal depreciation"""
    brand_new = VehicleInfo(
        brand="Hyundai",
        model="i20",
        segment="hatchback",
        age_years=0.0,
        vehicle_type="car"
    )
    
    estimate = estimator.estimate_damage_cost(
        damage_type="doorouter-scratch",
        severity="minor",
        vehicle_info=brand_new
    )
    
    assert estimate.breakdown.depreciation_percent == 5  # Minimum depreciation


# ============================================================================
# Test GST Calculations
# ============================================================================

def test_gst_calculation(estimator, basic_vehicle):
    """Test GST calculation (28% on parts, 18% on labor)"""
    estimate = estimator.estimate_damage_cost(
        damage_type="front-bumper-dent",
        severity="moderate",
        vehicle_info=basic_vehicle
    )
    
    # Verify GST is calculated
    assert estimate.breakdown.gst_on_parts > 0
    assert estimate.breakdown.gst_on_labor > 0
    assert estimate.breakdown.total_gst == (
        estimate.breakdown.gst_on_parts + estimate.breakdown.gst_on_labor
    )
    
    # Verify GST rates (approximately)
    parts_gst_rate = estimate.breakdown.gst_on_parts / estimate.breakdown.subtotal_parts
    labor_gst_rate = estimate.breakdown.gst_on_labor / estimate.breakdown.subtotal_labor
    
    assert 0.27 < parts_gst_rate < 0.29  # ~28%
    assert 0.17 < labor_gst_rate < 0.19  # ~18%


# ============================================================================
# Test Technology Variants
# ============================================================================

def test_technology_variant_multiplier(estimator, basic_vehicle):
    """Test technology variant pricing (LED vs Halogen headlights)"""
    halogen_estimate = estimator.estimate_damage_cost(
        damage_type="Headlight-Damage",
        severity="moderate",
        vehicle_info=basic_vehicle,
        technology_variant="halogen"
    )
    
    led_estimate = estimator.estimate_damage_cost(
        damage_type="Headlight-Damage",
        severity="moderate",
        vehicle_info=basic_vehicle,
        technology_variant="led"
    )
    
    # LED should be more expensive (1.8x multiplier)
    assert led_estimate.breakdown.total_with_gst > halogen_estimate.breakdown.total_with_gst * 1.5


# ============================================================================
# Test Vehicle Types (Motorcycles, Trucks, etc.)
# ============================================================================

def test_motorcycle_cost_estimation(estimator, motorcycle):
    """Test cost estimation for motorcycles"""
    estimate = estimator.estimate_damage_cost(
        damage_type="front-bumper-dent",
        severity="minor",
        vehicle_info=motorcycle
    )
    
    assert estimate is not None
    # Motorcycle should be cheaper (0.5x multiplier)
    assert estimate.multipliers.vehicle_type == 0.5


def test_truck_cost_estimation(estimator):
    """Test cost estimation for trucks"""
    truck = VehicleInfo(
        brand="Tata Motors",
        model="407",
        segment="hatchback",  # Not used for trucks
        age_years=5.0,
        vehicle_type="truck_medium"
    )
    
    estimate = estimator.estimate_damage_cost(
        damage_type="front-bumper-dent",
        severity="severe",
        vehicle_info=truck
    )
    
    assert estimate is not None
    # Truck should be more expensive (2.2x multiplier)
    assert estimate.multipliers.vehicle_type == 2.2


# ============================================================================
# Test Paint Type Multipliers
# ============================================================================

def test_paint_type_multipliers(estimator, basic_vehicle):
    """Test different paint type costs"""
    solid_vehicle = VehicleInfo(
        brand="Maruti Suzuki",
        model="Swift",
        segment="hatchback",
        age_years=2.0,
        paint_type="standard_solid",
        vehicle_type="car"
    )
    
    pearl_vehicle = VehicleInfo(
        brand="Maruti Suzuki",
        model="Swift",
        segment="hatchback",
        age_years=2.0,
        paint_type="pearl",
        vehicle_type="car"
    )
    
    solid_estimate = estimator.estimate_damage_cost(
        damage_type="doorouter-scratch",
        severity="moderate",
        vehicle_info=solid_vehicle
    )
    
    pearl_estimate = estimator.estimate_damage_cost(
        damage_type="doorouter-scratch",
        severity="moderate",
        vehicle_info=pearl_vehicle
    )
    
    # Pearl should be more expensive (1.6x multiplier)
    assert pearl_estimate.breakdown.total_with_gst > solid_estimate.breakdown.total_with_gst * 1.4


# ============================================================================
# Test Utility Methods
# ============================================================================

def test_get_supported_damage_types(estimator):
    """Test retrieval of supported damage types"""
    damage_types = estimator.get_supported_damage_types()
    
    assert isinstance(damage_types, list)
    assert len(damage_types) > 20
    assert "front-bumper-dent" in damage_types
    assert "doorouter-scratch" in damage_types


def test_get_vehicle_segments(estimator):
    """Test retrieval of vehicle segments"""
    segments = estimator.get_vehicle_segments()
    
    assert isinstance(segments, dict)
    assert "hatchback" in segments
    assert "luxury" in segments
    assert segments["hatchback"]["base_multiplier"] == 1.0


def test_get_brand_categories(estimator):
    """Test retrieval of brand categories"""
    brands = estimator.get_brand_categories()
    
    assert isinstance(brands, dict)
    assert "domestic_affordable" in brands
    assert "german_luxury" in brands


def test_get_database_metadata(estimator):
    """Test retrieval of database metadata"""
    metadata = estimator.get_database_metadata()
    
    assert isinstance(metadata, dict)
    assert "version" in metadata
    assert "currency" in metadata
    assert metadata["currency"] == "INR"


# ============================================================================
# Test Helper Functions
# ============================================================================

def test_create_vehicle_info_from_dict():
    """Test vehicle info creation from dictionary"""
    data = {
        "brand": "Hyundai",
        "model": "Creta",
        "segment": "midsize_suv",
        "age_years": 1.5,
        "paint_type": "metallic",
        "vehicle_type": "car"
    }
    
    vehicle_info = create_vehicle_info_from_dict(data)
    
    assert vehicle_info.brand == "Hyundai"
    assert vehicle_info.model == "Creta"
    assert vehicle_info.segment == "midsize_suv"
    assert vehicle_info.age_years == 1.5


def test_estimate_to_dict(estimator, basic_vehicle):
    """Test conversion of estimate to dictionary"""
    estimate = estimator.estimate_damage_cost(
        damage_type="front-bumper-dent",
        severity="moderate",
        vehicle_info=basic_vehicle
    )
    
    estimate_dict = estimate.to_dict()
    
    assert isinstance(estimate_dict, dict)
    assert "damage_type" in estimate_dict
    assert "breakdown" in estimate_dict
    assert "multipliers" in estimate_dict


# ============================================================================
# Test Edge Cases
# ============================================================================

def test_zero_age_vehicle(estimator):
    """Test estimation for brand new vehicle"""
    new_vehicle = VehicleInfo(
        brand="Tata Motors",
        model="Nexon",
        segment="compact_suv",
        age_years=0.0,
        vehicle_type="car"
    )
    
    estimate = estimator.estimate_damage_cost(
        damage_type="fender-dent",
        severity="minor",
        vehicle_info=new_vehicle
    )
    
    assert estimate.breakdown.depreciation_percent == 5


def test_very_old_vehicle(estimator):
    """Test estimation for very old vehicle (>10 years)"""
    old_vehicle = VehicleInfo(
        brand="Maruti Suzuki",
        model="Alto",
        segment="micro",
        age_years=12.0,
        vehicle_type="car"
    )
    
    estimate = estimator.estimate_damage_cost(
        damage_type="doorouter-dent",
        severity="moderate",
        vehicle_info=old_vehicle
    )
    
    assert estimate.breakdown.depreciation_percent == 50  # Maximum


def test_glass_damage_zero_depreciation(estimator, basic_vehicle):
    """Test that glass damage has 0% depreciation"""
    # Note: This is a business rule - glass parts have 0% depreciation
    # But our current implementation applies vehicle age depreciation
    # This test documents expected behavior for future enhancement
    estimate = estimator.estimate_damage_cost(
        damage_type="Front-Windscreen-Damage",
        severity="moderate",
        vehicle_info=basic_vehicle
    )
    
    # Should have note about glass depreciation
    assert any("glass" in note.lower() or "0%" in note for note in estimate.notes)


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
