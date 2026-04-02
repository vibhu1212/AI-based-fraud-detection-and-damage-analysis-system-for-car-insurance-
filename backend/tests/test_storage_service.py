import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.services.storage import StorageService

@pytest.fixture
def temp_storage_path(tmp_path):
    return tmp_path

@pytest.fixture
def storage_service(temp_storage_path):
    with patch('app.services.storage.settings') as mock_settings:
        mock_settings.STORAGE_PATH = str(temp_storage_path)
        service = StorageService()
        return service

def test_safe_path_valid(storage_service, temp_storage_path):
    path = storage_service._get_safe_path("original/test.jpg")
    assert path == (temp_storage_path / "original/test.jpg").resolve()

def test_safe_path_traversal(storage_service):
    with pytest.raises(ValueError) as excinfo:
        storage_service._get_safe_path("../test.jpg")
    assert "Path traversal detected" in str(excinfo.value)

    with pytest.raises(ValueError):
        storage_service._get_safe_path("original/../../test.jpg")

    with pytest.raises(ValueError):
        storage_service._get_safe_path("/etc/passwd")

def test_generate_object_key(storage_service):
    key = storage_service.generate_object_key("claim123", "image.jpg")
    assert key.startswith("original/claim123/")
    assert key.endswith("_image.jpg")
