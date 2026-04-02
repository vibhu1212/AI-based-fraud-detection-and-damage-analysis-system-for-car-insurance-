"""
Claim management endpoints for customers.
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload, selectinload
from typing import List, Optional
from uuid import UUID
from datetime import date, timedelta
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import io
from app.models.base import get_db
from app.models.user import User
from app.models.claim import Claim, ClaimStateTransition
from app.models.policy import Policy
from app.models.media import MediaAsset
from app.models.enums import ClaimStatus, RiskLevel, MediaType, CaptureAngle
from app.schemas.claim import ClaimCreateRequest, ClaimResponse, ClaimListResponse, P0LocksStatus
from app.schemas.media import PhotoUploadResponse, PhotoListResponse
from app.schemas.dashboard import CustomerDashboardResponse, DashboardStats, ClaimSummary
from app.api.dependencies import get_current_customer, get_current_user
from app.services.storage import storage_service

router = APIRouter()

# File upload constraints
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/jpg"]


@router.post("", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_claim(
    request: ClaimCreateRequest,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """
    Create a new claim.
    Only customers can create claims.
    
    DEMO MODE: Policy validation is relaxed for demo purposes.
    In production, this would strictly validate policy ownership.
    """
    try:
        # DEMO MODE: Create a demo policy if none exists
        policy_id = request.policy_id
        
        if policy_id:
            # Convert UUID to string
            policy_id_str = str(policy_id)
            
            # Check if policy exists
            policy = db.query(Policy).filter(Policy.id == policy_id_str).first()
            if not policy:
                # Create a demo policy on-the-fly for demo purposes
                import itertools
                prefix = "".join(itertools.islice(str(current_user.id), 8))
                policy = Policy(
                    id=policy_id_str,  # Use string version
                    user_id=str(current_user.id),  # Ensure string
                    policy_number=f"DEMO-{prefix}",
                    insurer_name="Demo Insurance Co.",
                    vehicle_make="Demo",
                    vehicle_model="Vehicle",
                    vehicle_year=2024,
                    idv=1000000.00,
                    coverage_type="comprehensive",
                    valid_from=date.today(),
                    valid_until=date.today() + timedelta(days=365)
                )
                db.add(policy)
                db.flush()  # Flush to get the ID
                policy_id = policy.id
            else:
                policy_id = policy_id_str
        else:
            # No policy_id provided, create a default demo policy
            import uuid as uuid_lib
            policy_id_str = str(uuid_lib.uuid4())
            import itertools
            prefix = "".join(itertools.islice(str(current_user.id), 8))
            policy = Policy(
                id=policy_id_str,
                user_id=str(current_user.id),  # Ensure string
                policy_number=f"DEMO-{prefix}",
                insurer_name="Demo Insurance Co.",
                vehicle_make="Demo",
                vehicle_model="Vehicle",
                vehicle_year=2024,
                idv=1000000.00,
                coverage_type="comprehensive",
                valid_from=date.today(),
                valid_until=date.today() + timedelta(days=365)
            )
            db.add(policy)
            db.flush()  # Flush to get the ID
            policy_id = policy.id
        
        # Create claim with P0 locks initialized to False
        claim = Claim(
            policy_id=str(policy_id),
            customer_id=str(current_user.id),
            status=ClaimStatus.CREATED,
            risk_level=RiskLevel.GREEN,
            incident_date=request.incident_date,
            incident_description=request.incident_description,
            incident_location_lat=request.incident_location_lat,
            incident_location_lng=request.incident_location_lng,
            p0_locks={
                "quality_gate_passed": False,
                "vin_hash_generated": False,
                "damage_detected": False,
                "damage_hash_generated": False,
                "duplicate_check_completed": False,
                "icve_estimate_generated": False
            }
        )
        
        db.add(claim)
        db.commit()
        db.refresh(claim)
        
        # Log state transition
        transition = ClaimStateTransition(
            claim_id=claim.id,
            from_status=None,
            to_status=ClaimStatus.CREATED,
            actor_user_id=current_user.id,
            reason="Claim created by customer"
        )
        db.add(transition)
        db.commit()
        
        return claim
        
    except Exception as e:
        db.rollback()
        print(f"Error creating claim: {str(e)}")  # Debug logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create claim: {str(e)}"
        )


@router.get("/dashboard", response_model=CustomerDashboardResponse)
async def get_customer_dashboard(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """
    Get customer dashboard with claims summary and groupings.
    Returns summary statistics and claims grouped by status.
    """
    from datetime import datetime, timedelta
    
    # Query all customer's claims
    all_claims = db.query(Claim).options(selectinload(Claim.icve_estimates)).filter(
        Claim.customer_id == str(current_user.id)
    ).order_by(Claim.created_at.desc()).all()
    
    # Calculate statistics
    total_claims = len(all_claims)
    
    # Pending statuses: CREATED, SUBMITTED, ANALYZING, DRAFT_READY, SURVEYOR_REVIEW, NEEDS_MORE_INFO
    pending_statuses = [
        ClaimStatus.CREATED,
        ClaimStatus.SUBMITTED,
        ClaimStatus.ANALYZING,
        ClaimStatus.DRAFT_READY,
        ClaimStatus.SURVEYOR_REVIEW,
        ClaimStatus.NEEDS_MORE_INFO
    ]
    
    pending_claims = [c for c in all_claims if c.status in pending_statuses]
    approved_claims = [c for c in all_claims if c.status == ClaimStatus.APPROVED]
    rejected_claims = [c for c in all_claims if c.status == ClaimStatus.REJECTED]
    
    stats = DashboardStats(
        total_claims=total_claims,
        pending_claims=len(pending_claims),
        approved_claims=len(approved_claims),
        rejected_claims=len(rejected_claims)
    )
    
    # Helper function to convert claim to summary
    def to_claim_summary(claim: Claim) -> ClaimSummary:
        # Get ICVE estimate if available
        estimated_amount = None
        if claim.icve_estimates:
            latest_estimate = claim.icve_estimates[0]  # Assuming relationship loads latest
            estimated_amount = latest_estimate.total_estimate
        
        # Check for recent updates (within last 24 hours)
        has_updates = False
        if claim.updated_at:
            time_since_update = datetime.utcnow() - claim.updated_at
            has_updates = time_since_update < timedelta(hours=24)
        
        return ClaimSummary(
            id=str(claim.id),
            policy_id=str(claim.policy_id),
            status=claim.status.value,
            risk_level=claim.risk_level.value,
            incident_date=claim.incident_date,
            submitted_at=claim.submitted_at,
            estimated_amount=estimated_amount,
            has_updates=has_updates
        )
    
    # Get recent claims (last 10)
    recent_claims = [to_claim_summary(c) for c in all_claims[:10]]
    
    # Group claims by status
    pending_claims_summary = [to_claim_summary(c) for c in pending_claims]
    approved_claims_summary = [to_claim_summary(c) for c in approved_claims]
    rejected_claims_summary = [to_claim_summary(c) for c in rejected_claims]
    
    return CustomerDashboardResponse(
        stats=stats,
        recent_claims=recent_claims,
        pending_claims=pending_claims_summary,
        approved_claims=approved_claims_summary,
        rejected_claims=rejected_claims_summary
    )


@router.get("/my-claims", response_model=List[ClaimResponse])
async def get_my_claims(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """
    Get all claims for the logged-in customer.
    """
    claims = db.query(Claim).options(selectinload(Claim.icve_estimates)).filter(
        Claim.customer_id == str(current_user.id)
    ).order_by(Claim.created_at.desc()).all()
    return claims



@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    claim_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get claim details by ID.
    Customers can only access their own claims.
    Surveyors can access any claim.
    """
    # Convert UUID to string for database query
    claim_id_str = str(claim_id)
    
    claim = db.query(Claim).options(
        joinedload(Claim.customer),
        joinedload(Claim.policy)
    ).filter(Claim.id == claim_id_str).first()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found"
        )
    
    # Check access permissions
    from app.models.enums import UserRole
    if current_user.role == UserRole.CUSTOMER and claim.customer_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own claims"
        )
    
    return claim





