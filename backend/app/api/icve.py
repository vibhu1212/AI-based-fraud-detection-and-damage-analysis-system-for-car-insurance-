"""
ICVE (Insurance Cost Valuation Engine) API Endpoints

Provides access to cost estimates with detailed breakdowns including:
- Vehicle segment and brand multipliers
- Regional labor rate adjustments
- IRDA-compliant depreciation
- Technology variant pricing
- GST calculations
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from app.models.base import get_db
from app.models.user import User
from app.models.claim import Claim
from app.models.icve import ICVEEstimate, ICVELineItem
from app.models.policy import Policy
from app.models.damage import DamageDetection
from app.api.dependencies import get_current_user
from app.services.cost_estimator_v2 import get_cost_estimator, VehicleInfo
from pydantic import BaseModel, Field

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================

class MultipliersResponse(BaseModel):
    """Multipliers applied to cost calculation"""
    vehicle_segment: float = Field(..., description="Vehicle segment multiplier (0.7x to 6.0x)")
    vehicle_type: float = Field(..., description="Vehicle type multiplier")
    brand: float = Field(..., description="Brand category multiplier (1.0x to 6.0x)")
    regional: float = Field(..., description="Regional labor rate multiplier (0.8x to 1.5x)")
    workshop: float = Field(..., description="Workshop type multiplier (0.6x to 1.8x)")
    paint_type: float = Field(..., description="Paint type multiplier")
    technology_variant: float = Field(..., description="Technology variant multiplier")
    combined: float = Field(..., description="Combined multiplier")


class CostBreakdownResponse(BaseModel):
    """Detailed cost breakdown"""
    parts_subtotal: int = Field(..., description="Parts cost before GST")
    labour_subtotal: int = Field(..., description="Labor cost before GST")
    subtotal_before_gst: int = Field(..., description="Total before GST")
    gst_on_parts: int = Field(..., description="GST on parts (28%)")
    gst_on_labor: int = Field(..., description="GST on labor (18%)")
    total_gst: int = Field(..., description="Total GST amount")
    total_with_gst: int = Field(..., description="Total including GST")
    depreciation_percent: int = Field(..., description="IRDA depreciation percentage")
    depreciation_amount: int = Field(..., description="Depreciation amount")
    claim_settlement_estimate: int = Field(..., description="Final settlement amount")


class LineItemResponse(BaseModel):
    """ICVE line item"""
    id: str
    item_type: str = Field(..., description="PART, LABOUR, TAX, ADJUSTMENT")
    item_name: str
    quantity: float
    unit_price: float
    amount: float
    meta: Optional[Dict[str, Any]] = None


class ICVEEstimateResponse(BaseModel):
    """Complete ICVE estimate with breakdown"""
    id: str
    claim_id: str
    icve_rule_version: str
    currency: str
    
    # Vehicle information
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_segment: Optional[str] = None
    vehicle_age_years: Optional[float] = None
    
    # Cost breakdown
    breakdown: CostBreakdownResponse
    
    # Multipliers (if available in meta)
    multipliers: Optional[MultipliersResponse] = None
    
    # Line items
    line_items: List[LineItemResponse]
    
    # Metadata
    location: Optional[str] = None
    workshop_type: Optional[str] = None
    damages_processed: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class VehicleSegmentInfo(BaseModel):
    """Vehicle segment information"""
    segment_key: str
    display_name: str
    base_multiplier: float
    ex_showroom_range: Dict[str, int]
    examples: List[str]
    description: str


class BrandCategoryInfo(BaseModel):
    """Brand category information"""
    category_key: str
    brands: List[str]
    parts_multiplier: float
    labor_multiplier: float
    spare_parts_availability: str
    notes: str


class EstimatePreviewRequest(BaseModel):
    """Request for cost estimate preview"""
    damage_type: str = Field(..., description="Damage type (e.g., 'front-bumper-dent')")
    severity: str = Field(..., description="Severity: minor, moderate, or severe")
    vehicle_brand: str = Field(..., description="Vehicle brand (e.g., 'Maruti Suzuki')")
    vehicle_model: Optional[str] = Field(None, description="Vehicle model (e.g., 'Swift')")
    vehicle_age_years: float = Field(0.0, description="Vehicle age in years")
    location: str = Field("tier2_cities", description="Location tier")
    workshop_type: str = Field("local_fka_garage", description="Workshop type")


class EstimatePreviewResponse(BaseModel):
    """Cost estimate preview"""
    damage_type: str
    severity: str
    vehicle_info: Dict[str, Any]
    breakdown: CostBreakdownResponse
    multipliers: MultipliersResponse
    notes: List[str]


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/claims/{claim_id}/icve", response_model=ICVEEstimateResponse)
async def get_claim_icve_estimate(
    claim_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get ICVE estimate for a claim with full breakdown.
    
    Returns:
    - Complete cost breakdown
    - Vehicle information
    - Multipliers applied
    - Line items (parts, labor, GST, depreciation)
    - Settlement amount
    """
    claim_id_str = str(claim_id)
    
    # Get claim
    claim = db.query(Claim).filter(Claim.id == claim_id_str).first()
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found"
        )
    
    # Check access (customer can see their own, surveyor can see assigned)
    if current_user.role == "customer" and claim.customer_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this claim"
        )
    
    # Get latest ICVE estimate
    icve = db.query(ICVEEstimate).filter(
        ICVEEstimate.claim_id == claim_id_str
    ).order_by(desc(ICVEEstimate.created_at)).first()
    
    if not icve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ICVE estimate not found for this claim"
        )
    
    # Get line items
    line_items = db.query(ICVELineItem).filter(
        ICVELineItem.icve_estimate_id == icve.id
    ).all()
    
    # Get vehicle info from policy
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    vehicle_make = policy.vehicle_make if policy else None
    vehicle_model = policy.vehicle_model if policy else None
    vehicle_age = None
    if policy and policy.vehicle_year:
        vehicle_age = float(datetime.now().year - policy.vehicle_year)
    
    # Get damages count
    damages_count = db.query(DamageDetection).filter(
        DamageDetection.claim_id == claim_id_str
    ).count()
    
    # Build breakdown (convert Decimal to float for calculations)
    parts_subtotal = float(icve.parts_subtotal) if icve.parts_subtotal else 0.0
    labour_subtotal = float(icve.labour_subtotal) if icve.labour_subtotal else 0.0
    tax_total = float(icve.tax_total) if icve.tax_total else 0.0
    depreciation_amount = float(icve.depreciation_amount) if icve.depreciation_amount else 0.0
    total_estimate = float(icve.total_estimate) if icve.total_estimate else 0.0
    
    # Calculate GST components
    gst_on_parts = parts_subtotal * 0.28  # 28% on parts
    gst_on_labor = labour_subtotal * 0.18  # 18% on labor
    subtotal_before_gst = parts_subtotal + labour_subtotal
    total_with_gst = parts_subtotal + labour_subtotal + tax_total
    
    # Calculate depreciation percentage
    if depreciation_amount > 0 and total_with_gst > 0:
        depreciation_percent = int((depreciation_amount / total_with_gst) * 100)
    else:
        depreciation_percent = 0
    
    breakdown = CostBreakdownResponse(
        parts_subtotal=int(parts_subtotal),
        labour_subtotal=int(labour_subtotal),
        subtotal_before_gst=int(subtotal_before_gst),
        gst_on_parts=int(gst_on_parts),
        gst_on_labor=int(gst_on_labor),
        total_gst=int(tax_total),
        total_with_gst=int(total_with_gst),
        depreciation_percent=depreciation_percent,
        depreciation_amount=int(depreciation_amount),
        claim_settlement_estimate=int(total_estimate)
    )
    
    # Extract multipliers from line items meta (if available)
    multipliers = None
    for item in line_items:
        if item.meta and "multipliers" in item.meta:
            m = item.meta["multipliers"]
            multipliers = MultipliersResponse(
                vehicle_segment=m.get("segment", 1.0),
                vehicle_type=m.get("vehicle_type", 1.0),
                brand=m.get("brand", 1.0),
                regional=m.get("regional", 1.0),
                workshop=m.get("workshop", 1.0),
                paint_type=1.0,
                technology_variant=1.0,
                combined=m.get("segment", 1.0) * m.get("brand", 1.0) * m.get("regional", 1.0) * m.get("workshop", 1.0)
            )
            break
    
    # Build response
    return ICVEEstimateResponse(
        id=icve.id,
        claim_id=icve.claim_id,
        icve_rule_version=icve.icve_rule_version,
        currency=icve.currency,
        vehicle_make=vehicle_make,
        vehicle_model=vehicle_model,
        vehicle_segment=None,  # Could be extracted from meta
        vehicle_age_years=vehicle_age,
        breakdown=breakdown,
        multipliers=multipliers,
        line_items=[
            LineItemResponse(
                id=item.id,
                item_type=item.item_type,
                item_name=item.item_name,
                quantity=float(item.quantity),
                unit_price=float(item.unit_price),
                amount=float(item.amount),
                meta=item.meta
            )
            for item in line_items
        ],
        location=None,
        workshop_type=None,
        damages_processed=damages_count,
        created_at=icve.created_at
    )


