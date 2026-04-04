from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload, contains_eager
from sqlalchemy import desc
from typing import List, Optional, Any
from datetime import datetime, timedelta
from app.models.base import get_db
from app.models.user import User
from app.models.claim import Claim, ClaimStateTransition
from app.models.enums import ClaimStatus, RiskLevel
from app.models.damage import DuplicateCheckResult, DamageDetection
from app.models.icve import ICVEEstimate
from app.models.media import MediaAsset
from app.api.dependencies import get_current_surveyor
from app.services.storage import storage_service
from pydantic import BaseModel
import uuid

router = APIRouter()

# Response Schemas for Inbox
class SurveyorClaimSummary(BaseModel):
    id: uuid.UUID
    policy_id: str
    customer_name: Optional[str]
    vehicle_info: Optional[str]
    status: ClaimStatus
    risk_level: RiskLevel
    submitted_at: datetime
    sla_deadline: datetime
    sla_status: str  # ON_TRACK, WARNING, BREACHED
    total_damage_cost: float
    
    class Config:
        from_attributes = True

class SurveyorInboxResponse(BaseModel):
    claims: List[SurveyorClaimSummary]
    total: int
    page: int
    page_size: int

# Response Schema for Detail
class SurveyorClaimDetailResponse(BaseModel):
    claim: Any 
    damages: List[Any]
    icve: Optional[Any]
    duplicate_check: Optional[Any]
    quality_gate: Optional[Any]
    report: Optional[Any]
    photos: List[Any] 
    
    class Config:
        from_attributes = True

