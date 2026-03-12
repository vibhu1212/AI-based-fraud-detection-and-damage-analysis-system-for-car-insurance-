"""
Object storage service for media files.
Supports local filesystem for demo and S3-compatible storage for production.
"""
import os
import hashlib
import shutil
from pathlib import Path
from typing import BinaryIO, Optional
from datetime import datetime, timedelta
from app.config import settings


class StorageService:
    """
    Storage service for managing media files.
    Implements local filesystem storage with S3-like interface.
    """
    
    def __init__(self):
        self.storage_path = Path(settings.STORAGE_PATH)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create storage directory structure if it doesn't exist."""
        directories = [
            self.storage_path / "original",
            self.storage_path / "redacted",
            self.storage_path / "thumbnails",
            self.storage_path / "masks",
            self.storage_path / "temp"
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def calculate_sha256(self, file: BinaryIO) -> str:
        """
        Calculate SHA-256 hash of file content.
        
        Args:
            file: File-like object
            
        Returns:
            Hexadecimal SHA-256 hash string
        """
        sha256_hash = hashlib.sha256()
        
        # Read file in chunks to handle large files
        for byte_block in iter(lambda: file.read(4096), b""):
            sha256_hash.update(byte_block)
        
        # Reset file pointer
        file.seek(0)
        
        return sha256_hash.hexdigest()
    
    def generate_object_key(self, claim_id: str, filename: str, folder: str = "original") -> str:
        """
        Generate object key for file storage.
        
        Args:
            claim_id: Claim UUID
            filename: Original filename
            folder: Storage folder (original, redacted, thumbnails, masks)
            
        Returns:
            Object key path
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        return f"{folder}/{claim_id}/{timestamp}_{safe_filename}"
    
    def upload_file(
        self,
        file: BinaryIO,
        object_key: str,
        content_type: Optional[str] = None
    ) -> dict:
        """
        Upload file to storage.
        
        Args:
            file: File-like object
            object_key: Storage key/path
            content_type: MIME type
            
        Returns:
            Dictionary with upload metadata
        """
        # Calculate SHA-256 hash
        sha256_hash = self.calculate_sha256(file)
        
        # Determine full path
        file_path = self.storage_path / object_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file, f)
        
        # Get file size
        file_size = file_path.stat().st_size
        
        return {
            "object_key": object_key,
            "sha256_hash": sha256_hash,
            "size_bytes": file_size,
            "content_type": content_type,
            "storage_path": str(file_path)
        }
    
    def download_file(self, object_key: str) -> Optional[Path]:
        """
        Get file path for download.
        
        Args:
            object_key: Storage key/path
            
        Returns:
            Path object if file exists, None otherwise
        """
        file_path = self.storage_path / object_key
        if file_path.exists():
            return file_path
        return None
    
    def generate_presigned_url(
        self,
        object_key: str,
        expiration: int = 3600
    ) -> str:
        """
        Generate presigned URL for file access.
        For local storage, returns a simple path.
        For S3, would return actual presigned URL.
        
        Args:
            object_key: Storage key/path
            expiration: URL expiration in seconds (default 1 hour)
            
        Returns:
            Presigned URL or local path
        """
        # For demo/local storage, return API endpoint path
        # In production with S3, this would generate actual presigned URL
        return f"/api/storage/{object_key}"
    
    def delete_file(self, object_key: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            object_key: Storage key/path
            
        Returns:
            True if deleted, False if file doesn't exist
        """
        file_path = self.storage_path / object_key
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def file_exists(self, object_key: str) -> bool:
        """
        Check if file exists in storage.
        
        Args:
            object_key: Storage key/path
            
        Returns:
            True if file exists, False otherwise
        """
        file_path = self.storage_path / object_key
        return file_path.exists()
    
    def store_pdf(self, pdf_bytes: bytes, filename: str) -> str:
        """
        Store PDF file in storage.
        
        Args:
            pdf_bytes: PDF file content as bytes
            filename: PDF filename
            
        Returns:
            URL/path to stored PDF
        """
        # Create reports directory if it doesn't exist
        reports_dir = self.storage_path / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate file path
        file_path = reports_dir / filename
        
        # Write PDF file
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)
        
        # Return URL
        object_key = f"reports/{filename}"
        return self.generate_presigned_url(object_key)


# Global storage service instance
storage_service = StorageService()
