"""
Enhanced ICVE Calculation Task V2.0

Integrates with EnhancedCostEstimator for comprehensive cost estimation with:
- Vehicle segment and brand multipliers
- Regional labor rate adjustments
- IRDA-compliant depreciation
- Technology variant pricing
- GST calculations (28% parts, 18% labor)
- Multi-damage aggregation

Author: InsurAI Team
Version: 2.0
Date: 2026-01-27
"""

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime

from app.models.base import SessionLocal
from app.models.claim import Claim
from app.models.damage import DamageDetection
from app.models.icve import ICVEEstimate, ICVELineItem
from app.models.policy import Policy
from app.services.cost_estimator_v2 import (
    get_cost_estimator,
    VehicleInfo,
    CostEstimate
)

logger = get_task_logger(__name__)


def extract_vehicle_info_from_claim(claim: Claim, db: Session) -> VehicleInfo:
    """
    Extract vehicle information from claim and policy.
    
    Args:
        claim: Claim object
        db: Database session
        
    Returns:
        VehicleInfo object for cost estimation
    """
    # Get policy
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    
    if not policy:
        logger.warning(f"No policy found for claim {claim.id}, using defaults")
        return VehicleInfo(
            brand="Maruti Suzuki",
            model="Swift",
            segment="hatchback",
            age_years=2.0,
            paint_type="standard_solid",
            vehicle_type="car"
        )
    
    # Extract vehicle info
    brand = policy.vehicle_make or "Maruti Suzuki"
    model = policy.vehicle_model or "Swift"
    
    # Calculate vehicle age
    current_year = datetime.now().year
    vehicle_year = policy.vehicle_year or (current_year - 2)
    age_years = max(0.0, float(current_year - vehicle_year))
    
    # Determine segment from brand and model
    segment = determine_vehicle_segment(brand, model)
    
    # Determine vehicle type (car, motorcycle, truck, etc.)
    vehicle_type = determine_vehicle_type(brand, model)
    
    # Default paint type (could be enhanced with actual data)
    paint_type = "standard_solid"
    
    # Get IDV for ex-showroom price estimation
    ex_showroom_price = int(policy.idv) if policy.idv else None
    
    return VehicleInfo(
        brand=brand,
        model=model,
        segment=segment,
        age_years=age_years,
        paint_type=paint_type,
        ex_showroom_price=ex_showroom_price,
        vehicle_type=vehicle_type
    )


def determine_vehicle_segment(brand: str, model: str) -> str:
    """
    Determine vehicle segment from brand and model.
    
    Args:
        brand: Vehicle brand
        model: Vehicle model
        
    Returns:
        Segment name (hatchback, compact_suv, etc.)
    """
    brand_lower = brand.lower()
    model_lower = model.lower()
    
    # Micro segment
    if any(x in model_lower for x in ["alto", "kwid", "s-presso"]):
        return "micro"
    
    # Hatchback segment
    if any(x in model_lower for x in ["swift", "i20", "baleno", "tiago", "altroz", "polo", "jazz"]):
        return "hatchback"
    
    # Compact sedan
    if any(x in model_lower for x in ["dzire", "aura", "amaze", "tigor", "aspire"]):
        return "compact_sedan"
    
    # Mid-size sedan
    if any(x in model_lower for x in ["verna", "city", "virtus", "slavia", "ciaz"]):
        return "sedan"
    
    # Compact SUV
    if any(x in model_lower for x in ["nexon", "venue", "sonet", "brezza", "xuv300", "punch", "exter", "fronx"]):
        return "compact_suv"
    
    # Mid-size SUV
    if any(x in model_lower for x in ["creta", "seltos", "harrier", "hector", "xuv700", "taigun", "kushaq", "astor"]):
        return "midsize_suv"
    
    # Full-size SUV
    if any(x in model_lower for x in ["fortuner", "endeavour", "scorpio", "safari", "alcazar"]):
        return "fullsize_suv"
    
    # Luxury
    if any(x in brand_lower for x in ["mercedes", "bmw", "audi", "lexus", "volvo", "jaguar", "land rover"]):
        return "luxury"
    
    # Super luxury
    if any(x in brand_lower for x in ["rolls royce", "bentley", "lamborghini", "ferrari", "porsche", "maserati"]):
        return "super_luxury"
    
    # Default to hatchback
    return "hatchback"


