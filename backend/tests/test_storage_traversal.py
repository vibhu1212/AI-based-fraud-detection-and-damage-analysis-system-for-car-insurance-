import unittest
import io
import os
import shutil
from pathlib import Path
from unittest.mock import patch
from app.services.storage import StorageService

class TestStorageServiceTraversal(unittest.TestCase):
    def setUp(self):
        # Create a temporary storage directory for testing
        self.test_storage_path = Path("./test_storage_dir")
        self.test_storage_path.mkdir(exist_ok=True)

        # We need to mock settings.STORAGE_PATH to use our test directory
        # The mock needs to be active when StorageService is instantiated
        with patch('app.services.storage.settings') as mock_settings:
            mock_settings.STORAGE_PATH = str(self.test_storage_path)
            self.storage_service = StorageService()

        # Create a dummy file outside the storage directory to attempt to access
        self.outside_file = Path("./outside_secret.txt")
        with open(self.outside_file, "w") as f:
            f.write("secret data")

    def tearDown(self):
        # Clean up test directories and files
        if self.test_storage_path.exists():
            shutil.rmtree(self.test_storage_path)
        if self.outside_file.exists():
            self.outside_file.unlink()

    def test_secure_path_resolution(self):
        # Test valid path
        valid_path = self.storage_service._get_secure_path("original/123/file.jpg")
        self.assertIsNotNone(valid_path)
        self.assertTrue(str(valid_path).startswith(str(self.test_storage_path.resolve())))

        # Test path traversal attempts
        traversal_attempts = [
            "../../../outside_secret.txt",
            "/etc/passwd",
            "C:\\Windows\\System32\\cmd.exe",
            "original/123/../../../../outside_secret.txt",
            "\\absolute\\path"
        ]

        for attempt in traversal_attempts:
            path = self.storage_service._get_secure_path(attempt)
            self.assertIsNone(path, f"Path traversal attempt failed to block: {attempt}")

    def test_upload_file_blocks_traversal(self):
        dummy_file = io.BytesIO(b"test data")
        with self.assertRaises(ValueError) as context:
            self.storage_service.upload_file(dummy_file, "../../../outside_secret.txt")
        self.assertIn("Invalid object key path", str(context.exception))

    def test_download_file_blocks_traversal(self):
        result = self.storage_service.download_file("../../../outside_secret.txt")
        self.assertIsNone(result)

    def test_delete_file_blocks_traversal(self):
        result = self.storage_service.delete_file("../../../outside_secret.txt")
        self.assertFalse(result)
        # Ensure the file was not actually deleted
        self.assertTrue(self.outside_file.exists())

    def test_file_exists_blocks_traversal(self):
        result = self.storage_service.file_exists("../../../outside_secret.txt")
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