@router.get("", response_model=ClaimListResponse)
async def list_claims(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List claims.
    Customers see only their own claims.
    Surveyors see all claims.
    """
    from app.models.enums import UserRole
    
    # Build query based on role
    query = db.query(Claim).options(selectinload(Claim.icve_estimates))
    
    if current_user.role == UserRole.CUSTOMER:
        query = query.filter(Claim.customer_id == str(current_user.id))
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    claims = query.order_by(Claim.created_at.desc()).offset(offset).limit(page_size).all()
    
    return ClaimListResponse(
        claims=claims,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/{claim_id}/photos", response_model=PhotoUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    claim_id: UUID,
    file: UploadFile = File(...),
    capture_angle: Optional[str] = Form(None),
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """
    Upload a photo to a claim.
    Only customers can upload photos to their own claims.
    """
    # Convert UUID to string for database query
    claim_id_str = str(claim_id)
    
    # Verify claim belongs to customer
    claim = db.query(Claim).filter(
        Claim.id == claim_id_str,
        Claim.customer_id == str(current_user.id)
    ).first()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found or does not belong to you"
        )
    
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )
    
    # Read file content
    file_content = await file.read()
    
    # Validate file size
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024)}MB"
        )
    
    # Get image dimensions
    from typing import cast
    try:
        file_content_bytes = cast(bytes, file_content)
        image = Image.open(io.BytesIO(file_content_bytes))
        width, height = image.size
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file"
        )
    
    # Generate object key
    object_key = storage_service.generate_object_key(
        str(claim_id),
        file.filename or "photo.jpg",
        folder="original"
    )
    
    # Upload to storage
    file_io = io.BytesIO(file_content_bytes)
    upload_result = storage_service.upload_file(
        file_io,
        object_key,
        content_type=file.content_type
    )
    
    # Parse capture angle
    angle_enum = None
    if capture_angle:
        try:
            angle_enum = CaptureAngle(capture_angle.upper())
        except ValueError:
            pass
    
    # Create media asset record
    media_asset = MediaAsset(
        claim_id=claim_id_str,  # Use string version
        media_type=MediaType.IMAGE,
        capture_angle=angle_enum,
        object_key=upload_result["object_key"],
        content_type=file.content_type,
        size_bytes=upload_result["size_bytes"],
        width=width,
        height=height,
        sha256_hash=upload_result["sha256_hash"]
    )
    
    db.add(media_asset)
    db.commit()
    db.refresh(media_asset)
    
    # Generate presigned URL
    presigned_url = storage_service.generate_presigned_url(media_asset.object_key)
    
    # Create response with all required fields including presigned_url
    response = PhotoUploadResponse(
        id=media_asset.id,
        claim_id=media_asset.claim_id,
        media_type=media_asset.media_type.value,
        capture_angle=media_asset.capture_angle.value if media_asset.capture_angle else None,
        object_key=media_asset.object_key,
        content_type=media_asset.content_type,
        size_bytes=media_asset.size_bytes,
        width=media_asset.width,
        height=media_asset.height,
        sha256_hash=media_asset.sha256_hash,
        uploaded_at=media_asset.uploaded_at,
        presigned_url=presigned_url
    )
    
    return response


@router.get("/{claim_id}/photos", response_model=List[PhotoListResponse])
async def list_photos(
    claim_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all photos for a claim.
    """
    # Convert UUID to string for database query
    claim_id_str = str(claim_id)
    
    # Verify claim access
    claim = db.query(Claim).filter(Claim.id == claim_id_str).first()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found"
        )
    
    # Check access permissions
    from app.models.enums import UserRole
    if current_user.role == UserRole.CUSTOMER and claim.customer_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own claims"
        )
    
    # Get photos
    photos = db.query(MediaAsset).filter(MediaAsset.claim_id == claim_id_str).order_by(MediaAsset.uploaded_at).all()
    
    # Add presigned URLs
    response_photos = []
    for photo in photos:
        presigned_url = storage_service.generate_presigned_url(photo.object_key)
        # Create dict explicitly to include presigned_url before validation
        photo_dict = {
            "id": photo.id,
            "capture_angle": photo.capture_angle,
            "content_type": photo.content_type,
            "size_bytes": photo.size_bytes,
            "uploaded_at": photo.uploaded_at,
            "presigned_url": presigned_url
        }
        response_photos.append(PhotoListResponse(**photo_dict))
    
    return response_photos



