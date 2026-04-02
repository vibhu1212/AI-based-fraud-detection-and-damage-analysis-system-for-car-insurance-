## 2024-03-18 - [Path Traversal in StorageService]
**Vulnerability:** The `StorageService` in `backend/app/services/storage.py` allowed path traversal via `download_file`, `delete_file`, and `file_exists` methods. The `object_key` was directly concatenated to the base storage path without validation, allowing access to arbitrary files (e.g., `../../etc/passwd`).
**Learning:** `pathlib`'s `/` operator does not automatically prevent traversing above the base directory. Simply appending user input to a `Path` object is insecure.
**Prevention:** Always use `resolve()` on both the target file path and the base storage path, and then use `is_relative_to()` to ensure the resolved target file remains within the authorized base directory boundary.