def determine_vehicle_type(brand: str, model: str) -> str:
    """
    Determine vehicle type (car, motorcycle, truck, etc.).
    
    Args:
        brand: Vehicle brand
        model: Vehicle model
        
    Returns:
        Vehicle type
    """
    brand_lower = brand.lower()
    model_lower = model.lower()
    
    # Auto-rickshaws (check first before motorcycles)
    if any(x in model_lower for x in ["auto", "rickshaw", "ape", "alfa", "three wheel"]):
        return "threewheel"
    
    # Motorcycles - check brand and model
    motorcycle_brands = ["hero", "bajaj", "tvs", "yamaha", "royal enfield", "ktm", "kawasaki", "ducati", "triumph", "harley"]
    
    # Special handling for Honda and Suzuki (both make cars and motorcycles)
    if "honda" in brand_lower and not any(x in model_lower for x in ["city", "amaze", "civic", "accord", "cr-v", "wr-v"]):
        motorcycle_brands.append("honda")
    if "suzuki" in brand_lower and "maruti" not in brand_lower:
        motorcycle_brands.append("suzuki")
    
    if any(x in brand_lower for x in motorcycle_brands):
        # Economy motorcycles/scooters
        if any(x in model_lower for x in ["splendor", "platina", "activa", "jupiter", "access", "pleasure"]):
            return "motorbike_economy"
        # Superbikes
        elif any(x in model_lower for x in ["ninja", "r15", "rc", "panigale", "hayabusa", "cbr", "gsxr"]):
            return "motorbike_superbike"
        # Premium motorcycles (default for motorcycle brands)
        else:
            return "motorbike_premium"
    
    # Vans
    if any(x in model_lower for x in ["ertiga", "carens", "innova", "marazzo", "xl6"]):
        return "van_passenger"
    if any(x in model_lower for x in ["eeco", "ace", "supro", "dost"]):
        return "van_cargo"
    
    # Buses
    if any(x in model_lower for x in ["traveller", "winger", "tourister"]):
        return "bus_mini"
    if any(x in brand_lower for x in ["ashok leyland", "tata motors"]) and "bus" in model_lower:
        return "bus_large"
    
    # Trucks
    if any(x in model_lower for x in ["pickup", "bolero", "ace gold"]):
        return "truck_light"
    if any(x in model_lower for x in ["407", "eicher", "bharatbenz"]):
        return "truck_medium"
    if any(x in model_lower for x in ["prima", "captain", "truck"]):
        return "truck_heavy"
    
    # Default to car
    return "car"


def classify_damage_severity(damage: DamageDetection) -> str:
    """
    Classify damage severity based on confidence and bounding box area.
    
    Args:
        damage: DamageDetection object
        
    Returns:
        Severity level: "minor", "moderate", or "severe"
    """
    confidence = damage.confidence or 0.5
    
    # Calculate bounding box area if available
    bbox_area = 0
    if damage.bbox:
        try:
            # bbox format: [x, y, width, height]
            bbox_area = damage.bbox[2] * damage.bbox[3]
        except (IndexError, TypeError):
            bbox_area = 0
    
    # Severity thresholds from cost database
    if bbox_area < 20000 and confidence < 0.75:
        return "minor"
    elif bbox_area < 50000 and confidence < 0.9:
        return "moderate"
    else:
        return "severe"


