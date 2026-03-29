## 2024-03-29 - Path Traversal Vulnerability in Storage Service

**Vulnerability:**
The `StorageService` in `backend/app/services/storage.py` previously constructed file paths by directly concatenating the base storage path with user-provided object keys using `self.storage_path / object_key`. This allowed a malicious user to craft an `object_key` containing path traversal characters (like `../../etc/passwd`) or absolute paths (like `/etc/passwd`), which, when resolved, would allow reading, writing, or deleting files outside of the intended storage directory.

**Learning:**
In Python's `pathlib` module, joining a base path with a string that represents an absolute path (e.g., `/etc/passwd`) completely discards the base path. For example, `Path("/base/dir") / "/etc/passwd"` resolves to `/etc/passwd`. Additionally, concatenating `../` sequences allows navigation outside the intended directory tree. Both of these behaviors enable severe Path Traversal vulnerabilities if user input is not canonically resolved and verified against the intended base directory.

**Prevention:**
Always canonicalize paths before operating on them.
1. Strip leading slashes to prevent absolute path overrides: `clean_key = object_key.lstrip('/')`.
2. Reject keys that still look absolute or use unsafe prefix schemes (e.g., `C:\`).
3. Resolve both the base path and the target path: `base_path = self.storage_path.resolve()` and `target_path = (self.storage_path / clean_key).resolve()`.
4. Enforce containment using `pathlib`'s relative check: `target_path.is_relative_to(base_path)`.
