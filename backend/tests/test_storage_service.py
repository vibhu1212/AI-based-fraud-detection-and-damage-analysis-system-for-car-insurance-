import pytest
import io
from pathlib import Path
import tempfile
import os
import shutil

# Mock config before importing StorageService
import sys
from unittest.mock import MagicMock

class MockSettings:
    STORAGE_PATH = tempfile.mkdtemp()

sys.modules['app.config'] = MagicMock()
sys.modules['app.config'].settings = MockSettings()

from app.services.storage import StorageService

@pytest.fixture
def storage_service():
    service = StorageService()
    yield service
    # Cleanup
    shutil.rmtree(MockSettings.STORAGE_PATH, ignore_errors=True)

def test_safe_path_valid(storage_service):
    path = storage_service._get_safe_path("original/123/file.jpg")
    assert path.is_relative_to(storage_service.storage_path.resolve())

def test_safe_path_traversal(storage_service):
    with pytest.raises(ValueError, match="Invalid path: Path traversal detected"):
        storage_service._get_safe_path("../../../etc/passwd")

def test_upload_file_traversal(storage_service):
    file_content = io.BytesIO(b"test content")
    with pytest.raises(ValueError, match="Invalid path: Path traversal detected"):
        storage_service.upload_file(file_content, "../../../etc/passwd")

def test_download_file_traversal(storage_service):
    assert storage_service.download_file("../../../etc/passwd") is None

def test_delete_file_traversal(storage_service):
    assert storage_service.delete_file("../../../etc/passwd") is False

def test_file_exists_traversal(storage_service):
    assert storage_service.file_exists("../../../etc/passwd") is False

def test_store_pdf_traversal(storage_service):
    pdf_content = b"fake pdf content"
    with pytest.raises(ValueError, match="Invalid path: Path traversal detected"):
        storage_service.store_pdf(pdf_content, "../../../../etc/passwd")