def map_damage_type_to_cost_db(damage_type: str) -> str:
    """
    Map detected damage type to cost database damage type.
    
    Args:
        damage_type: Detected damage type from model
        
    Returns:
        Cost database damage type key
    """
    damage_type_lower = damage_type.lower().replace("_", "-")
    
    # Direct mappings
    damage_mapping = {
        "dent": "dent",
        "scratch": "scratch",
        "crack": "scratch",  # Map crack to scratch for now
        "glass-shatter": "Front-Windscreen-Damage",
        "tear": "scratch",
        "bumper-damage": "front-bumper-dent",
        "misaligned": "dent",
        
        # Specific mappings from cost database
        "front-bumper-dent": "front-bumper-dent",
        "front-bumper-scratch": "front-bumper-scratch",
        "rear-bumper-dent": "rear-bumper-dent",
        "rear-bumper-scratch": "rear-bumper-scratch",
        "doorouter-dent": "doorouter-dent",
        "doorouter-scratch": "doorouter-scratch",
        "bonnet-dent": "bonnet-dent",
        "fender-dent": "fender-dent",
        "roof-dent": "roof-dent",
        "quaterpanel-dent": "quaterpanel-dent",
        "pillar-dent": "pillar-dent",
        "headlight-damage": "Headlight-Damage",
        "taillight-damage": "Taillight-Damage",
        "front-windscreen-damage": "Front-Windscreen-Damage",
        "rear-windscreen-damage": "Rear-windscreen-Damage",
        "sidemirror-damage": "Sidemirror-Damage",
        "rust": "rust",
        "rubber-puncture": "rubber-puncture",
        "alloy-wheel-damage": "alloy-wheel-damage",
        "underbody-damage": "underbody-damage",
    }
    
    return damage_mapping.get(damage_type_lower, "dent")


def determine_location_tier(claim: Claim) -> str:
    """
    Determine city tier from claim location.
    
    Args:
        claim: Claim object
        
    Returns:
        Location tier: "metro_cities", "tier1_cities", "tier2_cities", or "tier3_cities_rural"
    """
    # This could be enhanced with actual location data from claim
    # For now, default to tier2 (baseline)
    return "tier2_cities"


@shared_task(name="app.tasks.icve_calculation_v2.calculate_icve_v2")
def calculate_icve_v2(claim_id: str) -> Dict[str, Any]:
    """
    Calculate enhanced ICVE estimate for claim (P0 Lock 6).
    
    Uses EnhancedCostEstimator with:
    - Vehicle segment and brand multipliers
    - Regional labor rate adjustments
    - IRDA-compliant depreciation
    - Technology variant pricing
    - GST calculations
    
    Args:
        claim_id: Claim ID
        
    Returns:
        Dict with status and estimate details
    """
    logger.info(f"Starting enhanced ICVE calculation for claim {claim_id}")
    db = SessionLocal()
    
    try:
        # Get claim
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            logger.error(f"Claim {claim_id} not found")
            return {"status": "failed", "error": "Claim not found"}
        
        # Get damages
        damages = db.query(DamageDetection).filter(
            DamageDetection.claim_id == claim_id
        ).all()
        
        if not damages:
            logger.warning(f"No damages found for claim {claim_id}")
            # Create zero estimate
            return create_zero_estimate(claim_id, db)
        
        # Extract vehicle information
        vehicle_info = extract_vehicle_info_from_claim(claim, db)
        logger.info(f"Vehicle: {vehicle_info.brand} {vehicle_info.model} ({vehicle_info.segment}), Age: {vehicle_info.age_years} years")
        
        # Get cost estimator
        estimator = get_cost_estimator()
        
        # Determine location tier
        location = determine_location_tier(claim)
        
        # Process each damage
        damage_estimates: List[CostEstimate] = []
        
        for damage in damages:
            # Get damage type
            d_type = damage.damage_type.value if hasattr(damage.damage_type, 'value') else str(damage.damage_type)
            
            # Map to cost database damage type
            cost_db_damage_type = map_damage_type_to_cost_db(d_type)
            
            # Classify severity
            severity = classify_damage_severity(damage)
            
            logger.info(f"Processing damage: {d_type} → {cost_db_damage_type} ({severity})")
            
            # Estimate cost
            try:
                estimate = estimator.estimate_damage_cost(
                    damage_type=cost_db_damage_type,
                    severity=severity,
                    vehicle_info=vehicle_info,
                    location=location,
                    workshop_type="local_fka_garage"  # Default to local garage
                )
                
                # Add damage ID to estimate
                estimate.notes.append(f"Damage ID: {damage.id}")
                estimate.notes.append(f"Original type: {d_type}")
                estimate.notes.append(f"Confidence: {damage.confidence:.2f}")
                
                damage_estimates.append(estimate)
                
            except Exception as e:
                logger.error(f"Failed to estimate cost for damage {damage.id}: {e}")
                # Continue with other damages
                continue
        
        if not damage_estimates:
            logger.warning(f"No valid damage estimates for claim {claim_id}")
            return create_zero_estimate(claim_id, db)
        
        # Aggregate estimates
        total_result = aggregate_damage_estimates(damage_estimates, vehicle_info)
        
        # Create ICVE estimate record
        estimate_id = str(uuid.uuid4())
        
        icve_estimate = ICVEEstimate(
            id=estimate_id,
            claim_id=claim_id,
            icve_rule_version="v2.0.0-enhanced",
            currency="INR",
            parts_subtotal=total_result["parts_subtotal"],
            labour_subtotal=total_result["labour_subtotal"],
            tax_total=total_result["gst_total"],
            depreciation_amount=total_result["depreciation_amount"],
            total_estimate=total_result["claim_settlement"]
        )
        
        db.add(icve_estimate)
        
        # Create line items
        line_items = create_line_items(estimate_id, damage_estimates, total_result)
        db.add_all(line_items)
        
        # Set P0 lock
        if not claim.p0_locks:
            claim.p0_locks = {}
        
        locks = dict(claim.p0_locks)
        locks["icve_estimate_generated"] = True
        claim.p0_locks = locks
        flag_modified(claim, "p0_locks")
        
        db.commit()
        
        logger.info(f"Enhanced ICVE calculation complete for {claim_id}")
        logger.info(f"  - Total before depreciation: ₹{total_result['total_with_gst']:,.2f}")
        logger.info(f"  - Depreciation ({total_result['depreciation_percent']}%): ₹{total_result['depreciation_amount']:,.2f}")
        logger.info(f"  - Claim settlement: ₹{total_result['claim_settlement']:,.2f}")
        
        return {
            "status": "completed",
            "claim_id": claim_id,
            "total_amount": float(total_result["claim_settlement"]),
            "line_items": len(line_items),
            "damages_processed": len(damage_estimates),
            "vehicle_segment": vehicle_info.segment,
            "vehicle_brand": vehicle_info.brand,
            "depreciation_percent": total_result["depreciation_percent"]
        }
        
    except Exception as e:
        logger.error(f"Enhanced ICVE calculation failed: {e}", exc_info=True)
        db.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


