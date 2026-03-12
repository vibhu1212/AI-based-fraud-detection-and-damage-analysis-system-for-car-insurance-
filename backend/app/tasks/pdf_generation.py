"""
Celery task for PDF report generation.
"""
from celery import shared_task
from sqlalchemy.orm import Session
import logging

from app.models.claim import Claim
from app.models.user import User
from app.services.pdf_generator import pdf_generator
from app.models.base import SessionLocal

logger = logging.getLogger(__name__)


@shared_task(name="generate_pdf_report")
def generate_pdf_report_task(claim_id: str, surveyor_id: str, decision_reason: str = None):
    """
    Generate PDF report for approved claim.
    
    Args:
        claim_id: Claim UUID
        surveyor_id: Surveyor user ID
        decision_reason: Reason for approval/rejection
    """
    db: Session = SessionLocal()
    
    try:
        logger.info(f"Starting PDF generation for claim {claim_id}")
        
        # Get claim
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            logger.error(f"Claim {claim_id} not found")
            return {"success": False, "error": "Claim not found"}
        
        # Get surveyor
        surveyor = db.query(User).filter(User.id == surveyor_id).first()
        if not surveyor:
            logger.error(f"Surveyor {surveyor_id} not found")
            return {"success": False, "error": "Surveyor not found"}
        
        # Generate PDF
        pdf_url = pdf_generator.generate_claim_report(
            db=db,
            claim=claim,
            surveyor=surveyor,
            decision_reason=decision_reason
        )
        
        # Update claim with PDF URL
        claim.report_pdf_url = pdf_url
        db.commit()
        
        logger.info(f"PDF generated successfully for claim {claim_id}: {pdf_url}")
        
        return {
            "success": True,
            "claim_id": claim_id,
            "pdf_url": pdf_url
        }
    
    except Exception as e:
        logger.error(f"Failed to generate PDF for claim {claim_id}: {e}")
        db.rollback()
        return {
            "success": False,
            "claim_id": claim_id,
            "error": str(e)
        }
    
    finally:
        db.close()
