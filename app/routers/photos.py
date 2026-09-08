from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
from uuid import UUID

from app.database import get_db
from app.services.auth_service import AuthService
from app.services.photo_service import PhotoService
from app.models.user import User
from app.models.photo import Photo
from app.dependencies import get_current_user

router = APIRouter()

# ============================================================
# PHOTO ENDPOINTS
# ============================================================

@router.post("/upload")
async def upload_photo(
    file: UploadFile = File(...),
    is_primary: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Upload a photo
    
    - **file**: Image file (JPEG, PNG)
    - **is_primary**: Set as primary photo
    """
    photo = await PhotoService.upload_photo(db, current_user.id, file, is_primary)
    
    return {
        "id": str(photo.id),
        "url_thumbnail": photo.url_thumbnail,
        "url_medium": photo.url_medium,
        "url_large": photo.url_large,
        "is_primary": photo.is_primary,
        "order": photo.order,
        "message": "Photo uploaded successfully"
    }

@router.get("/")
async def get_my_photos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get all photos for current user
    """
    try:
        photos = db.query(Photo).filter(Photo.user_id == current_user.id).order_by(Photo.order.asc()).all()
        return [
            {
                "id": str(photo.id),
                "url_thumbnail": photo.url_thumbnail,
                "url_medium": photo.url_medium,
                "url_large": photo.url_large,
                "is_primary": photo.is_primary,
                "order": photo.order,
            }
            for photo in photos
        ]
    except Exception as e:
        print(f"❌ Error in /api/photos: {e}")
        import traceback
        traceback.print_exc()
        return []

@router.delete("/{photo_id}")
async def delete_photo(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete a photo
    """
    try:
        photo_uuid = UUID(photo_id)
        photo = db.query(Photo).filter(
            Photo.id == photo_uuid,
            Photo.user_id == current_user.id
        ).first()
        
        if not photo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Photo not found"
            )
        
        db.delete(photo)
        db.commit()
        
        return {"message": "Photo deleted successfully"}
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid photo ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete photo: {str(e)}"
        )

@router.put("/{photo_id}/primary")
async def set_primary_photo(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Set a photo as primary
    """
    try:
        photo_uuid = UUID(photo_id)
        photo = PhotoService.set_primary_photo(db, current_user.id, str(photo_uuid))
        
        return {
            "id": str(photo.id),
            "is_primary": photo.is_primary,
            "message": "Primary photo updated"
        }
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid photo ID format"
        )

@router.post("/reorder")
async def reorder_photos(
    photo_order: List[str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Reorder photos
    
    - **photo_order**: List of photo IDs in desired order
    """
    PhotoService.reorder_photos(db, current_user.id, photo_order)
    return {"message": "Photos reordered successfully"}