def aggregate_damage_estimates(
    estimates: List[CostEstimate],
    vehicle_info: VehicleInfo
) -> Dict[str, Any]:
    """
    Aggregate multiple damage estimates into total.
    
    Args:
        estimates: List of CostEstimate objects
        vehicle_info: Vehicle information
        
    Returns:
        Dict with aggregated totals
    """
    total_parts = 0
    total_labor = 0
    total_gst_parts = 0
    total_gst_labor = 0
    
    for estimate in estimates:
        total_parts += estimate.breakdown.subtotal_parts
        total_labor += estimate.breakdown.subtotal_labor
        total_gst_parts += estimate.breakdown.gst_on_parts
        total_gst_labor += estimate.breakdown.gst_on_labor
    
    subtotal = total_parts + total_labor
    gst_total = total_gst_parts + total_gst_labor
    total_with_gst = subtotal + gst_total
    
    # Apply depreciation (use first estimate's depreciation percent)
    depreciation_percent = estimates[0].breakdown.depreciation_percent if estimates else 0
    depreciation_amount = int(total_with_gst * depreciation_percent / 100)
    claim_settlement = total_with_gst - depreciation_amount
    
    return {
        "parts_subtotal": int(total_parts),
        "labour_subtotal": int(total_labor),
        "subtotal": int(subtotal),
        "gst_parts": int(total_gst_parts),
        "gst_labor": int(total_gst_labor),
        "gst_total": int(gst_total),
        "total_with_gst": int(total_with_gst),
        "depreciation_percent": depreciation_percent,
        "depreciation_amount": depreciation_amount,
        "claim_settlement": int(claim_settlement)
    }


