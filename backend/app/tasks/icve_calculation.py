from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session
from app.models.base import SessionLocal
from app.models.claim import Claim
from app.models.damage import DamageDetection
from app.models.icve import ICVEEstimate, ICVELineItem
from app.models.enums import DamageType
from app.services.cost_estimator_v2 import EnhancedCostEstimator, VehicleInfo
from sqlalchemy.orm.attributes import flag_modified
import uuid

logger = get_task_logger(__name__)


@shared_task(name="app.tasks.icve_calculation.calculate_icve")
def calculate_icve(claim_id: str):
    """
    Calculate ICVE estimate for claim (P0 Lock 6).
    Uses enhanced cost estimator with vehicle-specific pricing.
    """
    logger.info(f"Starting ICVE calculation for claim {claim_id}")
    db = SessionLocal()
    
    try:
        # Get claim
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")
        
        # Get vehicle type from claim extra_data (set by vehicle classification)
        vehicle_type = "car"  # Default
        if claim.extra_data and "vehicle_type" in claim.extra_data:
            vehicle_type_raw = claim.extra_data["vehicle_type"]
            # Map to cost estimator vehicle types
            vehicle_type_mapping = {
                "CAR": "car",
                "MOTORCYCLE": "motorbike_economy",
                "AUTO_RICKSHAW": "threewheel",
                "TRUCK": "truck_light",
                "BUS": "bus",
                "VAN": "van"
            }
            vehicle_type = vehicle_type_mapping.get(vehicle_type_raw, "car")
            logger.info(f"Using vehicle type: {vehicle_type} (from classification: {vehicle_type_raw})")
        else:
            logger.warning(f"No vehicle type found in claim extra_data, using default: {vehicle_type}")
        
        # Get damages
        damages = db.query(DamageDetection).filter(
            DamageDetection.claim_id == claim_id
        ).all()
        
        if not damages:
            logger.warning(f"No damages found for claim {claim_id}")
            # Create empty estimate
            estimate_id = str(uuid.uuid4())
            estimate = ICVEEstimate(
                id=estimate_id,
                claim_id=claim_id,
                icve_rule_version="v2.0.0-enhanced",
                currency="INR",
                parts_subtotal=0,
                labour_subtotal=0,
                tax_total=0,
                total_estimate=0
            )
            db.add(estimate)
            
            # Set P0 Lock
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
                "total_estimate": 0,
                "line_items": 0
            }
        
        # Create vehicle info
        vehicle_info = VehicleInfo(
            brand="Generic",  # Could be extracted from claim if available
            segment="hatchback",  # Default
            vehicle_type=vehicle_type,
            age_years=0.0  # Could be calculated from claim data
        )
        
        # Initialize enhanced cost estimator
        estimator = EnhancedCostEstimator()
        
        # Prepare damages for estimation
        damages_list = []
        for damage in damages:
            # Handle enum or string for damage type
            d_type = damage.damage_type.value if hasattr(damage.damage_type, 'value') else str(damage.damage_type)
            
            # Map damage type to part name
            part_mapping = {
                "DENT": "bumper",
                "SCRATCH": "door",
                "CRACK": "panel",
                "GLASS_SHATTER": "windshield",
                "TEAR": "seat",
                "BUMPER_DAMAGE": "bumper",
                "MISALIGNED": "panel",
                "LAMP_BROKEN": "headlight",
                "MISSING_PART": "grille",
                "OTHER": "panel"
            }
            
            part_name = part_mapping.get(d_type.upper(), "panel")
            
            # Determine severity
            severity = damage.severity if damage.severity else "MODERATE"
            
            damages_list.append({
                "damage_id": str(damage.id),
                "part": part_name,
                "damage_type": d_type,
                "severity": severity,
                "confidence": float(damage.confidence) if damage.confidence else 0.8
            })
        
        # Calculate estimate using estimate_damage_cost for each damage
        damage_details = []
        total_parts = 0
        total_labor = 0
        total_gst = 0
        
        for damage_info in damages_list:
            try:
                # Call estimate_damage_cost for each damage
                estimate = estimator.estimate_damage_cost(
                    damage_type=damage_info["part"],  # Use part as damage type
                    severity=damage_info["severity"].lower(),  # "minor", "moderate", "severe"
                    vehicle_info=vehicle_info,
                    location="tier2_cities",
                    workshop_type="local_fka_garage"
                )
                
                # Extract costs from estimate
                breakdown = estimate.breakdown
                damage_details.append({
                    "damage_id": damage_info["damage_id"],
                    "part": damage_info["part"],
                    "damage_type": damage_info["damage_type"],
                    "severity": damage_info["severity"],
                    "part_cost": breakdown.subtotal_parts,
                    "labor_cost": breakdown.subtotal_labor,
                    "labor_hours": estimate.labor_hours,
                    "total_cost": breakdown.subtotal_before_gst
                })
                
                total_parts += breakdown.subtotal_parts
                total_labor += breakdown.subtotal_labor
                
            except Exception as e:
                logger.warning(f"Failed to estimate cost for damage {damage_info['damage_id']}: {e}")
                # Add zero-cost entry
                damage_details.append({
                    "damage_id": damage_info["damage_id"],
                    "part": damage_info["part"],
                    "damage_type": damage_info["damage_type"],
                    "severity": damage_info["severity"],
                    "part_cost": 0,
                    "labor_cost": 0,
                    "labor_hours": 0,
                    "total_cost": 0
                })
        
        # Calculate GST (18%)
        subtotal = total_parts + total_labor
        total_gst = int(subtotal * 0.18)
        total_with_gst = subtotal + total_gst
        
        # Build result in expected format
        from typing import Dict, Any
        estimate_result: Dict[str, Any] = {
            "damage_details": damage_details,
            "cost_breakdown": {
                "subtotal_parts": total_parts,
                "subtotal_labor": total_labor,
                "subtotal_before_gst": subtotal,
                "total_gst": total_gst,
                "total_with_gst": total_with_gst
            }
        }
        
        # Create Estimate Record
        estimate_id = str(uuid.uuid4())
        
        # Extract totals from result
        cost_breakdown = estimate_result.get("cost_breakdown", {})
        total_estimate = cost_breakdown.get("total_with_gst", 0)
        parts_subtotal = cost_breakdown.get("subtotal_parts", 0)
        labour_subtotal = cost_breakdown.get("subtotal_labor", 0)
        tax_total = cost_breakdown.get("total_gst", 0)
        
        estimate = ICVEEstimate(
            id=estimate_id,
            claim_id=claim_id,
            icve_rule_version="v2.0.0-enhanced",
            currency="INR",
            parts_subtotal=parts_subtotal,
            labour_subtotal=labour_subtotal,
            tax_total=tax_total,
            total_estimate=total_estimate
        )
        
        db.add(estimate)
        
        # Create line items from damage details
        line_items = []
        for damage_detail in estimate_result.get("damage_details", []):
            # Part cost line item
            if damage_detail.get("part_cost", 0) > 0:
                line_items.append(ICVELineItem(
                    id=str(uuid.uuid4()),
                    icve_estimate_id=estimate_id,
                    item_type="PART",
                    item_name=f"{damage_detail.get('part', 'Part')} - {damage_detail.get('damage_type', 'Repair')}",
                    quantity=1,
                    unit_price=damage_detail.get("part_cost", 0),
                    amount=damage_detail.get("part_cost", 0),
                    meta={"damage_id": damage_detail.get("damage_id")}
                ))
            
            # Labor cost line item
            if damage_detail.get("labor_cost", 0) > 0:
                line_items.append(ICVELineItem(
                    id=str(uuid.uuid4()),
                    icve_estimate_id=estimate_id,
                    item_type="LABOUR",
                    item_name=f"Labor: {damage_detail.get('part', 'Part')}",
                    quantity=damage_detail.get("labor_hours", 1),
                    unit_price=damage_detail.get("labor_cost", 0) / max(damage_detail.get("labor_hours", 1), 1),
                    amount=damage_detail.get("labor_cost", 0),
                    meta={"damage_id": damage_detail.get("damage_id")}
                ))
        
        # GST line item
        if tax_total > 0:
            line_items.append(ICVELineItem(
                id=str(uuid.uuid4()),
                icve_estimate_id=estimate_id,
                item_type="TAX",
                item_name="GST (18%)",
                quantity=1,
                unit_price=tax_total,
                amount=tax_total
            ))
        
        db.add_all(line_items)
        
        # Set P0 Lock
        if not claim.p0_locks:
            claim.p0_locks = {}
        
        locks = dict(claim.p0_locks)
        locks["icve_estimate_generated"] = True
        claim.p0_locks = locks
        flag_modified(claim, "p0_locks")
        
        db.commit()
        
        logger.info(f"ICVE calculation complete for {claim_id}. Total: ₹{total_estimate:,.2f} (Vehicle: {vehicle_type})")
        
        return {
            "status": "completed",
            "claim_id": claim_id,
            "total_estimate": float(total_estimate),
            "line_items": len(line_items),
            "vehicle_type": vehicle_type
        }
        
    except Exception as e:
        logger.error(f"ICVE calculation failed: {e}", exc_info=True)
        db.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