@router.get("/vehicle-segments", response_model=List[VehicleSegmentInfo])
async def get_vehicle_segments(
    db: Session = Depends(get_db)
):
    """
    Get list of all supported vehicle segments with examples and multipliers.
    
    Returns information about:
    - Micro (Alto) - 0.7x
    - Hatchback (Swift) - 1.0x baseline
    - Compact SUV (Nexon) - 1.2x
    - Mid-Size SUV (Creta) - 1.5x
    - Luxury (BMW) - 3.5x
    - Super Luxury (Rolls Royce) - 6.0x
    - And more...
    """
    estimator = get_cost_estimator()
    segments_data = estimator.cost_db.get("vehicle_segments", {})
    
    segments = []
    for key, data in segments_data.items():
        segments.append(VehicleSegmentInfo(
            segment_key=key,
            display_name=data.get("display_name", key),
            base_multiplier=data.get("base_multiplier", 1.0),
            ex_showroom_range=data.get("ex_showroom_range", {"min": 0, "max": 0}),
            examples=data.get("examples", []),
            description=data.get("description", "")
        ))
    
    return segments


@router.get("/brand-categories", response_model=List[BrandCategoryInfo])
async def get_brand_categories(
    db: Session = Depends(get_db)
):
    """
    Get list of all brand categories with multipliers.
    
    Returns information about:
    - Domestic (Maruti, Tata) - 1.0x
    - Korean/Japanese (Hyundai, Honda) - 1.3x
    - European (VW, Skoda) - 1.6x
    - German Luxury (BMW, Mercedes) - 4.0x
    - British/Italian Exotic (Ferrari, Rolls Royce) - 6.0x
    """
    estimator = get_cost_estimator()
    brands_data = estimator.cost_db.get("brand_cost_multipliers", {})
    
    categories = []
    for key, data in brands_data.items():
        if key == "description":
            continue
        categories.append(BrandCategoryInfo(
            category_key=key,
            brands=data.get("brands", []),
            parts_multiplier=data.get("parts_multiplier", 1.0),
            labor_multiplier=data.get("labor_multiplier", 1.0),
            spare_parts_availability=data.get("spare_parts_availability", "unknown"),
            notes=data.get("notes", "")
        ))
    
    return categories


