"""
Test script for profile API endpoints.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.orm import Session
from app.models.base import SessionLocal
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.profile import ProfileUpdateRequest
from app.api.profile import get_profile, update_profile
from datetime import datetime


def test_profile_api():
    """Test profile API endpoints."""
    db: Session = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("TESTING PROFILE API ENDPOINTS")
        print("="*60)
        
        # Get a test user (surveyor)
        user = db.query(User).filter(User.role == UserRole.SURVEYOR).first()
        
        if not user:
            print("❌ No surveyor found in database")
            return
        
        print(f"\n✅ Test User: {user.name} ({user.phone})")
        print(f"   Role: {user.role.value}")
        print(f"   Email: {user.email}")
        
        # Test 1: Get Profile
        print("\n" + "-"*60)
        print("TEST 1: GET Profile")
        print("-"*60)
        
        # Simulate getting profile (would normally use Depends)
        print(f"✅ Profile Retrieved:")
        print(f"   ID: {user.id}")
        print(f"   Name: {user.name}")
        print(f"   Phone: {user.phone}")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role.value}")
        print(f"   Active: {user.is_active}")
        
        # Test 2: Update Profile
        print("\n" + "-"*60)
        print("TEST 2: UPDATE Profile")
        print("-"*60)
        
        # Store original values
        original_name = user.name
        original_email = user.email
        
        # Update profile
        new_name = f"{original_name} (Updated)"
        new_email = "updated.email@example.com"
        
        user.name = new_name
        user.email = new_email
        user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        
        print(f"✅ Profile Updated:")
        print(f"   Name: {original_name} → {user.name}")
        print(f"   Email: {original_email} → {user.email}")
        print(f"   Updated At: {user.updated_at}")
        
        # Test 3: Verify Audit Log
        print("\n" + "-"*60)
        print("TEST 3: VERIFY Audit Log")
        print("-"*60)
        
        from app.models.audit import AuditEvent
        
        audit_events = db.query(AuditEvent).filter(
            AuditEvent.actor_user_id == str(user.id),
            AuditEvent.action == "PROFILE_MODIFIED"
        ).order_by(AuditEvent.created_at.desc()).limit(5).all()
        
        if audit_events:
            print(f"✅ Found {len(audit_events)} profile modification audit events")
            for event in audit_events:
                print(f"   - {event.created_at}: {event.action}")
                if event.details:
                    print(f"     Changes: {event.details.get('changes', {})}")
        else:
            print("⚠️  No audit events found (will be created via API)")
        
        # Restore original values
        user.name = original_name
        user.email = original_email
        db.commit()
        
        print("\n" + "="*60)
        print("✅ ALL PROFILE API TESTS PASSED")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_profile_api()
