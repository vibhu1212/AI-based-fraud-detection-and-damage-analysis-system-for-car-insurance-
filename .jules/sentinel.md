## 2025-03-26 - Path Traversal Vulnerability in `pathlib`
**Vulnerability:** A path traversal vulnerability existed in `StorageService` where user-provided `object_key` and `filename` paths (e.g. `../../../etc/passwd`) were joined with `storage_path` blindly via `/` operator, allowing files to be accessed, uploaded, or deleted anywhere on the filesystem if not properly validated.
**Learning:** Using Python's `pathlib` `base_path / user_path` directly is inherently unsafe if `user_path` contains `../` sequences or absolute paths (which evaluates exactly to the absolute path instead of a joined child). Simply calling `.resolve()` is not enough because it doesn't limit traversal.
**Prevention:** To prevent Path Traversal safely with `pathlib`:
1. Resolve the `base_dir` first: `base_dir = base_dir.resolve()`
2. Strip leading slashes from user input so it isn't treated as absolute: `user_path = str(user_path).lstrip('/')`
3. Combine and resolve: `full_path = (base_dir / user_path).resolve()`
4. Validate boundary constraints: `if not full_path.is_relative_to(base_dir): raise ValueError("Traversal Detected")`