@router.get("/damage-types", response_model=List[str])
async def get_supported_damage_types(
    db: Session = Depends(get_db)
):
    """
    Get list of all supported damage types in the cost database.
    
    Returns damage types like:
    - front-bumper-dent
    - front-bumper-scratch
    - doorouter-dent
    - Headlight-Damage
    - etc.
    """
    estimator = get_cost_estimator()
    return estimator.get_supported_damage_types()


@router.post("/estimate-preview", response_model=EstimatePreviewResponse)
async def preview_cost_estimate(
    request: EstimatePreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Preview cost estimate before claim submission.
    
    Useful for:
    - Customer transparency (show estimated costs upfront)
    - Surveyor reference (quick cost lookup)
    - Testing cost calculations
    
    Does not create any database records.
    """
    estimator = get_cost_estimator()
    
    # Determine segment from brand and model
    from app.tasks.icve_calculation_v2 import determine_vehicle_segment, determine_vehicle_type
    
    segment = determine_vehicle_segment(request.vehicle_brand, request.vehicle_model or "")
    vehicle_type = determine_vehicle_type(request.vehicle_brand, request.vehicle_model or "")
    
    # Create vehicle info
    vehicle_info = VehicleInfo(
        brand=request.vehicle_brand,
        model=request.vehicle_model or "Unknown",
        segment=segment,
        age_years=request.vehicle_age_years,
        paint_type="standard_solid",
        vehicle_type=vehicle_type
    )
    
    # Estimate cost
    try:
        estimate = estimator.estimate_damage_cost(
            damage_type=request.damage_type,
            severity=request.severity,
            vehicle_info=vehicle_info,
            location=request.location,
            workshop_type=request.workshop_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to estimate cost: {str(e)}"
        )
    
    # Build response
    breakdown = CostBreakdownResponse(
        parts_subtotal=estimate.breakdown.subtotal_parts,
        labour_subtotal=estimate.breakdown.subtotal_labor,
        subtotal_before_gst=estimate.breakdown.subtotal_before_gst,
        gst_on_parts=estimate.breakdown.gst_on_parts,
        gst_on_labor=estimate.breakdown.gst_on_labor,
        total_gst=estimate.breakdown.total_gst,
        total_with_gst=estimate.breakdown.total_with_gst,
        depreciation_percent=estimate.breakdown.depreciation_percent,
        depreciation_amount=estimate.breakdown.depreciation_amount,
        claim_settlement_estimate=estimate.breakdown.claim_settlement_estimate
    )
    
    multipliers = MultipliersResponse(
        vehicle_segment=estimate.multipliers.vehicle_segment,
        vehicle_type=estimate.multipliers.vehicle_type,
        brand=estimate.multipliers.brand,
        regional=estimate.multipliers.regional,
        workshop=estimate.multipliers.workshop,
        paint_type=estimate.multipliers.paint_type,
        technology_variant=estimate.multipliers.technology_variant,
        combined=estimate.multipliers.get_combined_multiplier()
    )
    
    return EstimatePreviewResponse(
        damage_type=estimate.damage_type,
        severity=estimate.severity,
        vehicle_info={
            "brand": vehicle_info.brand,
            "model": vehicle_info.model,
            "segment": vehicle_info.segment,
            "vehicle_type": vehicle_info.vehicle_type,
            "age_years": vehicle_info.age_years
        },
        breakdown=breakdown,
        multipliers=multipliers,
        notes=estimate.notes
    )


@router.get("/metadata", response_model=Dict[str, Any])
async def get_cost_database_metadata(
    db: Session = Depends(get_db)
):
    """
    Get cost database metadata including version, sources, and coverage.
    
    Returns:
    - Database version
    - Data sources
    - Coverage statistics
    - GST rates
    - Last updated date
    """
    estimator = get_cost_estimator()
    metadata = estimator.get_database_metadata()
    
    return {
        "version": metadata.get("version"),
        "currency": metadata.get("currency"),
        "last_updated": metadata.get("last_updated"),
        "market": metadata.get("market"),
        "sources": metadata.get("sources", []),
        "gst_rate_parts": metadata.get("gst_rate_parts"),
        "gst_rate_labor": metadata.get("gst_rate_labor"),
        "coverage": {
            "damage_types": len(estimator.get_supported_damage_types()),
            "vehicle_segments": len(estimator.get_vehicle_segments()),
            "brand_categories": len(estimator.get_brand_categories())
        }
    }
