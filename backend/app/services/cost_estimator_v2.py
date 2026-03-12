"""
Enhanced Cost Estimator Service V2.0

Comprehensive cost estimation for Indian vehicle repairs with:
- IRDA depreciation compliance
- Regional labor rate adjustments
- Vehicle segment and brand multipliers
- Technology variant pricing
- GST calculations
- Detailed cost breakdowns

Author: InsurAI Team
Version: 2.0
Date: 2026-01-27
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class VehicleInfo:
    """Vehicle information for cost estimation"""
    brand: str  # "Maruti Suzuki", "Hyundai", "BMW", etc.
    model: Optional[str] = None  # "Swift", "i20", etc.
    segment: str = "hatchback"  # Default to hatchback baseline
    age_years: float = 0.0  # For depreciation calculation
    paint_type: str = "standard_solid"  # "metallic", "pearl", etc.
    ex_showroom_price: Optional[int] = None  # For IDV calculation
    vehicle_type: str = "car"  # "motorbike_economy", "truck_light", etc.
    
    def __post_init__(self):
        """Normalize brand name for matching"""
        self.brand = self.brand.strip()


@dataclass
class CostBreakdown:
    """Detailed cost breakdown"""
    base_repair_cost: int = 0
    base_replace_cost: int = 0
    base_paint_cost: int = 0
    labor_cost: int = 0
    
    # After multipliers
    adjusted_repair_cost: int = 0
    adjusted_replace_cost: int = 0
    adjusted_paint_cost: int = 0
    adjusted_labor_cost: int = 0
    
    # Subtotals
    subtotal_parts: int = 0
    subtotal_labor: int = 0
    subtotal_before_gst: int = 0
    
    # GST
    gst_on_parts: int = 0
    gst_on_labor: int = 0
    total_gst: int = 0
    
    # Final
    total_with_gst: int = 0
    
    # Depreciation
    depreciation_percent: int = 0
    depreciation_amount: int = 0
    claim_settlement_estimate: int = 0


@dataclass
class MultipliersApplied:
    """Track all multipliers applied"""
    vehicle_segment: float = 1.0
    vehicle_type: float = 1.0
    brand: float = 1.0
    regional: float = 1.0
    workshop: float = 1.0
    paint_type: float = 1.0
    technology_variant: float = 1.0
    
    def get_combined_multiplier(self) -> float:
        """Calculate combined multiplier"""
        return (
            self.vehicle_segment *
            self.vehicle_type *
            self.brand *
            self.regional *
            self.workshop *
            self.paint_type *
            self.technology_variant
        )


@dataclass
class CostEstimate:
    """Complete cost estimate for a single damage"""
    damage_type: str
    severity: str
    
    # Base costs from database
    base_costs: Dict[str, Any] = field(default_factory=dict)
    
    # Labor
    labor_hours: float = 0.0
    labor_rate_per_hour: int = 500
    
    # Multipliers
    multipliers: MultipliersApplied = field(default_factory=MultipliersApplied)
    
    # Breakdown
    breakdown: CostBreakdown = field(default_factory=CostBreakdown)
    
    # Metadata
    location: str = "tier2_cities"
    workshop_type: str = "local_fka_garage"
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Timestamps
    estimated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "damage_type": self.damage_type,
            "severity": self.severity,
            "base_costs": self.base_costs,
            "labor_hours": self.labor_hours,
            "labor_rate_per_hour": self.labor_rate_per_hour,
            "multipliers": asdict(self.multipliers),
            "breakdown": asdict(self.breakdown),
            "location": self.location,
            "workshop_type": self.workshop_type,
            "notes": self.notes,
            "warnings": self.warnings,
            "estimated_at": self.estimated_at
        }


# ============================================================================
# Enhanced Cost Estimator
# ============================================================================

class EnhancedCostEstimator:
    """
    Advanced cost estimation engine for Indian vehicle repairs
    
    Features:
    - IRDA-compliant depreciation
    - Regional labor rate adjustments
    - Vehicle segment and brand multipliers
    - Technology variant pricing
    - Comprehensive cost breakdowns
    """
    
    def __init__(self, cost_db_path: Optional[str] = None):
        """
        Initialize cost estimator
        
        Args:
            cost_db_path: Path to repair_costs_inr.json (optional)
        """
        if cost_db_path is None:
            # Default path relative to this file
            base_path = Path(__file__).parent.parent.parent
            cost_db_path = base_path / "data" / "repair_costs_inr.json"
        
        self.cost_db = self._load_cost_database(cost_db_path)
        logger.info(f"Cost estimator initialized with database version {self.cost_db['metadata']['version']}")
    
    def _load_cost_database(self, path: Path) -> Dict[str, Any]:
        """Load and validate cost database"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                db = json.load(f)
            
            # Validate required sections
            required_sections = [
                'metadata', 'vehicle_types', 'damage_costs',
                'labor_rates', 'severity_multipliers'
            ]
            
            for section in required_sections:
                if section not in db:
                    raise ValueError(f"Missing required section: {section}")
            
            logger.info(f"Loaded cost database: {db['metadata']['version']} ({db['metadata']['last_updated']})")
            return db
            
        except FileNotFoundError:
            logger.error(f"Cost database not found at {path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in cost database: {e}")
            raise
    
    # ========================================================================
    # Main Estimation Method
    # ========================================================================
    
    def estimate_damage_cost(
        self,
        damage_type: str,
        severity: str,
        vehicle_info: VehicleInfo,
        location: str = "tier2_cities",
        workshop_type: str = "local_fka_garage",
        technology_variant: Optional[str] = None
    ) -> CostEstimate:
        """
        Calculate comprehensive cost estimate for a damage
        
        Args:
            damage_type: e.g., "front-bumper-dent", "doorouter-scratch"
            severity: "minor", "moderate", "severe"
            vehicle_info: VehicleInfo object with vehicle details
            location: City tier for regional adjustment
            workshop_type: Type of workshop (ASC, local, etc.)
            technology_variant: For parts with variants (e.g., "led" for headlights)
        
        Returns:
            CostEstimate with complete breakdown
        """
        estimate = CostEstimate(
            damage_type=damage_type,
            severity=severity,
            location=location,
            workshop_type=workshop_type
        )
        
        try:
            # 1. Get base costs from database
            base_costs = self._get_base_costs(damage_type, severity)
            estimate.base_costs = base_costs
            estimate.labor_hours = base_costs.get('labor_hours', 0)
            
            # 2. Get labor rate
            labor_rate = self._get_labor_rate(base_costs)
            estimate.labor_rate_per_hour = labor_rate
            
            # 3. Calculate multipliers
            multipliers = self._calculate_multipliers(
                vehicle_info=vehicle_info,
                location=location,
                workshop_type=workshop_type,
                damage_type=damage_type,
                technology_variant=technology_variant
            )
            estimate.multipliers = multipliers
            
            # 4. Calculate costs with multipliers
            breakdown = self._calculate_breakdown(
                base_costs=base_costs,
                labor_hours=estimate.labor_hours,
                labor_rate=labor_rate,
                multipliers=multipliers
            )
            estimate.breakdown = breakdown
            
            # 5. Apply depreciation
            self._apply_depreciation(
                breakdown=breakdown,
                vehicle_age_years=vehicle_info.age_years
            )
            
            # 6. Add notes and warnings
            self._add_notes_and_warnings(estimate, vehicle_info, base_costs)
            
            logger.info(f"Estimated {damage_type} ({severity}): ₹{breakdown.claim_settlement_estimate:,}")
            
        except Exception as e:
            logger.error(f"Error estimating cost for {damage_type}: {e}")
            estimate.warnings.append(f"Estimation error: {str(e)}")
            # Return estimate with error info
        
        return estimate
    
    # ========================================================================
    # Base Cost Retrieval
    # ========================================================================
    
    def _get_base_costs(self, damage_type: str, severity: str) -> Dict[str, Any]:
        """
        Get base costs from database
        
        Returns dict with: repair, replace, paint, labor_hours, total_estimate
        """
        damage_costs = self.cost_db.get('damage_costs', {})
        
        if damage_type not in damage_costs:
            # Try to find similar damage type
            similar = self._find_similar_damage_type(damage_type)
            if similar:
                logger.warning(f"Damage type '{damage_type}' not found, using '{similar}'")
                damage_type = similar
            else:
                raise ValueError(f"Unknown damage type: {damage_type}")
        
        damage_data = damage_costs[damage_type]
        
        if severity not in damage_data:
            raise ValueError(f"Unknown severity '{severity}' for damage '{damage_type}'")
        
        severity_data = damage_data[severity]
        
        # Extract costs
        base_costs = {
            'repair': severity_data.get('repair', 0),
            'replace': severity_data.get('replace', 0),
            'paint': severity_data.get('paint', 0),
            'labor_hours': severity_data.get('labor_hours', 0),
            'total_estimate': severity_data.get('total_estimate', 0),
            'part': damage_data.get('part', 'unknown'),
            'display_name': damage_data.get('display_name', damage_type)
        }
        
        return base_costs
    
    def _find_similar_damage_type(self, damage_type: str) -> Optional[str]:
        """Find similar damage type in database (fuzzy matching)"""
        damage_costs = self.cost_db.get('damage_costs', {})
        damage_type_lower = damage_type.lower().replace('_', '-')
        
        # Try exact match with different casing
        for key in damage_costs.keys():
            if key.lower() == damage_type_lower:
                return key
        
        # Try partial match
        for key in damage_costs.keys():
            if damage_type_lower in key.lower() or key.lower() in damage_type_lower:
                return key
        
        return None
    
    def _get_labor_rate(self, base_costs: Dict[str, Any]) -> int:
        """Determine appropriate labor rate based on repair type"""
        labor_rates = self.cost_db.get('labor_rates', {})
        
        # Determine labor type
        if base_costs.get('replace', 0) > 0:
            return labor_rates.get('replace', {}).get('rate_per_hour', 800)
        elif base_costs.get('paint', 0) > 0:
            return labor_rates.get('paint', {}).get('rate_per_hour', 600)
        else:
            return labor_rates.get('repair', {}).get('rate_per_hour', 500)
    
    # ========================================================================
    # Multiplier Calculations
    # ========================================================================
    
    def _calculate_multipliers(
        self,
        vehicle_info: VehicleInfo,
        location: str,
        workshop_type: str,
        damage_type: str,
        technology_variant: Optional[str]
    ) -> MultipliersApplied:
        """Calculate all applicable multipliers"""
        multipliers = MultipliersApplied()
        
        # 1. Vehicle segment multiplier
        multipliers.vehicle_segment = self._get_vehicle_segment_multiplier(vehicle_info.segment)
        
        # 2. Vehicle type multiplier
        multipliers.vehicle_type = self._get_vehicle_type_multiplier(vehicle_info.vehicle_type)
        
        # 3. Brand multiplier
        multipliers.brand = self._get_brand_multiplier(vehicle_info.brand)
        
        # 4. Regional multiplier
        multipliers.regional = self._get_regional_multiplier(location)
        
        # 5. Workshop type multiplier
        multipliers.workshop = self._get_workshop_multiplier(workshop_type)
        
        # 6. Paint type multiplier
        multipliers.paint_type = self._get_paint_type_multiplier(vehicle_info.paint_type)
        
        # 7. Technology variant multiplier (if applicable)
        if technology_variant:
            multipliers.technology_variant = self._get_technology_variant_multiplier(
                damage_type, technology_variant
            )
        
        return multipliers
    
    def _get_vehicle_segment_multiplier(self, segment: str) -> float:
        """Get multiplier based on vehicle segment"""
        segments = self.cost_db.get('vehicle_segments', {})
        
        if segment in segments:
            return segments[segment].get('base_multiplier', 1.0)
        
        logger.warning(f"Unknown vehicle segment '{segment}', using 1.0")
        return 1.0
    
    def _get_vehicle_type_multiplier(self, vehicle_type: str) -> float:
        """Get multiplier based on vehicle type"""
        vehicle_types = self.cost_db.get('vehicle_types', {})
        
        if vehicle_type in vehicle_types:
            return vehicle_types[vehicle_type].get('base_multiplier', 1.0)
        
        logger.warning(f"Unknown vehicle type '{vehicle_type}', using 1.0")
        return 1.0
    
    def _get_brand_multiplier(self, brand: str) -> float:
        """Get multiplier based on vehicle brand"""
        brand_multipliers = self.cost_db.get('brand_cost_multipliers', {})
        
        # Normalize brand name
        brand_lower = brand.lower()
        
        # Check each category
        for category, data in brand_multipliers.items():
            # Skip non-dict entries (like 'description')
            if not isinstance(data, dict):
                continue
                
            brands = data.get('brands', [])
            for b in brands:
                if b.lower() in brand_lower or brand_lower in b.lower():
                    return data.get('parts_multiplier', 1.0)
        
        logger.warning(f"Unknown brand '{brand}', using 1.0")
        return 1.0
    
    def _get_regional_multiplier(self, location: str) -> float:
        """Get multiplier based on location/city tier"""
        regional_rates = self.cost_db.get('regional_labor_rates', {})
        
        if location in regional_rates:
            return regional_rates[location].get('multiplier', 1.0)
        
        # Default to tier2 baseline
        return 1.0
    
    def _get_workshop_multiplier(self, workshop_type: str) -> float:
        """Get multiplier based on workshop type"""
        regional_rates = self.cost_db.get('regional_labor_rates', {})
        workshop_multipliers = regional_rates.get('workshop_type_multipliers', {})
        
        if workshop_type in workshop_multipliers:
            return workshop_multipliers[workshop_type].get('multiplier', 1.0)
        
        return 1.0
    
    def _get_paint_type_multiplier(self, paint_type: str) -> float:
        """Get multiplier based on paint type"""
        paint_types = self.cost_db.get('paint_types', {})
        
        if paint_type in paint_types:
            return paint_types[paint_type].get('multiplier', 1.0)
        
        return 1.0
    
    def _get_technology_variant_multiplier(
        self,
        damage_type: str,
        variant: str
    ) -> float:
        """Get multiplier for technology variants (LED headlights, etc.)"""
        damage_costs = self.cost_db.get('damage_costs', {})
        
        if damage_type in damage_costs:
            damage_data = damage_costs[damage_type]
            tech_variants = damage_data.get('technology_variants', {})
            
            if variant in tech_variants:
                return tech_variants[variant].get('multiplier', 1.0)
        
        return 1.0
    
    # ========================================================================
    # Cost Breakdown Calculation
    # ========================================================================
    
    def _calculate_breakdown(
        self,
        base_costs: Dict[str, Any],
        labor_hours: float,
        labor_rate: int,
        multipliers: MultipliersApplied
    ) -> CostBreakdown:
        """Calculate detailed cost breakdown with all multipliers"""
        breakdown = CostBreakdown()
        
        # Base costs
        breakdown.base_repair_cost = base_costs.get('repair', 0)
        breakdown.base_replace_cost = base_costs.get('replace', 0)
        breakdown.base_paint_cost = base_costs.get('paint', 0)
        breakdown.labor_cost = int(labor_hours * labor_rate)
        
        # Get combined multiplier for parts
        parts_multiplier = multipliers.get_combined_multiplier()
        
        # Apply multipliers to parts
        breakdown.adjusted_repair_cost = int(breakdown.base_repair_cost * parts_multiplier)
        breakdown.adjusted_replace_cost = int(breakdown.base_replace_cost * parts_multiplier)
        breakdown.adjusted_paint_cost = int(breakdown.base_paint_cost * parts_multiplier)
        
        # Labor gets regional and workshop multipliers only
        labor_multiplier = multipliers.regional * multipliers.workshop
        breakdown.adjusted_labor_cost = int(breakdown.labor_cost * labor_multiplier)
        
        # Subtotals
        breakdown.subtotal_parts = (
            breakdown.adjusted_repair_cost +
            breakdown.adjusted_replace_cost +
            breakdown.adjusted_paint_cost
        )
        breakdown.subtotal_labor = breakdown.adjusted_labor_cost
        breakdown.subtotal_before_gst = breakdown.subtotal_parts + breakdown.subtotal_labor
        
        # GST calculation
        gst_rate_parts = self.cost_db['metadata'].get('gst_rate_parts', 28) / 100
        gst_rate_labor = self.cost_db['metadata'].get('gst_rate_labor', 18) / 100
        
        breakdown.gst_on_parts = int(breakdown.subtotal_parts * gst_rate_parts)
        breakdown.gst_on_labor = int(breakdown.subtotal_labor * gst_rate_labor)
        breakdown.total_gst = breakdown.gst_on_parts + breakdown.gst_on_labor
        
        # Final total
        breakdown.total_with_gst = breakdown.subtotal_before_gst + breakdown.total_gst
        
        return breakdown
    
    # ========================================================================
    # Depreciation
    # ========================================================================
    
    def _apply_depreciation(
        self,
        breakdown: CostBreakdown,
        vehicle_age_years: float
    ) -> None:
        """Apply IRDA depreciation to cost breakdown"""
        depreciation_schedule = self.cost_db.get('irda_depreciation_schedule', {})
        age_schedule = depreciation_schedule.get('vehicle_age_depreciation', {})
        
        # Determine depreciation percentage based on age
        if vehicle_age_years < 0.5:
            dep_key = '0_to_6_months'
        elif vehicle_age_years < 1.0:
            dep_key = '6_to_12_months'
        elif vehicle_age_years < 2.0:
            dep_key = '1_to_2_years'
        elif vehicle_age_years < 3.0:
            dep_key = '2_to_3_years'
        elif vehicle_age_years < 4.0:
            dep_key = '3_to_4_years'
        elif vehicle_age_years < 5.0:
            dep_key = '4_to_5_years'
        elif vehicle_age_years < 10.0:
            dep_key = '5_to_10_years'
        else:
            dep_key = 'above_10_years'
        
        depreciation_percent = age_schedule.get(dep_key, {}).get('depreciation_percent', 0)
        
        breakdown.depreciation_percent = depreciation_percent
        breakdown.depreciation_amount = int(
            breakdown.total_with_gst * (depreciation_percent / 100)
        )
        breakdown.claim_settlement_estimate = (
            breakdown.total_with_gst - breakdown.depreciation_amount
        )
    
    # ========================================================================
    # Notes and Warnings
    # ========================================================================
    
    def _add_notes_and_warnings(
        self,
        estimate: CostEstimate,
        vehicle_info: VehicleInfo,
        base_costs: Dict[str, Any]
    ) -> None:
        """Add helpful notes and warnings to estimate"""
        
        # Add multiplier notes
        if estimate.multipliers.vehicle_segment > 1.5:
            estimate.notes.append(
                f"Luxury/premium vehicle segment increases costs by {(estimate.multipliers.vehicle_segment - 1) * 100:.0f}%"
            )
        
        if estimate.multipliers.brand > 2.0:
            estimate.notes.append(
                f"Premium brand parts cost {estimate.multipliers.brand:.1f}x standard parts"
            )
        
        if estimate.multipliers.regional > 1.2:
            estimate.notes.append(
                f"Metro city labor rates are {(estimate.multipliers.regional - 1) * 100:.0f}% higher"
            )
        
        # Add depreciation note
        if estimate.breakdown.depreciation_percent > 0:
            estimate.notes.append(
                f"IRDA depreciation of {estimate.breakdown.depreciation_percent}% applied based on vehicle age"
            )
        
        # Add warnings for high costs
        if estimate.breakdown.total_with_gst > 50000:
            estimate.warnings.append(
                "High repair cost - consider total loss assessment if vehicle value is low"
            )
        
        # Add part-specific notes
        part = base_costs.get('part', '')
        if 'glass' in part or 'windscreen' in estimate.damage_type.lower():
            estimate.notes.append("Glass parts have 0% depreciation as per IRDA guidelines")
        
        if 'headlight' in estimate.damage_type.lower() or 'taillight' in estimate.damage_type.lower():
            estimate.notes.append("Light assembly costs vary significantly based on technology (Halogen/LED/Matrix)")
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def get_supported_damage_types(self) -> List[str]:
        """Get list of all supported damage types"""
        return list(self.cost_db.get('damage_costs', {}).keys())
    
    def get_vehicle_segments(self) -> Dict[str, Any]:
        """Get all vehicle segments with details"""
        return self.cost_db.get('vehicle_segments', {})
    
    def get_brand_categories(self) -> Dict[str, Any]:
        """Get all brand categories with multipliers"""
        return self.cost_db.get('brand_cost_multipliers', {})
    
    def get_database_metadata(self) -> Dict[str, Any]:
        """Get cost database metadata"""
        return self.cost_db.get('metadata', {})


# ============================================================================
# Convenience Functions
# ============================================================================

def create_vehicle_info_from_dict(data: Dict[str, Any]) -> VehicleInfo:
    """Create VehicleInfo from dictionary"""
    return VehicleInfo(
        brand=data.get('brand', 'Unknown'),
        model=data.get('model'),
        segment=data.get('segment', 'hatchback'),
        age_years=data.get('age_years', 0.0),
        paint_type=data.get('paint_type', 'standard_solid'),
        ex_showroom_price=data.get('ex_showroom_price'),
        vehicle_type=data.get('vehicle_type', 'car')
    )


# ============================================================================
# Module-level instance (singleton pattern)
# ============================================================================

_estimator_instance: Optional[EnhancedCostEstimator] = None


def get_cost_estimator() -> EnhancedCostEstimator:
    """Get singleton instance of cost estimator"""
    global _estimator_instance
    
    if _estimator_instance is None:
        _estimator_instance = EnhancedCostEstimator()
    
    return _estimator_instance
