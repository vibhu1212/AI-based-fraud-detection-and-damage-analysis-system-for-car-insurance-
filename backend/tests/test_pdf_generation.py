"""
Test PDF generation functionality.
"""
import sys
from pathlib import Path
from sqlalchemy.orm import Session

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.models.base import SessionLocal
from app.models.claim import Claim
from app.models.user import User
from app.services.pdf_generator import pdf_generator


def test_pdf_generation():
    """Test PDF generation for an approved claim."""
    db: Session = SessionLocal()
    
    try:
        # Get a claim (preferably one that's been approved or in surveyor review)
        claim = db.query(Claim).filter(
            Claim.status.in_(['APPROVED', 'SURVEYOR_REVIEW', 'DRAFT_READY'])
        ).first()
        
        if not claim:
            print("❌ No suitable claim found for testing")
            return False
        
        print(f"✓ Found claim: {claim.id} (Status: {claim.status})")
        
        # Get a surveyor user
        surveyor = db.query(User).filter(User.role == 'SURVEYOR').first()
        
        if not surveyor:
            print("❌ No surveyor found")
            return False
        
        print(f"✓ Found surveyor: {surveyor.full_name}")
        
        # Generate PDF
        print("\n📄 Generating PDF report...")
        pdf_url = pdf_generator.generate_claim_report(
            db=db,
            claim=claim,
            surveyor=surveyor,
            decision_reason="Test approval for PDF generation"
        )
        
        print(f"✅ PDF generated successfully!")
        print(f"   URL: {pdf_url}")
        
        # Check if file exists
        from app.services.storage import storage_service
        object_key = pdf_url.replace("/api/storage/", "")
        file_path = storage_service.download_file(object_key)
        
        if file_path and file_path.exists():
            file_size = file_path.stat().st_size
            print(f"✓ PDF file exists: {file_path}")
            print(f"✓ File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
            return True
        else:
            print(f"❌ PDF file not found at: {object_key}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("PDF Generation Test")
    print("=" * 60)
    
    success = test_pdf_generation()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ PDF GENERATION TEST PASSED")
    else:
        print("❌ PDF GENERATION TEST FAILED")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
