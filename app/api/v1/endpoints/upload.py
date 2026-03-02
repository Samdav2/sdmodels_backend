from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.db.session import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.utils.storage_factory import storage
from app.utils.file_utils import generate_secure_filename
from app.utils.validators import (
    validate_file_size, validate_file_extension,
    ALLOWED_MODEL_EXTENSIONS, ALLOWED_IMAGE_EXTENSIONS
)
from app.core.config import settings

router = APIRouter()


@router.post("/model")
async def upload_model_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Upload 3D model file with UUID-based secure filename"""
    try:
        # Validate file extension
        if not validate_file_extension(file.filename, ALLOWED_MODEL_EXTENSIONS):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_MODEL_EXTENSIONS)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Validate file size
        if not validate_file_size(len(content), settings.MAX_MODEL_SIZE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: {settings.MAX_MODEL_SIZE / 1024 / 1024}MB"
            )
        
        # Generate secure filename with UUID
        secure_filename = generate_secure_filename(file.filename)
        print(f"Original filename: {file.filename}")
        print(f"Secure filename: {secure_filename}")
        
        # Upload to storage with secure filename
        file_url = await storage.upload_file(
            content,
            secure_filename,  # Use UUID-based filename
            file.content_type or "application/octet-stream",
            folder="models"
        )
        
        if not file_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage"
            )
        
        return {
            "file_url": file_url,
            "file_size": len(content),
            "file_format": file.filename.split('.')[-1].upper(),
            "secure_filename": secure_filename
        }
    except HTTPException:
        raise
    except httpx.ConnectTimeout:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service connection timeout. Please try again in a moment."
        )
    except httpx.ReadTimeout:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Storage service took too long to respond. File may be too large or connection is slow."
        )
    except Exception as e:
        print(f"Upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Upload image (thumbnail, preview) with UUID-based secure filename"""
    try:
        # Validate file extension
        if not validate_file_extension(file.filename, ALLOWED_IMAGE_EXTENSIONS):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Validate file size
        if not validate_file_size(len(content), settings.MAX_IMAGE_SIZE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: {settings.MAX_IMAGE_SIZE / 1024 / 1024}MB"
            )
        
        # Generate secure filename with UUID
        secure_filename = generate_secure_filename(file.filename)
        print(f"Uploading image: {file.filename} -> {secure_filename}")
        
        # Upload to storage with secure filename
        file_url = await storage.upload_file(
            content,
            secure_filename,  # Use UUID-based filename
            file.content_type or "image/jpeg",
            folder="images"
        )
        
        if not file_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage"
            )
        
        print(f"Image uploaded successfully: {file_url}")
        return {
            "image_url": file_url,
            "secure_filename": secure_filename
        }
    except HTTPException:
        raise
    except httpx.ConnectTimeout:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service connection timeout. Please try again in a moment."
        )
    except httpx.ReadTimeout:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Storage service took too long to respond. File may be too large or connection is slow."
        )
    except Exception as e:
        print(f"Image upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Upload user avatar with UUID-based secure filename"""
    try:
        # Validate file extension
        if not validate_file_extension(file.filename, ALLOWED_IMAGE_EXTENSIONS):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Validate file size
        if not validate_file_size(len(content), settings.MAX_AVATAR_SIZE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: {settings.MAX_AVATAR_SIZE / 1024 / 1024}MB"
            )
        
        # Generate secure filename with UUID (include user_id for organization)
        secure_filename = generate_secure_filename(f"avatar_{current_user.id}_{file.filename}")
        
        # Upload to storage with secure filename
        file_url = await storage.upload_file(
            content,
            secure_filename,  # Use UUID-based filename
            file.content_type or "image/jpeg",
            folder="avatars"
        )
        
        if not file_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage"
            )
        
        return {
            "avatar_url": file_url,
            "secure_filename": secure_filename
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Avatar upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/document")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Upload document"""
    # Upload to storage
    content = await file.read()
    file_url = await storage.upload_file(
        content,
        file.filename,
        file.content_type,
        folder="documents"
    )
    
    if not file_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )
    
    return {"file_url": file_url}


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete uploaded file"""
    # TODO: Implement file deletion with proper authorization
    return {"message": "File deleted"}
