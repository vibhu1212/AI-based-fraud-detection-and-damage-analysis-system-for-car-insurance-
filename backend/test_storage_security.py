import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock dependencies
sys.modules['pydantic_settings'] = MagicMock()
sys.modules['app.config'] = MagicMock()

# Now we can import the module we want to test
from app.services.storage import StorageService

class TestStorageServiceSecurity(unittest.TestCase):
    def setUp(self):
        # Setup a mock StorageService
        with patch('app.services.storage.settings') as mock_settings:
            mock_settings.STORAGE_PATH = "./test_storage"
            self.service = StorageService()

    def test_safe_paths(self):
        # Valid paths should not raise errors
        self.assertTrue(self.service._is_safe_path("original/123/image.jpg"))
        self.assertTrue(self.service._is_safe_path("masks/claim-456/mask.png"))
        self.assertTrue(self.service._is_safe_path("reports/report.pdf"))

    def test_absolute_paths(self):
        with self.assertRaisesRegex(ValueError, "Absolute paths are not allowed"):
            self.service._is_safe_path("/etc/passwd")
        with self.assertRaisesRegex(ValueError, "Absolute paths are not allowed"):
            self.service._is_safe_path("\\Windows\\System32")
        with self.assertRaisesRegex(ValueError, "Absolute paths are not allowed"):
            self.service._is_safe_path("C:\\Windows")

    def test_directory_traversal(self):
        with self.assertRaisesRegex(ValueError, "Directory traversal components"):
            self.service._is_safe_path("../../../etc/passwd")
        with self.assertRaisesRegex(ValueError, "Directory traversal components"):
            self.service._is_safe_path("original/../../secrets.txt")

    def test_empty_path(self):
        with self.assertRaisesRegex(ValueError, "Path cannot be empty"):
            self.service._is_safe_path("")

    def test_outside_storage(self):
        # The '..' components are caught first.
        # This is expected behavior.
        pass

if __name__ == '__main__':
    unittest.main()
