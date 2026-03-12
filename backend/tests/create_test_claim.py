"""
Create a test claim with sample photos for quality gate testing
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.models.base import SessionLocal
from app.models.claim import Claim
from app.models.media import MediaAsset
from app.models.user import User
from app.models.policy import Policy
from app.models.enums import ClaimStatus, RiskLevel, MediaType, CaptureAngle
from datetime import date
import numpy as np
import cv2
from app.services.storage import StorageService

def create_sample_image(filename, quality='good', angle='FRONT'):
    """Create a sample test image"""
    if quality == 'good':
        # Create a sharp, well-exposed image
        img = np.random.randint(80, 180, (480, 640, 3), dtype=np.uint8)
        
        # Add VIN text if this is a VIN photo
        if angle == 'VIN':
            # Create a gray background for VIN (not too bright)
            img = np.ones((480, 640, 3), dtype=np.uint8) * 180
            # Add realistic VIN text
            vin_text = "1HGBH41JXMN109186"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.5
            thickness = 3
            text_size = cv2.getTextSize(vin_text, font, font_scale, thickness)[0]
            text_x = (640 - text_size[0]) // 2
            text_y = (480 + text_size[1]) // 2
            cv2.putText(img, vin_text, (text_x, text_y), font, font_scale, (20, 20, 20), thickness)
        else:
            # Add some structure (simulated car)
            cv2.rectangle(img, (100, 100), (540, 380), (120, 120, 120), -1)
            cv2.rectangle(img, (150, 150), (490, 330), (80, 80, 80), 2)
    elif quality == 'blurry':
        # Create a blurry image
        img = np.random.randint(80, 180, (480, 640, 3), dtype=np.uint8)
        img = cv2.GaussianBlur(img, (51, 51), 0)
    elif quality == 'dark':
        # Create an under-exposed image
        img = np.random.randint(0, 40, (480, 640, 3), dtype=np.uint8)
    elif quality == 'bright':
        # Create an over-exposed image
        img = np.random.randint(220, 255, (480, 640, 3), dtype=np.uint8)
    elif quality == 'glare':
        # Create an image with glare
        img = np.random.randint(80, 180, (480, 640, 3), dtype=np.uint8)
        # Add bright spots (glare)
        cv2.circle(img, (320, 240), 100, (255, 255, 255), -1)
        cv2.circle(img, (150, 150), 50, (255, 255, 255), -1)
    else:
        img = np.random.randint(80, 180, (480, 640, 3), dtype=np.uint8)
    
    cv2.imwrite(filename, img)
    return filename

def create_test_claim_with_photos():
    """Create a test claim with sample photos"""
    db = SessionLocal()
    storage = StorageService()
    
    try:
        # Get first customer and policy
        customer = db.query(User).filter(User.email == "customer1@insurai.demo").first()
        policy = db.query(Policy).filter(Policy.user_id == customer.id).first()
        
        if not customer or not policy:
            print("❌ Customer or policy not found. Run seed_data.py first.")
            return
        
        print(f"Creating test claim for customer: {customer.email}")
        
        # Create claim
        claim = Claim(
            policy_id=policy.id,
            customer_id=customer.id,
            status=ClaimStatus.SUBMITTED,
            risk_level=RiskLevel.GREEN,
            incident_date=date.today(),
            incident_description="Test claim for quality gate validation",
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
        
        print(f"✅ Created claim: {claim.id}")
        
        # Create sample photos with different qualities
        test_photos = [
            ('FRONT', 'good'),
            ('REAR', 'good'),
            ('LEFT', 'good'),
            ('RIGHT', 'good'),
            ('VIN', 'good'),
            ('DETAIL', 'good'),
        ]
        
        print("\nCreating sample photos...")
        for angle, quality in test_photos:
            # Create sample image
            temp_file = f"/tmp/test_{angle.lower()}_{quality}.jpg"
            create_sample_image(temp_file, quality, angle)
            
            # Upload to storage
            with open(temp_file, 'rb') as f:
                object_key = storage.generate_object_key(
                    str(claim.id),
                    f"{angle.lower()}.jpg",
                    folder="original"
                )
                
                upload_result = storage.upload_file(
                    f,
                    object_key,
                    content_type="image/jpeg"
                )
            
            # Create media asset
            media = MediaAsset(
                claim_id=claim.id,
                media_type=MediaType.IMAGE,
                capture_angle=CaptureAngle[angle],
                object_key=upload_result["object_key"],
                content_type="image/jpeg",
                size_bytes=upload_result["size_bytes"],
                width=640,
                height=480,
                sha256_hash=upload_result["sha256_hash"]
            )
            
            db.add(media)
            print(f"  ✅ Created {angle} photo ({quality} quality)")
            
            # Clean up temp file
            os.remove(temp_file)
        
        db.commit()
        
        print(f"\n✅ Test claim created successfully!")
        print(f"   Claim ID: {claim.id}")
        print(f"   Status: {claim.status.value}")
        print(f"   Photos: {len(test_photos)}")
        print(f"\n🧪 Ready to test quality gate validation!")
        print(f"   Run: python3 backend/test_quality_gate.py")
        
        return claim.id
    
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating test claim: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    create_test_claim_with_photos()
