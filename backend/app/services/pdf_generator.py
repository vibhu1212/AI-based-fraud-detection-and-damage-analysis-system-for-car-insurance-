"""
PDF Report Generation Service.
Generates professional PDF reports for approved claims.
"""
from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.damage import DamageDetection
from app.models.icve import ICVEEstimate
from app.models.report import ReportDraft
from app.models.user import User
from app.services.storage import StorageService

logger = logging.getLogger(__name__)


class PDFGeneratorService:
    """Service for generating PDF reports from claim data."""
    
    def __init__(self):
        # Setup Jinja2 template environment
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        self.storage = StorageService()
    
    def generate_claim_report(
        self,
        db: Session,
        claim: Claim,
        surveyor: User,
        decision_reason: Optional[str] = None
    ) -> str:
        """
        Generate PDF report for a claim.
        
        Args:
            db: Database session
            claim: Claim object
            surveyor: Surveyor who approved/rejected the claim
            decision_reason: Reason for approval/rejection
        
        Returns:
            str: URL to the generated PDF file
        """
        try:
            # Gather all required data
            report_data = self._prepare_report_data(db, claim, surveyor, decision_reason)
            
            # Render HTML from template
            html_content = self._render_template(report_data)
            
            # Generate PDF
            pdf_bytes = self._generate_pdf(html_content)
            
            # Store PDF
            pdf_filename = f"report_{claim.claim_number}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_url = self.storage.store_pdf(pdf_bytes, pdf_filename)
            
            logger.info(f"Generated PDF report for claim {claim.id}: {pdf_url}")
            return pdf_url
        
        except Exception as e:
            logger.error(f"Failed to generate PDF for claim {claim.id}: {e}")
            raise
    
    def _prepare_report_data(
        self,
        db: Session,
        claim: Claim,
        surveyor: User,
        decision_reason: Optional[str]
    ) -> Dict[str, Any]:
        """Prepare all data needed for the report template."""
        
        # Get damages
        damages = db.query(DamageDetection).filter(
            DamageDetection.claim_id == claim.id
        ).all()
        
        # Get ICVE estimate
        icve = db.query(ICVEEstimate).filter(
            ICVEEstimate.claim_id == claim.id
        ).first()
        
        # Get report draft - handle missing columns gracefully
        report_draft = None
        report_sections = []
        try:
            report_draft = db.query(ReportDraft).filter(
                ReportDraft.claim_id == claim.id
            ).first()
            
            if report_draft:
                # Try to get report sections from various fields
                if hasattr(report_draft, 'surveyor_version') and report_draft.surveyor_version:
                    report_sections = report_draft.surveyor_version.get('sections', [])
                elif hasattr(report_draft, 'report_sections') and report_draft.report_sections:
                    report_sections = report_draft.report_sections.get('sections', [])
                elif hasattr(report_draft, 'final_text') and report_draft.final_text:
                    # Create a single section from final_text
                    report_sections = [{'title': 'Survey Report', 'content': report_draft.final_text}]
                elif hasattr(report_draft, 'draft_text') and report_draft.draft_text:
                    # Create a single section from draft_text
                    report_sections = [{'title': 'Survey Report', 'content': report_draft.draft_text}]
        except Exception as e:
            logger.warning(f"Could not load report draft: {e}")
        
        # Calculate approved amount
        approved_amount = icve.total_estimate if icve else 0.0
        
        # Prepare data dictionary
        data = {
            'claim': claim,
            'damages': damages,
            'icve': icve,
            'surveyor': surveyor,
            'decision_date': datetime.utcnow(),
            'decision_reason': decision_reason,
            'approved_amount': approved_amount,
            'report_sections': report_sections,
            'report_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return data
    
    def _render_template(self, data: Dict[str, Any]) -> str:
        """Render HTML template with data."""
        template = self.env.get_template('report_template.html')
        html_content = template.render(**data)
        return html_content
    
    def _generate_pdf(self, html_content: str) -> bytes:
        """Generate PDF from HTML content."""
        # Create PDF from HTML
        pdf_document = HTML(string=html_content)
        pdf_bytes = pdf_document.write_pdf()
        return pdf_bytes


# Global PDF generator instance
pdf_generator = PDFGeneratorService()
