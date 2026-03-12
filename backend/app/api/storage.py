"""
Storage endpoints for serving media files locally.
In production, this would be replaced by direct S3/CDN access or signed URLs.
"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pathlib import Path
from app.services.storage import storage_service
import os

router = APIRouter()

@router.get("/{folder}/{claim_id}/{filename}")
async def get_file(folder: str, claim_id: str, filename: str):
    """
    Serve a file from storage.
    """
    # Construct object key
    object_key = f"{folder}/{claim_id}/{filename}"
    
    # Check if file exists
    file_path = storage_service.download_file(object_key)
    
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return FileResponse(file_path)