@router.get("/inbox", response_model=SurveyorInboxResponse)
async def get_surveyor_inbox(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[ClaimStatus] = Query(None),
    current_user: User = Depends(get_current_surveyor),
    db: Session = Depends(get_db)
):
    """
    Get claims ready for review.
    Shows both DRAFT_READY and SURVEYOR_REVIEW claims.
    Sorted by Risk Level (RED > AMBER > GREEN) then Submission Time.
    Includes SLA calculation (24 hour standard).
    """
    # Base query - show both DRAFT_READY and SURVEYOR_REVIEW claims
    query = db.query(Claim).options(
        joinedload(Claim.customer),
        selectinload(Claim.icve_estimates)
    )
    if status_filter:
        query = db.query(Claim).options(
            joinedload(Claim.customer),
            selectinload(Claim.icve_estimates)
        ).filter(Claim.status == status_filter)
    else:
        # Default: show both new claims and claims in review
        query = db.query(Claim).options(
            joinedload(Claim.customer),
            selectinload(Claim.icve_estimates)
        ).filter(
            Claim.status.in_([ClaimStatus.DRAFT_READY, ClaimStatus.SURVEYOR_REVIEW])
        )
    
    # Calculate Total
    total = query.count()
    
    # Apply eager loading to avoid N+1 queries during iteration
    query = query.options(selectinload(Claim.icve_estimates), joinedload(Claim.customer))

    # Fetch all for in-memory sorting (complex risk sorting)
    all_claims = query.all()
    
    # Risk Score Map
    risk_scores = {
        RiskLevel.RED: 3,
        RiskLevel.AMBER: 2,
        RiskLevel.GREEN: 1
    }
    
    # Sort: Risk (Desc), Submitted At (Asc - FIFO)
    sorted_claims = sorted(
        all_claims, 
        key=lambda x: (risk_scores.get(x.risk_level, 0), -(x.submitted_at.timestamp() if x.submitted_at else 0)), 
        reverse=True
    )
    
    # Pagination
    import itertools
    start = (page - 1) * page_size
    end = start + page_size
    paginated_claims = list(itertools.islice(sorted_claims, start, end))
    
    # Process for Response
    processed_claims = []
    now = datetime.utcnow()

    # Bulk fetch latest ICVE estimates
    claim_ids = [str(c.id) for c in paginated_claims]
    icves = db.query(ICVEEstimate).filter(ICVEEstimate.claim_id.in_(claim_ids)).order_by(desc(ICVEEstimate.created_at)).all() if claim_ids else []

    # Keep only the latest ICVE per claim (since they are ordered descending)
    latest_icves = {}
    for icve in icves:
        if str(icve.claim_id) not in latest_icves:
            latest_icves[str(icve.claim_id)] = icve

    for claim in paginated_claims:
        # SLA Calculation (24 hours from submission)
        submission_time = claim.submitted_at or claim.created_at
        deadline = submission_time + timedelta(hours=24)
        time_left = (deadline - now).total_seconds() / 3600 # hours
        
        if time_left < 0:
            sla_status = "BREACHED"
        elif time_left < 4:
            sla_status = "WARNING"
        else:
            sla_status = "ON_TRACK"
            
        # Get customer name
        customer_name = "Unknown"
        if claim.customer:
             customer_name = claim.customer.name or claim.customer.phone
        
        # Get estimate total
        est_amount = 0.0
        latest_icve = latest_icves.get(str(claim.id))
        if latest_icve:
             est_amount = float(latest_icve.total_estimate)
        
        processed_claims.append(SurveyorClaimSummary(
            id=claim.id,
            policy_id=claim.policy_id,
            customer_name=customer_name,
            vehicle_info="Vehicle Info",
            status=claim.status,
            risk_level=claim.risk_level,
            submitted_at=submission_time,
            sla_deadline=deadline,
            sla_status=sla_status,
            total_damage_cost=est_amount
        ))
    
    return SurveyorInboxResponse(
        claims=processed_claims,
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/claims/{claim_id}", response_model=SurveyorClaimDetailResponse)
async def get_surveyor_claim_detail(
    claim_id: str,
    current_user: User = Depends(get_current_surveyor),
    db: Session = Depends(get_db)
):
    """
    Get full claim details for surveyor review.
    Combines Claim, Damages, ICVE, Duplicate Check, and Photos.
    Transitions claim to SURVEYOR_REVIEW on first access (Work in progress state).
    """
    try:
        claim_uuid = uuid.UUID(claim_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID")

    claim = db.query(Claim).filter(Claim.id == str(claim_uuid)).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # State Transition: DRAFT_READY -> SURVEYOR_REVIEW
    if claim.status == ClaimStatus.DRAFT_READY:
        old_status = claim.status
        claim.status = ClaimStatus.SURVEYOR_REVIEW
        claim.reviewed_at = datetime.utcnow()
        
        # Log transition
        transition = ClaimStateTransition(
            claim_id=str(claim_uuid),
            from_status=old_status,
            to_status=ClaimStatus.SURVEYOR_REVIEW,
            actor_user_id=current_user.id,
            reason="Surveyor opened claim for review"
        )
        db.add(transition)
        db.commit()
        db.refresh(claim)

    # Fetch Related Data
    damages = db.query(DamageDetection).filter(DamageDetection.claim_id == str(claim_uuid)).all()
    
    icve = db.query(ICVEEstimate).filter(ICVEEstimate.claim_id == str(claim_uuid)).order_by(desc(ICVEEstimate.created_at)).first()
    
    dup_result = db.query(DuplicateCheckResult).filter(DuplicateCheckResult.claim_id == str(claim_uuid)).order_by(desc(DuplicateCheckResult.created_at)).first()
    
    photos = db.query(MediaAsset).filter(MediaAsset.claim_id == str(claim_uuid)).all()
    
    # Generate presigned URLs for photos
    processed_photos = []
    for p in photos:
        # Create a clean dict with only the fields we need
        p_dict = {
            'id': p.id,
            'claim_id': p.claim_id,
            'media_type': p.media_type.value if p.media_type else None,
            'capture_angle': p.capture_angle.value if p.capture_angle else None,
            'object_key': p.object_key,
            'content_type': p.content_type,
            'size_bytes': p.size_bytes,
            'width': p.width,
            'height': p.height,
            'uploaded_at': p.uploaded_at.isoformat() if p.uploaded_at else None,
        }
        if p.object_key:
            p_dict['presigned_url'] = storage_service.generate_presigned_url(p.object_key)
        processed_photos.append(p_dict)
    
    # Fetch Report Draft
    from app.models.report import ReportDraft
    report = db.query(ReportDraft).filter(ReportDraft.claim_id == str(claim_uuid)).order_by(desc(ReportDraft.created_at)).first()

    # Convert claim to dict
    claim_dict = {
        'id': claim.id,
        'customer_id': claim.customer_id,
        'policy_id': claim.policy_id,
        'status': claim.status.value if claim.status else None,
        'risk_level': claim.risk_level.value if claim.risk_level else None,
        'incident_date': claim.incident_date.isoformat() if claim.incident_date else None,
        'incident_description': claim.incident_description,
        'incident_location_lat': claim.incident_location_lat,
        'incident_location_lng': claim.incident_location_lng,
        'created_at': claim.created_at.isoformat() if claim.created_at else None,
        'submitted_at': claim.submitted_at.isoformat() if claim.submitted_at else None,
        'reviewed_at': claim.reviewed_at.isoformat() if claim.reviewed_at else None,
        'p0_locks': claim.p0_locks,
        'vin_hash': claim.vin_hash,
    }
    
    # Convert damages to list of dicts with cost estimates
    damages_list = []
    for d in damages:
        # Calculate estimated cost for this damage
        estimated_cost = 0
        try:
            from app.services.cost_estimator_v2 import get_cost_estimator, VehicleInfo
            from app.tasks.icve_calculation_v2 import determine_vehicle_segment, determine_vehicle_type
            from app.models.policy import Policy
            
            # Get vehicle info from policy
            policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
            if policy:
                segment = determine_vehicle_segment(policy.vehicle_make or "Unknown", policy.vehicle_model or "")
                vehicle_type = determine_vehicle_type(policy.vehicle_make or "Unknown", policy.vehicle_model or "")
                vehicle_age = float(datetime.now().year - policy.vehicle_year) if policy.vehicle_year else 0.0
                
                vehicle_info = VehicleInfo(
                    brand=policy.vehicle_make or "Unknown",
                    model=policy.vehicle_model or "Unknown",
                    segment=segment,
                    age_years=vehicle_age,
                    vehicle_type=vehicle_type
                )
                
                # Get cost estimator
                estimator = get_cost_estimator()
                
                # Map damage type to cost database format
                damage_type_key = d.damage_type.value.lower().replace('_', '-') if d.damage_type else 'other'
                severity = d.severity.value.lower() if d.severity else 'moderate'
                
                # Estimate cost
                try:
                    estimate = estimator.estimate_damage_cost(
                        damage_type=damage_type_key,
                        severity=severity,
                        vehicle_info=vehicle_info,
                        location="tier2_cities",
                        workshop_type="local_fka_garage"
                    )
                    estimated_cost = estimate.breakdown.claim_settlement_estimate
                except Exception as e:
                    # If specific damage type not found, use a default estimate based on severity
                    if severity == 'severe':
                        estimated_cost = 15000
                    elif severity == 'moderate':
                        estimated_cost = 8000
                    else:
                        estimated_cost = 3000
        except Exception as e:
            # Fallback to default estimates
            pass
        
        damages_list.append({
            'id': d.id,
            'claim_id': d.claim_id,
            'media_id': d.media_id,
            'damage_type': d.damage_type.value if d.damage_type else None,
            'severity': d.severity.value if d.severity else None,
            'vehicle_part': d.vehicle_part if d.vehicle_part else None,
            'confidence': float(d.confidence) if d.confidence else None,
            'bbox_x1': float(d.bbox_x1) if d.bbox_x1 else None,
            'bbox_y1': float(d.bbox_y1) if d.bbox_y1 else None,
            'bbox_x2': float(d.bbox_x2) if d.bbox_x2 else None,
            'bbox_y2': float(d.bbox_y2) if d.bbox_y2 else None,
            'mask_object_key': d.mask_object_key,  # Mask R-CNN segmentation mask
            'mask_url': storage_service.generate_presigned_url(d.mask_object_key) if d.mask_object_key else None,
            'cost_override': float(d.cost_override) if d.cost_override else None,
            'estimated_cost': estimated_cost,  # Add estimated cost
            'surveyor_notes': d.surveyor_notes,
            'is_ai_generated': d.is_ai_generated,
            'surveyor_modified': d.surveyor_modified,
            'surveyor_id': d.surveyor_id,
        })
    
    # Convert ICVE to dict
    icve_dict = None
    if icve:
        icve_dict = {
            'id': icve.id,
            'claim_id': icve.claim_id,
            'total_estimate': float(icve.total_estimate) if icve.total_estimate else None,
            'created_at': icve.created_at.isoformat() if icve.created_at else None,
        }
    
    # Convert duplicate check to dict
    dup_dict = None
    if dup_result:
        dup_dict = {
            'id': dup_result.id,
            'claim_id': dup_result.claim_id,
            'fraud_action': dup_result.fraud_action,
            'similarity_score': float(dup_result.similarity_score) if dup_result.similarity_score else None,
            'matched_claim_id': dup_result.matched_claim_id,
            'created_at': dup_result.created_at.isoformat() if dup_result.created_at else None,
        }
    
    # Convert report to dict
    report_dict = None
    if report:
        report_dict = {
            'id': report.id,
            'claim_id': report.claim_id,
            'report_sections': report.report_sections,
            'surveyor_version': report.surveyor_version,
            'ai_version': report.ai_version,
            'version': report.version,
            'surveyor_id': report.surveyor_id,
            'created_at': report.created_at.isoformat() if report.created_at else None,
            'updated_at': report.updated_at.isoformat() if report.updated_at else None,
        }

    return SurveyorClaimDetailResponse(
        claim=claim_dict,
        damages=damages_list,
        icve=icve_dict,
        duplicate_check=dup_dict,
        quality_gate=None,
        report=report_dict,
        photos=processed_photos
    )

@router.get("/claims/{claim_id}/duplicate-check")
async def get_duplicate_check(
    claim_id: str,
    current_user: User = Depends(get_current_surveyor),
    db: Session = Depends(get_db)
):
    """
    Get duplicate check results for a claim (P0 Lock 5 Display).
    """
    dup_result = db.query(DuplicateCheckResult).filter(
        DuplicateCheckResult.claim_id == claim_id
    ).order_by(desc(DuplicateCheckResult.created_at)).first()
    
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    
    if not dup_result:
        # Return default safe response
        return {
            "fraud_action": "PROCEED",
            "similarity_score": 0.0,
            "matched_claim_id": None,
            "risk_level": claim.risk_level.value if claim else "GREEN"
        }
    
    return {
        "fraud_action": dup_result.fraud_action,
        "similarity_score": float(dup_result.similarity_score or 0),
        "matched_claim_id": dup_result.matched_claim_id,
        "risk_level": claim.risk_level.value
    }

# Approval/Rejection Request Schema
class DecisionRequest(BaseModel):
    reason: Optional[str] = None

@router.post("/claims/{claim_id}/approve")
async def approve_claim(
    claim_id: str,
    payload: DecisionRequest,
    current_user: User = Depends(get_current_surveyor),
    db: Session = Depends(get_db)
):
    """
    Approve claim (Surveyor Only).
    Transitions to APPROVED.
    Sends WebSocket notification to customer.
    """
    try:
        claim_uuid = uuid.UUID(claim_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID")

    claim = db.query(Claim).filter(Claim.id == str(claim_uuid)).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    old_status = claim.status
    claim.status = ClaimStatus.APPROVED
    approved_amount = 0.0
    if claim.icve_estimates:
         claim.total_approved_amount = claim.icve_estimates[0].total_estimate
         approved_amount = float(claim.icve_estimates[0].total_estimate)
    
    # Audit
    transition = ClaimStateTransition(
        claim_id=str(claim_uuid),
        from_status=old_status,
        to_status=ClaimStatus.APPROVED,
        actor_user_id=current_user.id,
        reason=payload.reason or "Approved by Surveyor"
    )
    db.add(transition)
    db.commit()
    
    # Send WebSocket notification (Task 5.11.8)
    from app.websocket.broadcaster import broadcaster
    import asyncio
    try:
        asyncio.create_task(broadcaster.broadcast_claim_approved(
            claim_id=str(claim_uuid),
            surveyor_id=current_user.id,
            approved_amount=approved_amount,
            reason=payload.reason
        ))
    except Exception as e:
        print(f"WebSocket broadcast failed: {e}")
    
    # Trigger PDF generation (Task 5.11.9)
    from app.tasks.pdf_generation import generate_pdf_report_task
    try:
        generate_pdf_report_task.delay(
            claim_id=str(claim_uuid),
            surveyor_id=current_user.id,
            decision_reason=payload.reason
        )
    except Exception as e:
        print(f"PDF generation task failed to queue: {e}")
    
    return {"message": "Claim approved successfully", "status": "APPROVED"}

@router.post("/claims/{claim_id}/reject")
async def reject_claim(
    claim_id: str,
    payload: DecisionRequest,
    current_user: User = Depends(get_current_surveyor),
    db: Session = Depends(get_db)
):
    """
    Reject claim (Surveyor Only).
    Transitions to REJECTED.
    Sends WebSocket notification to customer.
    """
    try:
        claim_uuid = uuid.UUID(claim_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID")

    claim = db.query(Claim).filter(Claim.id == str(claim_uuid)).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    old_status = claim.status
    claim.status = ClaimStatus.REJECTED
    
    transition = ClaimStateTransition(
        claim_id=str(claim_uuid),
        from_status=old_status,
        to_status=ClaimStatus.REJECTED,
        actor_user_id=current_user.id,
        reason=payload.reason or "Rejected by Surveyor"
    )
    db.add(transition)
    db.commit()
    
    # Send WebSocket notification (Task 5.11.8)
    from app.websocket.broadcaster import broadcaster
    import asyncio
    try:
        asyncio.create_task(broadcaster.broadcast_claim_rejected(
            claim_id=str(claim_uuid),
            surveyor_id=current_user.id,
            reason=payload.reason or "Rejected by Surveyor"
        ))
    except Exception as e:
        print(f"WebSocket broadcast failed: {e}")
    
    return {"message": "Claim rejected", "status": "REJECTED"}

@router.post("/claims/{claim_id}/request-info")
async def request_info_claim(
    claim_id: str,
    payload: DecisionRequest,
    current_user: User = Depends(get_current_surveyor),
    db: Session = Depends(get_db)
):
    """
    Request more info (Surveyor Only).
    Transitions to NEEDS_MORE_INFO.
    Sends WebSocket notification to customer.
    """
    try:
        claim_uuid = uuid.UUID(claim_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid claim ID")

    claim = db.query(Claim).filter(Claim.id == str(claim_uuid)).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    old_status = claim.status
    claim.status = ClaimStatus.NEEDS_MORE_INFO
    
    transition = ClaimStateTransition(
        claim_id=str(claim_uuid),
        from_status=old_status,
        to_status=ClaimStatus.NEEDS_MORE_INFO,
        actor_user_id=current_user.id,
        reason=payload.reason or "Surveyor requested more info"
    )
    db.add(transition)
    db.commit()
    
    # Send WebSocket notification (Task 5.11.8)
    from app.websocket.broadcaster import broadcaster
    import asyncio
    try:
        asyncio.create_task(broadcaster.broadcast_info_requested(
            claim_id=str(claim_uuid),
            surveyor_id=current_user.id,
            reason=payload.reason or "Surveyor requested more info"
        ))
    except Exception as e:
        print(f"WebSocket broadcast failed: {e}")
    
    return {"message": "Info requested", "status": "NEEDS_MORE_INFO"}

# Damage Modification Endpoints (Task 5.6)

class DamageUpdateRequest(BaseModel):
    damage_type: Optional[str] = None
    severity: Optional[str] = None
    vehicle_part: Optional[str] = None
    cost_override: Optional[float] = None
    surveyor_notes: Optional[str] = None

class DamageCreateRequest(BaseModel):
    media_id: Optional[str] = None
    damage_type: str
    severity: str
    vehicle_part: str
    cost_override: Optional[float] = None
    surveyor_notes: Optional[str] = None
    bbox_x1: Optional[float] = 0
    bbox_y1: Optional[float] = 0
    bbox_x2: Optional[float] = 0
    bbox_y2: Optional[float] = 0

@router.put("/claims/{claim_id}/damages/{damage_id}")
async def update_damage(
    claim_id: str,
    damage_id: str,
    payload: DamageUpdateRequest,
    current_user: User = Depends(get_current_surveyor),
    db: Session = Depends(get_db)
):
    """
    Update damage detection (Surveyor Only).
    Tracks modifications for audit trail.
    Triggers ICVE recalculation.
    """
    damage = db.query(DamageDetection).filter(
        DamageDetection.id == damage_id,
        DamageDetection.claim_id == claim_id
    ).first()
    
    if not damage:
        raise HTTPException(status_code=404, detail="Damage not found")
    
    # Track modifications
    modifications = []
    if payload.damage_type and payload.damage_type != damage.damage_type:
        modifications.append(f"Type: {damage.damage_type} → {payload.damage_type}")
        damage.damage_type = payload.damage_type
    
    if payload.severity and payload.severity != damage.severity:
        modifications.append(f"Severity: {damage.severity} → {payload.severity}")
        damage.severity = payload.severity
    
    if payload.vehicle_part and payload.vehicle_part != damage.vehicle_part:
        modifications.append(f"Part: {damage.vehicle_part} → {payload.vehicle_part}")
        damage.vehicle_part = payload.vehicle_part
    
    if payload.cost_override is not None:
        modifications.append(f"Cost Override: ₹{payload.cost_override}")
        damage.cost_override = payload.cost_override
    
    if payload.surveyor_notes is not None:
        damage.surveyor_notes = payload.surveyor_notes
    
    # Mark as surveyor-modified
    damage.surveyor_modified = True
    damage.surveyor_id = current_user.id
    
    # Log audit trail
    from app.models.audit import AuditEvent
    audit = AuditEvent(
        claim_id=claim_id,
        actor_user_id=current_user.id,
        action="DAMAGE_MODIFIED",
        details={"damage_id": damage_id, "modifications": modifications}
    )
    db.add(audit)
    
    db.commit()
    db.refresh(damage)
    
    # TODO: Trigger ICVE recalculation
    # from app.tasks.icve_calculation import calculate_icve
    # calculate_icve.delay(claim_id)
    
    return {"message": "Damage updated", "damage": damage}

@router.post("/claims/{claim_id}/damages")
async def add_damage(
    claim_id: str,
    payload: DamageCreateRequest,
    current_user: User = Depends(get_current_surveyor),
    db: Session = Depends(get_db)
):
    """
    Add new damage detection (Surveyor Only).
    Creates manual damage entry.
    Triggers ICVE recalculation.
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Create new damage
    new_damage = DamageDetection(
        claim_id=claim_id,
        media_id=payload.media_id,
        damage_type=payload.damage_type,
        severity=payload.severity,
        vehicle_part=payload.vehicle_part,
        confidence=1.0,  # Manual entry = 100% confidence
        bbox_x1=payload.bbox_x1,
        bbox_y1=payload.bbox_y1,
        bbox_x2=payload.bbox_x2,
        bbox_y2=payload.bbox_y2,
        cost_override=payload.cost_override,
        surveyor_notes=payload.surveyor_notes,
        is_ai_generated=False,
        surveyor_modified=True,
        surveyor_id=current_user.id
    )
    
    db.add(new_damage)
    
    # Log audit trail
    from app.models.audit import AuditEvent
    audit = AuditEvent(
        claim_id=claim_id,
        actor_user_id=current_user.id,
        action="DAMAGE_ADDED",
        details={"damage_type": payload.damage_type, "vehicle_part": payload.vehicle_part}
    )
    db.add(audit)
    
    db.commit()
    db.refresh(new_damage)
    
    # TODO: Trigger ICVE recalculation
    # from app.tasks.icve_calculation import calculate_icve
    # calculate_icve.delay(claim_id)
    
    return {"message": "Damage added", "damage": new_damage}

@router.delete("/claims/{claim_id}/damages/{damage_id}")
async def delete_damage(
    claim_id: str,
    damage_id: str,
    current_user: User = Depends(get_current_surveyor),
    db: Session = Depends(get_db)
):
    """
    Remove damage detection (Surveyor Only).
    Soft delete or hard delete based on policy.
    Triggers ICVE recalculation.
    """
    damage = db.query(DamageDetection).filter(
        DamageDetection.id == damage_id,
        DamageDetection.claim_id == claim_id
    ).first()
    
    if not damage:
        raise HTTPException(status_code=404, detail="Damage not found")
    
    # Log audit trail before deletion
    from app.models.audit import AuditEvent
    audit = AuditEvent(
        claim_id=claim_id,
        actor_user_id=current_user.id,
        action="DAMAGE_REMOVED",
        details={"damage_id": damage_id, "damage_type": damage.damage_type, "vehicle_part": damage.vehicle_part}
    )
    db.add(audit)
    
    # Hard delete (could implement soft delete with is_deleted flag)
    db.delete(damage)
    db.commit()
    
    # TODO: Trigger ICVE recalculation
    # from app.tasks.icve_calculation import calculate_icve
    # calculate_icve.delay(claim_id)
    
    return {"message": "Damage removed"}

# Report Modification Endpoints (Task 5.9)

class ReportUpdateRequest(BaseModel):
    report_sections: List[dict]  # List of {title: str, content: str}

@router.put("/claims/{claim_id}/report")
async def update_report(
    claim_id: str,
    payload: ReportUpdateRequest,
    current_user: User = Depends(get_current_surveyor),
    db: Session = Depends(get_db)
):
    """
    Update survey report (Surveyor Only).
    Stores surveyor version separately from AI version.
    Tracks version history and modifications.
    """
    from app.models.report import ReportDraft
    
    # Get existing report
    report = db.query(ReportDraft).filter(
        ReportDraft.claim_id == claim_id
    ).order_by(desc(ReportDraft.created_at)).first()
    
    if not report:
        # Create new report if none exists
        report = ReportDraft(
            claim_id=claim_id,
            report_sections=payload.report_sections,
            surveyor_version=payload.report_sections,
            version=1,
            surveyor_id=current_user.id
        )
        db.add(report)
    else:
        # Store AI version if not already stored
        if not report.ai_version and report.report_sections:
            report.ai_version = report.report_sections
        
        # Update surveyor version
        report.surveyor_version = payload.report_sections
        report.version += 1
        report.surveyor_id = current_user.id
        report.updated_at = datetime.utcnow()
    
    # Log audit trail
    from app.models.audit import AuditEvent
    audit = AuditEvent(
        claim_id=claim_id,
        actor_user_id=current_user.id,
        action="REPORT_MODIFIED",
        details={"version": report.version, "sections_count": len(payload.report_sections)}
    )
    db.add(audit)
    
    db.commit()
    db.refresh(report)
    
    return {"message": "Report updated", "report": report}

@router.get("/claims/{claim_id}/report/history")
async def get_report_history(
    claim_id: str,
    current_user: User = Depends(get_current_surveyor),
    db: Session = Depends(get_db)
):
    """
    Get report version history (Surveyor Only).
    Returns all versions with timestamps.
    """
    from app.models.report import ReportDraft
    
    reports = db.query(ReportDraft).filter(
        ReportDraft.claim_id == claim_id
    ).order_by(desc(ReportDraft.created_at)).all()
    
    return {"versions": reports}


@router.post("/claims/{claim_id}/report/generate")
async def generate_report(
    claim_id: str,
    current_user: User = Depends(get_current_surveyor),
    db: Session = Depends(get_db)
):
    """
    Generate AI report for a claim (Surveyor Only).
    Creates initial report draft if one doesn't exist.
    """
    from app.models.report import ReportDraft
    
    # Check if report already exists
    existing = db.query(ReportDraft).filter(
        ReportDraft.claim_id == claim_id
    ).first()
    
    if existing:
        return {"message": "Report already exists", "report_id": existing.id}
    
    # Get claim
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Gather data
    damages = db.query(DamageDetection).filter(
        DamageDetection.claim_id == claim_id
    ).all()
    
    icve = db.query(ICVEEstimate).filter(
        ICVEEstimate.claim_id == claim_id
    ).order_by(desc(ICVEEstimate.created_at)).first()
    
    # Build damage descriptions
    damage_descriptions = []
    for d in damages:
        severity = d.severity.value if d.severity else 'Unknown'
        dtype = d.damage_type.value if d.damage_type else 'Damage'
        part = d.vehicle_part or 'Unknown part'
        conf = f"{float(d.confidence)*100:.0f}%" if d.confidence else 'N/A'
        damage_descriptions.append(f"• {dtype} on {part} ({severity}, Confidence: {conf})")
    
    damages_text = "\n".join(damage_descriptions) if damage_descriptions else "No damages detected."
    total_estimate = float(icve.total_estimate) if icve and icve.total_estimate else 0
    locks = claim.p0_locks or {}
    
    # Build structured report sections
    report_sections = [
        {
            "title": "Summary",
            "content": f"This claim has been processed through the AI pipeline. A total of {len(damages)} damage(s) were detected and analyzed. The estimated repair cost is ₹{total_estimate:,.0f}."
        },
        {
            "title": "Damage Assessment",
            "content": f"The following damages were identified:\n\n{damages_text}"
        },
        {
            "title": "Cost Breakdown",
            "content": f"Total Estimated Repair Cost: ₹{total_estimate:,.0f}\n\nThis estimate is based on the detected damages, vehicle type, and current market rates for parts and labor in the region."
        },
        {
            "title": "Risk Assessment",
            "content": f"Risk Level: {claim.risk_level.value if claim.risk_level else 'GREEN'}\n\nDuplicate Check: {'Passed' if locks.get('duplicate_check_completed') else 'Pending'}\nQuality Gate: {'Passed' if locks.get('quality_gate_passed') else 'Failed'}"
        },
        {
            "title": "Recommendations",
            "content": "Based on the AI analysis, the surveyor should:\n\n1. Verify the identified damages match the submitted photos\n2. Confirm the cost estimates are reasonable for the vehicle type\n3. Check for any missed damages not captured in photos\n4. Review the incident description for consistency"
        }
    ]
    
    # Build summary text for legacy draft_text field
    summary_text = f"""SURVEY REPORT

Summary:
This claim has been processed through the AI pipeline. A total of {len(damages)} damage(s) were detected and analyzed. The estimated repair cost is ₹{total_estimate:,.0f}.

Damage Assessment:
{damages_text}

Cost Breakdown:
Total Estimated Repair Cost: ₹{total_estimate:,.0f}
This estimate is based on the detected damages, vehicle type, and current market rates for parts and labor in the region.

Risk Assessment:
Risk Level: {claim.risk_level.value if claim.risk_level else 'GREEN'}
Duplicate Check: {'Passed' if locks.get('duplicate_check_completed') else 'Pending'}
Quality Gate: {'Passed' if locks.get('quality_gate_passed') else 'Failed'}

Recommendations:
Based on the AI analysis, the surveyor should:
1. Verify the identified damages match the submitted photos
2. Confirm the cost estimates are reasonable for the vehicle type
3. Check for any missed damages not captured in photos
4. Review the incident description for consistency
"""
    
    # Create report
    report = ReportDraft(
        claim_id=claim_id,
        draft_text=summary_text,
        report_sections=report_sections,
        ai_version=report_sections,
        version=1,
        surveyor_id=current_user.id,
        llm_provider="System",
        llm_model="Auto-Generated"
    )
    db.add(report)
    
    # Log audit trail
    from app.models.audit import AuditEvent
    audit = AuditEvent(
        claim_id=claim_id,
        actor_user_id=current_user.id,
        action="REPORT_GENERATED",
        details={"sections_count": len(report_sections)}
    )
    db.add(audit)
    
    db.commit()
    db.refresh(report)
    
    return {
        "message": "Report generated successfully",
        "report": {
            "id": report.id,
            "claim_id": report.claim_id,
            "report_sections": report.report_sections,
            "version": report.version,
            "created_at": report.created_at.isoformat() if report.created_at else None
        }
    }


# Epic 13.1: Overview Section Backend

class OverviewStats(BaseModel):
    total_handled: int
    approved_count: int
    rejected_count: int
    needs_info_count: int
    approval_rate: float
    avg_processing_time_hours: float
    
    class Config:
        from_attributes = True

class OverviewClaimSummary(BaseModel):
    id: uuid.UUID
    policy_id: str
    customer_name: Optional[str]
    status: ClaimStatus
    risk_level: RiskLevel
    submitted_at: datetime
    reviewed_at: Optional[datetime]
    total_damage_cost: float
    decision_reason: Optional[str]
    
    class Config:
        from_attributes = True

class OverviewResponse(BaseModel):
    stats: OverviewStats
    claims_by_status: dict  # {status: [claims]}
    total: int
    page: int
    page_size: int

@router.get("/overview", response_model=OverviewResponse)
async def get_surveyor_overview(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_surveyor),
    db: Session = Depends(get_db)
):
    """
    Get overview of claims handled by the surveyor.
    Groups claims by status (approved, rejected, needs_more_info).
    Calculates summary statistics.
    """
    # Base query - claims reviewed by this surveyor
    query = db.query(Claim).options(
        joinedload(Claim.customer),
        selectinload(Claim.icve_estimates),
        selectinload(Claim.state_transitions)
    ).filter(
        Claim.reviewed_at.isnot(None)
    )
    
    # Date range filtering
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(Claim.reviewed_at >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(Claim.reviewed_at <= end_dt)
        except ValueError:
            pass
    
    # Status filtering
    if status_filter:
        try:
            status_enum = ClaimStatus(status_filter.upper())
            query = query.filter(Claim.status == status_enum)
        except ValueError:
            pass
    
    # Apply eager loading to avoid N+1 queries during iteration
    query = query.options(selectinload(Claim.icve_estimates), joinedload(Claim.customer), selectinload(Claim.state_transitions))

    # Get all claims for statistics
    all_claims = query.all()
    total = len(all_claims)
    
    # Calculate statistics
    approved = [c for c in all_claims if c.status == ClaimStatus.APPROVED]
    rejected = [c for c in all_claims if c.status == ClaimStatus.REJECTED]
    needs_info = [c for c in all_claims if c.status == ClaimStatus.NEEDS_MORE_INFO]
    
    approval_rate: float = float((len(approved) / total * 100) if total > 0 else 0.0)
    
    # Calculate average processing time
    processing_times = []
    for claim in all_claims:
        if claim.submitted_at and claim.reviewed_at:
            diff = (claim.reviewed_at - claim.submitted_at).total_seconds() / 3600
            processing_times.append(diff)
    
    avg_processing_time: float = float(sum(processing_times) / len(processing_times) if processing_times else 0.0)
    stats = OverviewStats(
        total_handled=total,
        approved_count=len(approved),
        rejected_count=len(rejected),
        needs_info_count=len(needs_info),
        approval_rate=round(approval_rate, 2),
        avg_processing_time_hours=round(avg_processing_time, 2)
    )
    
    # Group claims by status
    claims_by_status = {
        "APPROVED": approved,
        "REJECTED": rejected,
        "NEEDS_MORE_INFO": needs_info,
        "IN_REVIEW": [c for c in all_claims if c.status == ClaimStatus.SURVEYOR_REVIEW]
    }
    
    # Pagination on filtered claims
    start = (page - 1) * page_size
    end = start + page_size
    paginated_claims = all_claims[start:end]
    
    # Process claims for response
    processed_claims = []

    # Bulk fetch latest ICVE estimates
    claim_ids = [str(c.id) for c in paginated_claims]
    icves = db.query(ICVEEstimate).filter(ICVEEstimate.claim_id.in_(claim_ids)).order_by(desc(ICVEEstimate.created_at)).all() if claim_ids else []

    # Keep only the latest ICVE per claim
    latest_icves = {}
    for icve in icves:
        if str(icve.claim_id) not in latest_icves:
            latest_icves[str(icve.claim_id)] = icve

    # Bulk fetch latest ClaimStateTransitions
    transitions = db.query(ClaimStateTransition).filter(
        ClaimStateTransition.claim_id.in_(claim_ids)
    ).order_by(desc(ClaimStateTransition.created_at)).all() if claim_ids else []

    # Keep only the latest transition per claim
    latest_transitions = {}
    for transition in transitions:
        if str(transition.claim_id) not in latest_transitions:
            latest_transitions[str(transition.claim_id)] = transition

    for claim in paginated_claims:
        # Get customer name
        customer_name = "Unknown"
        if claim.customer:
            customer_name = claim.customer.name or claim.customer.phone
        
        # Get estimate total
        est_amount = 0.0
        if claim.icve_estimates:
            latest_icve = max(claim.icve_estimates, key=lambda e: e.created_at)
            est_amount = float(latest_icve.total_estimate)
        
        # Get decision reason from last transition (optimized with eager loading)
        decision_reason = None
        if claim.state_transitions:
            last_transition = max(claim.state_transitions, key=lambda t: t.created_at)
            decision_reason = last_transition.reason

        processed_claims.append(OverviewClaimSummary(
            id=claim.id,
            policy_id=claim.policy_id,
            customer_name=customer_name,
            status=claim.status,
            risk_level=claim.risk_level,
            submitted_at=claim.submitted_at or claim.created_at,
            reviewed_at=claim.reviewed_at,
            total_damage_cost=est_amount,
            decision_reason=decision_reason
        ))
    
    # Group processed claims by status
    grouped_claims = {}
    for status_key in claims_by_status.keys():
        status_claims = [c for c in processed_claims if c.status.value == status_key]
        grouped_claims[status_key] = status_claims
    return OverviewResponse(
        stats=stats,
        claims_by_status=grouped_claims,
        total=total,
        page=page,
        page_size=page_size
    )


# Epic 13.3: Reports Section Backend

class ReportSummary(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    policy_id: str
    customer_name: Optional[str]
    status: ClaimStatus
    version: int
    created_at: datetime
    updated_at: datetime
    surveyor_modified: bool
    total_estimate: float
    
    class Config:
        from_attributes = True

class ReportsResponse(BaseModel):
    reports: List[ReportSummary]
    total: int
    page: int
    page_size: int

@router.get("/reports", response_model=ReportsResponse)
async def get_surveyor_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_surveyor),
    db: Session = Depends(get_db)
):
    """
    Get all AI-generated reports.
    Includes claim references and filtering options.
    """
    from app.models.report import ReportDraft
    
    # Base query - all reports with eager loading
    query = db.query(ReportDraft).join(Claim, ReportDraft.claim_id == Claim.id).options(
        contains_eager(ReportDraft.claim).selectinload(Claim.icve_estimates),
        contains_eager(ReportDraft.claim).joinedload(Claim.customer)
    )
    
    # Date range filtering
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(ReportDraft.created_at >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(ReportDraft.created_at <= end_dt)
        except ValueError:
            pass
    
    # Status filtering (filter by claim status)
    if status_filter:
        try:
            status_enum = ClaimStatus(status_filter.upper())
            query = query.filter(Claim.status == status_enum)
        except ValueError:
            pass
    
    # Calculate total
    total = query.count()
    
    # Pagination
    reports = query.order_by(desc(ReportDraft.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    # Process reports for response
    processed_reports = []

    # Bulk fetch ICVE estimates
    claim_ids = [str(r.claim_id) for r in reports]
    icves = db.query(ICVEEstimate).filter(ICVEEstimate.claim_id.in_(claim_ids)).order_by(desc(ICVEEstimate.created_at)).all() if claim_ids else []

    # Keep only latest ICVE per claim
    latest_icves = {}
    for icve in icves:
        if str(icve.claim_id) not in latest_icves:
            latest_icves[str(icve.claim_id)] = icve

    for report in reports:
        claim = report.claim
        if not claim:
            continue
        
        # Get customer name
        customer_name = "Unknown"
        if claim.customer:
            customer_name = claim.customer.name or claim.customer.phone
        
        # Get estimate total
        est_amount = 0.0
        if claim.icve_estimates:
            latest_icve = max(claim.icve_estimates, key=lambda e: e.created_at)
            est_amount = float(latest_icve.total_estimate)
        
        # Check if surveyor modified
        surveyor_modified = report.surveyor_version is not None
        processed_reports.append(ReportSummary(
            id=report.id,
            claim_id=uuid.UUID(report.claim_id),
            policy_id=claim.policy_id,
            customer_name=customer_name,
            status=claim.status,
            version=report.version,
            created_at=report.created_at,
            updated_at=report.updated_at,
            surveyor_modified=surveyor_modified,
            total_estimate=est_amount
        ))
    
    return ReportsResponse(
        reports=processed_reports,
        total=total,
        page=page,
        page_size=page_size
    )
