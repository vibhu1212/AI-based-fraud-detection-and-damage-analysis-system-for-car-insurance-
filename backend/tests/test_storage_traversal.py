import pytest
import io
from pathlib import Path
from app.services.storage import StorageService

def test_storage_service_path_traversal():
    storage_service = StorageService()

    # Test upload_file path traversal
    file_io = io.BytesIO(b"test content")
    with pytest.raises(ValueError, match="Invalid object key path"):
        storage_service.upload_file(file_io, "../../../etc/passwd", content_type="text/plain")

    # Test download_file path traversal
    assert storage_service.download_file("../../../etc/passwd") is None

    # Test delete_file path traversal
    assert storage_service.delete_file("../../../etc/passwd") is False

    # Test file_exists path traversal
    assert storage_service.file_exists("../../../etc/passwd") is False

    # Test store_pdf path traversal
    with pytest.raises(ValueError, match="Invalid PDF filename"):
        storage_service.store_pdf(b"test pdf", "../../../etc/passwd")

def test_storage_service_valid_operations():
    storage_service = StorageService()

    # Test valid upload
    file_io = io.BytesIO(b"test content")
    result = storage_service.upload_file(file_io, "test_file.txt", content_type="text/plain")
    assert result["object_key"] == "test_file.txt"

    # Test valid file_exists
    assert storage_service.file_exists("test_file.txt") is True

    # Test valid download
    file_path = storage_service.download_file("test_file.txt")
    assert file_path is not None
    assert file_path.exists()

    # Test valid store_pdf
    pdf_url = storage_service.store_pdf(b"test pdf", "test_report.pdf")
    assert "reports/test_report.pdf" in pdf_url
    assert storage_service.file_exists("reports/test_report.pdf") is True

    # Test valid delete
    assert storage_service.delete_file("test_file.txt") is True
    assert storage_service.file_exists("test_file.txt") is False
    assert storage_service.delete_file("reports/test_report.pdf") is True
    assert storage_service.file_exists("reports/test_report.pdf") is False