@router.post("/{claim_id}/submit", response_model=ClaimResponse)
async def submit_claim(
    claim_id: UUID,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """
    Submit a claim for processing.
    Validates minimum photos and VIN photo presence.
    """
    # Convert UUID to string for database query
    claim_id_str = str(claim_id)
    
    # Verify claim belongs to customer
    claim = db.query(Claim).filter(
        Claim.id == claim_id_str,
        Claim.customer_id == str(current_user.id)
    ).first()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found or does not belong to you"
        )
    
    # Verify claim is in CREATED state
    if claim.status != ClaimStatus.CREATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Claim has already been submitted"
        )
    
    # Verify minimum photos (3 minimum)
    photo_count = db.query(MediaAsset).filter(MediaAsset.claim_id == claim_id_str).count()
    if photo_count < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum 3 photos required to submit claim"
        )
    
    # DEMO MODE: VIN photo validation is relaxed for demo purposes
    # In production, this would strictly require a VIN photo
    # Verify VIN photo present (optional in demo mode)
    # vin_photo = db.query(MediaAsset).filter(
    #     MediaAsset.claim_id == claim_id_str,
    #     MediaAsset.capture_angle == CaptureAngle.VIN
    # ).first()
    # 
    # if not vin_photo:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="VIN photo is required to submit claim"
    #     )
    
    # Update claim status
    from datetime import datetime
    old_status = claim.status
    claim.status = ClaimStatus.SUBMITTED
    claim.submitted_at = datetime.utcnow()
    
    # Log state transition
    transition = ClaimStateTransition(
        claim_id=claim.id,
        from_status=old_status,
        to_status=ClaimStatus.SUBMITTED,
        actor_user_id=current_user.id,
        reason="Claim submitted by customer for processing"
    )
    db.add(transition)
    db.commit()
    db.refresh(claim)
    
    # Trigger AI processing pipeline (P0 Master Locks 1-6)
    from app.core.celery_app import celery_app
    celery_app.send_task(
        'app.tasks.pipeline.process_claim_pipeline',
        args=[claim_id_str]  # Use string version
    )
    
    return claim


