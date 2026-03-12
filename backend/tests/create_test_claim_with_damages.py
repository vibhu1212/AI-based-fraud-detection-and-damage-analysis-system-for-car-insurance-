#!/usr/bin/env python3
"""
Create a test claim with mock damage detections for testing Phase 4.4 and 4.5
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.models.base import SessionLocal
from app.models.claim import Claim
from app.models.user import User
from app.models.policy import Policy
from app.models.media import MediaAsset
from app.models.damage import DamageDetection
from app.models.enums import ClaimStatus, MediaType, CaptureAngle, DamageType
from app.services.storage import StorageService
from datetime import datetime
from PIL import Image
import io
import uuid

def create_test_claim_with_damages():
    """Create a test claim with photos and mock damage detections"""
    db = SessionLocal()
    storage = StorageService()
    
    try:
        # Get customer
        customer = db.query(User).filter(User.email == "customer1@insurai.demo").first()
        if not customer:
            print("❌ Customer not found. Run init_db.py first.")
            return None
            
        # Get policy
        policy = db.query(Policy).filter(Policy.user_id == customer.id).first()
        if not policy:
            print("❌ Policy not found. Run init_db.py first.")
            return None
            
        print(f"Creating test claim for customer: {customer.email}")
        
        # Create claim
        claim = Claim(
            customer_id=customer.id,
            policy_id=policy.id,
            incident_date=datetime.utcnow(),
            incident_description="Test claim with mock damages for Phase 4.4/4.5 testing",
            status=ClaimStatus.ANALYZING,
            vin_hash="test_vin_hash_" + str(uuid.uuid4())[:8]
        )
        
        # Set P0 locks (simulate completed tasks 4.1, 4.2, 4.3)
        claim.p0_locks = {
            "quality_gate_passed": True,
            "vin_hash_generated": True,
            "damage_detected": True,
            "damage_hash_generated": False,
            "duplicate_check_completed": False,
            "icve_estimate_generated": False
        }
        
        db.add(claim)
        db.flush()
        
        print(f"✅ Created claim: {claim.id}")
        
        # Create sample photos with mock damages
        angles = [
            (CaptureAngle.FRONT, "front"),
            (CaptureAngle.REAR, "rear"),
            (CaptureAngle.LEFT, "left"),
            (CaptureAngle.RIGHT, "right"),
            (CaptureAngle.VIN, "vin"),
            (CaptureAngle.DETAIL, "detail")
        ]
        
        print("\nCreating sample photos with mock damages...")
        
        for angle, name in angles:
            # Create a simple test image (640x480 RGB)
            img = Image.new('RGB', (640, 480), color=(100, 150, 200))
            
            # Save to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=95)
            img_bytes.seek(0)
            
            # Upload to storage
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{name}.jpg"
            object_key = storage.generate_object_key("original", str(claim.id), filename)
            
            upload_result = storage.upload_file(
                file=img_bytes,
                object_key=object_key,
                content_type="image/jpeg"
            )
            
            # Create media asset
            media = MediaAsset(
                claim_id=claim.id,
                media_type=MediaType.IMAGE,
                capture_angle=angle,
                object_key=upload_result["object_key"],
                size_bytes=upload_result["size_bytes"],
                sha256_hash=upload_result["sha256_hash"],
                width=640,
                height=480
            )
            db.add(media)
            db.flush()
            
            # Add mock damage detections (2-3 per photo except VIN)
            if angle != CaptureAngle.VIN:
                num_damages = 2 if angle in [CaptureAngle.FRONT, CaptureAngle.REAR] else 3
                
                for i in range(num_damages):
                    # Create mock bounding boxes
                    x1 = 100 + (i * 150)
                    y1 = 100 + (i * 100)
                    x2 = x1 + 120
                    y2 = y1 + 80
                    
                    # Vary damage types
                    damage_types = [DamageType.DENT, DamageType.SCRATCH, DamageType.CRACK]
                    damage_type = damage_types[i % len(damage_types)]
                    
                    damage = DamageDetection(
                        claim_id=claim.id,
                        media_id=media.id,
                        damage_type=damage_type,
                        confidence=0.85 + (i * 0.05),
                        bbox_x1=x1,
                        bbox_y1=y1,
                        bbox_x2=x2,
                        bbox_y2=y2
                    )
                    db.add(damage)
            
            print(f"  ✅ Created {name.upper()} photo with mock damages")
        
        db.commit()
        
        # Count damages
        damage_count = db.query(DamageDetection).filter(
            DamageDetection.claim_id == claim.id
        ).count()
        
        print(f"\n✅ Test claim created successfully!")
        print(f"   Claim ID: {claim.id}")
        print(f"   Status: {claim.status.value}")
        print(f"   VIN Hash: {claim.vin_hash}")
        print(f"   Photos: 6")
        print(f"   Mock Damages: {damage_count}")
        print(f"\n🧪 Ready to test Phase 4.4 and 4.5!")
        print(f"   Run: python test_pipeline_4.4_4.5.py")
        
        return claim.id
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    claim_id = create_test_claim_with_damages()
    sys.exit(0 if claim_id else 1)
