#!/usr/bin/env python3
"""
Create test claim with REAL photos from Kaggle car damage dataset
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.models.base import SessionLocal
from app.models import User, Policy, Claim, ClaimStatus
from app.models.media import MediaAsset, MediaType, CaptureAngle
from app.services.storage import StorageService
from datetime import datetime
import uuid
import shutil
from pathlib import Path

# Dataset path
DATASET_PATH = Path.home() / ".cache/kagglehub/datasets/anujms/car-damage-detection/versions/1/data1a"
DAMAGE_PHOTOS = DATASET_PATH / "training/00-damage"
WHOLE_PHOTOS = DATASET_PATH / "training/01-whole"

def create_test_claim_with_real_photos():
    """Create a test claim with real car damage photos"""
    print("Creating test claim with REAL car damage photos...")
    
    db = SessionLocal()
    storage = StorageService()
    
    try:
        # Get customer
        customer = db.query(User).filter(User.email == "customer1@insurai.demo").first()
        if not customer:
            print("❌ Customer not found. Run seed_data.py first")
            return None
        
        print(f"Creating test claim for customer: {customer.email}")
        
        # Get policy
        policy = db.query(Policy).filter(Policy.user_id == customer.id).first()
        if not policy:
            print("❌ Policy not found")
            return None
        
        # Create claim
        claim_id = str(uuid.uuid4())
        claim = Claim(
            id=claim_id,
            policy_id=policy.id,
            customer_id=customer.id,
            status=ClaimStatus.SUBMITTED,
            incident_date=datetime.utcnow().date(),
            incident_description="Car accident with visible damage. Testing with real photos from dataset.",
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
        
        print(f"✅ Created claim: {claim_id}")
        
        # Photo mapping: use real damage photos
        photo_mapping = [
            ("0001.JPEG", CaptureAngle.FRONT, "Front view with damage"),
            ("0002.JPEG", CaptureAngle.REAR, "Rear view with damage"),
            ("0003.JPEG", CaptureAngle.LEFT, "Left side with damage"),
            ("0004.JPEG", CaptureAngle.RIGHT, "Right side with damage"),
            ("0005.JPEG", CaptureAngle.DETAIL, "Close-up damage detail"),
            ("0006.JPEG", CaptureAngle.VIN, "VIN plate photo"),
        ]
        
        print(f"\nCopying real photos from dataset...")
        photos_created = 0
        
        for photo_file, angle, description in photo_mapping:
            source_path = DAMAGE_PHOTOS / photo_file
            
            if not source_path.exists():
                print(f"  ⚠️  Photo not found: {photo_file}, skipping")
                continue
            
            # Generate object key
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{claim_id[:8]}_{angle.value.lower()}.jpg"
            object_key = storage.generate_object_key(claim_id, filename, "original")
            
            # Copy file to storage
            dest_path = storage.storage_path / object_key
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest_path)
            
            # Get file size
            file_size = dest_path.stat().st_size
            
            # Create media asset record
            media = MediaAsset(
                id=str(uuid.uuid4()),
                claim_id=claim_id,
                media_type=MediaType.IMAGE,
                capture_angle=angle,
                object_key=object_key,
                size_bytes=file_size,
                content_type="image/jpeg",
                sha256_hash=f"real_photo_{photo_file}",
                exif_data={
                    "source": "kaggle_car_damage_dataset",
                    "original_filename": photo_file,
                    "description": description
                }
            )
            db.add(media)
            photos_created += 1
            print(f"  ✅ Copied {photo_file} as {angle.value} photo")
        
        db.commit()
        
        print(f"\n✅ Test claim created successfully!")
        print(f"   Claim ID: {claim_id}")
        print(f"   Status: {claim.status.value}")
        print(f"   Photos: {photos_created} (real car damage photos)")
        print(f"\n🧪 Ready to test full pipeline!")
        print(f"   Run: python test_full_pipeline.py")
        
        return claim_id
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    # Check if dataset exists
    if not DAMAGE_PHOTOS.exists():
        print(f"❌ Dataset not found at: {DAMAGE_PHOTOS}")
        print(f"   Please download the dataset first")
        sys.exit(1)
    
    print(f"📁 Dataset found: {DAMAGE_PHOTOS}")
    print(f"   Photos available: {len(list(DAMAGE_PHOTOS.glob('*.JPEG')))}")
    
    claim_id = create_test_claim_with_real_photos()
    sys.exit(0 if claim_id else 1)