@router.delete("/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_claim(
    claim_id: UUID,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """
    Delete a claim.
    Only customers can delete their own claims.
    Claims can be deleted in any status (for demo purposes).
    """
    # Convert UUID to string for database query
    claim_id_str = str(claim_id)
    
    # Verify claim belongs to customer
    claim = db.query(Claim).filter(
        Claim.id == claim_id_str,
        Claim.customer_id == str(current_user.id)
    ).first()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found or does not belong to you"
        )
    
    # Allow deletion of claims in any status (for demo purposes)
    # In production, you might want to restrict this based on business rules
    
    # Delete associated records in order (to avoid foreign key constraints)
    
    # 1. Delete audit events
    from app.models.audit import AuditEvent, RiskAssessment
    db.query(AuditEvent).filter(AuditEvent.claim_id == claim_id_str).delete(synchronize_session=False)
    
    # 2. Delete risk assessments
    db.query(RiskAssessment).filter(RiskAssessment.claim_id == claim_id_str).delete(synchronize_session=False)
    
    # 3. Delete duplicate check results
    from app.models.damage import DuplicateCheckResult
    db.query(DuplicateCheckResult).filter(DuplicateCheckResult.claim_id == claim_id_str).delete(synchronize_session=False)
    
    # 4. Delete damages
    from app.models.damage import DamageDetection
    db.query(DamageDetection).filter(DamageDetection.claim_id == claim_id_str).delete(synchronize_session=False)
    
    # 5. Delete ICVE estimates and line items
    from app.models.icve import ICVEEstimate, ICVELineItem
    # Optimization: Batch delete line items using a subquery to prevent N+1 queries
    estimate_ids = [e.id for e in db.query(ICVEEstimate.id).filter(ICVEEstimate.claim_id == claim_id_str).all()]
    if estimate_ids:
        db.query(ICVELineItem).filter(ICVELineItem.icve_estimate_id.in_(estimate_ids)).delete(synchronize_session=False)
    db.query(ICVEEstimate).filter(ICVEEstimate.claim_id == claim_id_str).delete()
    
    # 6. Delete AI artifacts
    from app.models.report import AIArtifact
    db.query(AIArtifact).filter(AIArtifact.claim_id == claim_id_str).delete(synchronize_session=False)
    
    # 7. Delete media files from storage and database
    # Optimization: Fetch only object keys and parallelize deletion from storage
    import concurrent.futures
    media_keys = [m.object_key for m in db.query(MediaAsset.object_key).filter(MediaAsset.claim_id == claim_id_str).all()]

    def delete_media_file(object_key):
        try:
            storage_service.delete_file(object_key)
        except Exception as e:
            print(f"Warning: Failed to delete file {object_key}: {e}")

    if media_keys:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(delete_media_file, media_keys)

    db.query(MediaAsset).filter(MediaAsset.claim_id == claim_id_str).delete(synchronize_session=False)
    
    # 8. Delete report drafts
    from app.models.report import ReportDraft
    db.query(ReportDraft).filter(ReportDraft.claim_id == claim_id_str).delete(synchronize_session=False)
    
    # 9. Delete state transitions (already has cascade in model, but explicit is safer)
    from app.models.claim import ClaimStateTransition
    db.query(ClaimStateTransition).filter(ClaimStateTransition.claim_id == claim_id_str).delete(synchronize_session=False)
    
    # 10. Finally, delete the claim itself
    db.delete(claim)
    db.commit()
    
    return None
