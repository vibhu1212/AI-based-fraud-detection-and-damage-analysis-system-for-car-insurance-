#!/usr/bin/env python3
"""
Script to manually submit an existing claim to trigger the AI pipeline.
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.models.base import SessionLocal
from app.models.claim import Claim, ClaimStateTransition
from app.models.enums import ClaimStatus
from datetime import datetime

def submit_claim(claim_id: str):
    """Submit a claim and trigger the pipeline."""
    db: Session = SessionLocal()
    
    try:
        # Get the claim
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        
        if not claim:
            print(f"❌ Claim {claim_id} not found")
            return False
        
        print(f"📋 Found claim: {claim_id}")
        print(f"   Status: {claim.status}")
        print(f"   Customer ID: {claim.customer_id}")
        
        # Check if already submitted
        if claim.status != ClaimStatus.CREATED:
            print(f"⚠️  Claim is already in {claim.status} status")
            print(f"   Forcing submission anyway...")
        
        # Update claim status
        old_status = claim.status
        claim.status = ClaimStatus.SUBMITTED
        claim.submitted_at = datetime.utcnow()
        
        # Log state transition
        transition = ClaimStateTransition(
            claim_id=claim.id,
            from_status=old_status,
            to_status=ClaimStatus.SUBMITTED,
            actor_user_id=claim.customer_id,
            reason="Manually submitted via script"
        )
        db.add(transition)
        db.commit()
        
        print(f"✅ Claim status updated to SUBMITTED")
        
        # Trigger AI processing pipeline
        from app.core.celery_app import celery_app
        
        result = celery_app.send_task(
            'app.tasks.pipeline.process_claim_pipeline',
            args=[claim_id],
            queue='main-queue'
        )
        
        print(f"🚀 Pipeline task sent to Celery")
        print(f"   Task ID: {result.id}")
        print(f"   Queue: main-queue")
        print(f"\n💡 Check the Celery worker terminal to see task processing")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python submit_existing_claim.py <claim_id>")
        print("\nExample:")
        print("  python submit_existing_claim.py 77e53189-2498-447f-8a6e-c49cd21cd1ec")
        sys.exit(1)
    
    claim_id = sys.argv[1]
    success = submit_claim(claim_id)
    sys.exit(0 if success else 1)
