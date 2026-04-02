import os
import io
import sys
import pytest
from pathlib import Path

# Add the backend directory to sys.path to resolve imports
backend_dir = str(Path(__file__).parent.parent.absolute())
sys.path.insert(0, backend_dir)

from app.services.storage import StorageService

# Mock settings for testing
class MockSettings:
    STORAGE_PATH = "./test_storage"

def test_storage_traversal_prevention(monkeypatch):
    monkeypatch.setattr("app.services.storage.settings", MockSettings())
    storage = StorageService()

    # Test that a valid key works
    assert storage._is_safe_path("original/123/test.jpg") is True

    # Test path traversal attempts
    assert storage._is_safe_path("../../../etc/passwd") is False
    assert storage._is_safe_path("/etc/passwd") is False
    assert storage._is_safe_path("original/123/../../../etc/passwd") is False
    assert storage._is_safe_path("C:\\Windows\\System32") is False

    # Ensure upload_file raises ValueError for bad paths
    with pytest.raises(ValueError, match="Invalid or unsafe object key"):
        storage.upload_file(io.BytesIO(b"test"), "../../../etc/passwd")

    # Ensure download_file raises ValueError for bad paths
    with pytest.raises(ValueError, match="Invalid or unsafe object key"):
        storage.download_file("../../../etc/passwd")

    # Ensure delete_file raises ValueError for bad paths
    with pytest.raises(ValueError, match="Invalid or unsafe object key"):
        storage.delete_file("../../../etc/passwd")

    # Ensure file_exists raises ValueError for bad paths
    with pytest.raises(ValueError, match="Invalid or unsafe object key"):
        storage.file_exists("../../../etc/passwd")

    # Ensure store_pdf raises ValueError for bad paths
    with pytest.raises(ValueError, match="Invalid or unsafe filename"):
        storage.store_pdf(b"test pdf", "../../../etc/passwd")

    # Clean up test directories
    import shutil
    shutil.rmtree(MockSettings.STORAGE_PATH, ignore_errors=True)
