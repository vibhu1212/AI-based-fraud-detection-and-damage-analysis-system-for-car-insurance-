## 2024-05-18 - Path Traversal Vulnerability in Storage Service
**Vulnerability:** The Storage Service constructed file paths using user-provided strings directly (e.g., `self.storage_path / object_key`) without proper validation, leading to potential path traversal (LFI/RFI) allowing arbitrary file access/deletion.
**Learning:** Using `pathlib.Path` concatenation (`/`) alone is not sufficient to prevent path traversal when handling unsanitized paths, especially those containing `../` or leading slashes. Absolute paths bypass the intended base directory.
**Prevention:** To safely handle user-provided paths with `pathlib`:
1. Strip leading slashes from user input (`path_string.lstrip('/')`).
2. Construct the full path and securely resolve it `(base_path / safe_string).resolve()`.
3. Verify that the resolved path originates from the expected root directory using `.is_relative_to(base_path.resolve())`.
