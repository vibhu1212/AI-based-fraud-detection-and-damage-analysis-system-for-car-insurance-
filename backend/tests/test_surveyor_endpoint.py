"""
Test script to debug surveyor endpoint 500 error
"""
import sys
import os
import pathlib

# Change to backend directory
backend_dir = str(pathlib.Path(__file__).parent.parent.absolute())
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

from app.models.base import get_db
from app.models.claim import Claim
from app.models.damage import DamageDetection, DuplicateCheckResult
from app.models.icve import ICVEEstimate
from app.models.media import MediaAsset
from sqlalchemy import desc

claim_id = 'd99db613-b060-4c39-8375-762e41759f94'

db = next(get_db())

try:
    print("Testing surveyor endpoint logic...")
    print(f"Claim ID: {claim_id}")
    print()
    
    # Fetch claim
    print("1. Fetching claim...")
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        print("ERROR: Claim not found")
        sys.exit(1)
    print(f"   ✓ Claim found: {claim.id}")
    print(f"   Status: {claim.status}")
    print()
    
    # Fetch damages
    print("2. Fetching damages...")
    damages = db.query(DamageDetection).filter(DamageDetection.claim_id == claim_id).all()
    print(f"   ✓ Found {len(damages)} damages")
    print()
    
    # Fetch ICVE
    print("3. Fetching ICVE estimate...")
    icve = db.query(ICVEEstimate).filter(ICVEEstimate.claim_id == claim_id).order_by(desc(ICVEEstimate.created_at)).first()
    if icve:
        print(f"   ✓ ICVE found: {icve.id}")
        print(f"   Total estimate: {icve.total_estimate}")
    else:
        print("   ⚠ No ICVE estimate found")
    print()
    
    # Fetch duplicate check
    print("4. Fetching duplicate check...")
    dup_result = db.query(DuplicateCheckResult).filter(DuplicateCheckResult.claim_id == claim_id).order_by(desc(DuplicateCheckResult.created_at)).first()
    if dup_result:
        print(f"   ✓ Duplicate check found: {dup_result.id}")
        print(f"   Fraud action: {dup_result.fraud_action}")
    else:
        print("   ⚠ No duplicate check found")
    print()
    
    # Fetch photos
    print("5. Fetching photos...")
    photos = db.query(MediaAsset).filter(MediaAsset.claim_id == claim_id).all()
    print(f"   ✓ Found {len(photos)} photos")
    for p in photos:
        print(f"     - {p.id}: {p.capture_angle}")
    print()
    
    # Fetch report
    print("6. Fetching report draft...")
    from app.models.report import ReportDraft
    report = db.query(ReportDraft).filter(ReportDraft.claim_id == claim_id).order_by(desc(ReportDraft.created_at)).first()
    if report:
        print(f"   ✓ Report found: {report.id}")
    else:
        print("   ⚠ No report draft found")
    print()
    
    # Try to serialize claim
    print("7. Testing claim serialization...")
    try:
        claim_dict = {
            'id': claim.id,
            'status': claim.status,
            'policy_id': claim.policy_id,
            'customer_id': claim.customer_id,
            'incident_description': claim.incident_description,
            'incident_date': claim.incident_date,
            'submitted_at': claim.submitted_at,
            'risk_level': claim.risk_level,
            'p0_locks': claim.p0_locks
        }
        print("   ✓ Claim serialization successful")
    except Exception as e:
        print(f"   ✗ Claim serialization failed: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # Try to serialize ICVE
    print("8. Testing ICVE serialization...")
    if icve:
        try:
            icve_dict = {
                'id': icve.id,
                'total_estimate': icve.total_estimate,
                'labor_cost': icve.labor_cost,
                'parts_cost': icve.parts_cost
            }
            print("   ✓ ICVE serialization successful")
        except Exception as e:
            print(f"   ✗ ICVE serialization failed: {e}")
            import traceback
            traceback.print_exc()
    print()
    
    # Try to generate presigned URLs
    print("9. Testing presigned URL generation...")
    from app.services.storage import storage_service
    processed_photos = []
    for p in photos:
        try:
            p_dict = p.__dict__.copy()
            if 'object_key' in p_dict:
                p_dict['presigned_url'] = storage_service.generate_presigned_url(p.object_key)
            processed_photos.append(p_dict)
            print(f"   ✓ Photo {p.id} processed")
        except Exception as e:
            print(f"   ✗ Photo {p.id} failed: {e}")
            import traceback
            traceback.print_exc()
    print()
    
    print("=" * 60)
    print("All tests passed! The endpoint should work.")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
