## 2024-05-20 - Fix Path Traversal in Storage Service
**Vulnerability:** Path traversal vulnerability in Python `pathlib` usage inside `StorageService`. `self.storage_path / object_key` can be overridden by absolute paths (`object_key = '/etc/passwd'`) or navigated upwards (`object_key = '../../../etc/passwd'`).
**Learning:** `pathlib`'s `/` operator treats absolute paths on the right side as root paths, wiping out the prefix. Additionally, `pathlib` does not inherently block parent directory resolution (`..`).
**Prevention:** Before joining user provided keys to a base directory, always strip leading slashes using `.lstrip('/')`. After joining, strictly enforce the boundary using `.resolve()` and `.is_relative_to(base_dir)`.
