
## 2025-02-14 - Prevent Path Traversal in Local Storage
**Vulnerability:** User-provided object keys in StorageService could contain absolute paths, '..', or root directories, potentially exposing paths on the local file system (e.g. `/etc/passwd` or outside the intended `storage` directory) due to insecure handling of file saving/downloading.
**Learning:** Python's `Path` library is powerful, but when working with unsanitized user-provided paths joined to a directory root, relying purely on default `.resolve()` can unintentionally navigate to system paths outside the root directory. Absolute path patterns need explicitly rejecting before resolution.
**Prevention:** Implement a layered sanitization approach (`_is_safe_path`): Explicitly reject path traversal sequences (`../`) and absolute paths (`/`, `\`, `:\`). Afterward, use `Path.resolve()` and `Path.is_relative_to()` to definitively bound access to the expected directory.