def create_line_items(
    estimate_id: str,
    damage_estimates: List[CostEstimate],
    total_result: Dict[str, Any]
) -> List[ICVELineItem]:
    """
    Create line items from damage estimates.
    
    Args:
        estimate_id: ICVE estimate ID
        damage_estimates: List of damage estimates
        total_result: Aggregated totals
        
    Returns:
        List of ICVELineItem objects
    """
    line_items = []
    
    # Add line items for each damage
    for i, estimate in enumerate(damage_estimates, 1):
        # Parts line item
        if estimate.breakdown.subtotal_parts > 0:
            line_items.append(ICVELineItem(
                id=str(uuid.uuid4()),
                icve_estimate_id=estimate_id,
                item_type="PART",
                item_name=f"Damage {i}: {estimate.damage_type} ({estimate.severity})",
                quantity=1,
                unit_price=estimate.breakdown.subtotal_parts,
                amount=estimate.breakdown.subtotal_parts,
                meta={
                    "damage_type": estimate.damage_type,
                    "severity": estimate.severity,
                    "multipliers": {
                        "segment": estimate.multipliers.vehicle_segment,
                        "brand": estimate.multipliers.brand,
                        "regional": estimate.multipliers.regional,
                        "workshop": estimate.multipliers.workshop
                    }
                }
            ))
        
        # Labor line item
        if estimate.breakdown.subtotal_labor > 0:
            line_items.append(ICVELineItem(
                id=str(uuid.uuid4()),
                icve_estimate_id=estimate_id,
                item_type="LABOUR",
                item_name=f"Labor: {estimate.damage_type} ({estimate.labor_hours}h)",
                quantity=estimate.labor_hours,
                unit_price=estimate.labor_rate_per_hour,
                amount=estimate.breakdown.subtotal_labor,
                meta={
                    "damage_type": estimate.damage_type,
                    "labor_hours": estimate.labor_hours,
                    "rate_per_hour": estimate.labor_rate_per_hour
                }
            ))
    
    # GST line item
    if total_result["gst_total"] > 0:
        line_items.append(ICVELineItem(
            id=str(uuid.uuid4()),
            icve_estimate_id=estimate_id,
            item_type="TAX",
            item_name="GST (28% on parts, 18% on labor)",
            quantity=1,
            unit_price=total_result["gst_total"],
            amount=total_result["gst_total"],
            meta={
                "gst_on_parts": total_result["gst_parts"],
                "gst_on_labor": total_result["gst_labor"]
            }
        ))
    
    # Depreciation line item
    if total_result["depreciation_amount"] > 0:
        line_items.append(ICVELineItem(
            id=str(uuid.uuid4()),
            icve_estimate_id=estimate_id,
            item_type="ADJUSTMENT",
            item_name=f"IRDA Depreciation ({total_result['depreciation_percent']}%)",
            quantity=1,
            unit_price=-total_result["depreciation_amount"],
            amount=-total_result["depreciation_amount"],
            meta={
                "depreciation_percent": total_result["depreciation_percent"],
                "irda_compliant": True
            }
        ))
    
    return line_items


def create_zero_estimate(claim_id: str, db: Session) -> Dict[str, Any]:
    """
    Create a zero estimate when no damages are found.
    
    Args:
        claim_id: Claim ID
        db: Database session
        
    Returns:
        Dict with status
    """
    estimate_id = str(uuid.uuid4())
    
    icve_estimate = ICVEEstimate(
        id=estimate_id,
        claim_id=claim_id,
        icve_rule_version="v2.0.0-enhanced",
        currency="INR",
        parts_subtotal=0,
        labour_subtotal=0,
        tax_total=0,
        total_estimate=0
    )
    
    db.add(icve_estimate)
    
    # Set P0 lock
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if claim:
        if not claim.p0_locks:
            claim.p0_locks = {}
        
        locks = dict(claim.p0_locks)
        locks["icve_estimate_generated"] = True
        claim.p0_locks = locks
        flag_modified(claim, "p0_locks")
    
    db.commit()
    
    return {
        "status": "completed",
        "claim_id": claim_id,
        "total_amount": 0.0,
        "line_items": 0,
        "damages_processed": 0,
        "note": "No damages found"
    }
