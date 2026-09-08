from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile, File
from datetime import datetime
import uuid
import os
import shutil
from PIL import Image
import io

from app.models.photo import Photo
from app.models.user import User
from app.config import settings

class PhotoService:
    """Service for photo management"""
    
    @staticmethod
    def get_user_photos(db: Session, user_id: str) -> List[Dict[str, Any]]:
        """Get all photos for a user"""
        try:
            photos = db.query(Photo).filter(
                Photo.user_id == user_id
            ).order_by(Photo.order.asc()).all()
        except Exception as e:
            print(f"❌ Error fetching photos: {e}")
            return []
        
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
    
    @staticmethod
    def get_primary_photo(db: Session, user_id: str) -> Optional[Photo]:
        """Get the primary photo for a user"""
        try:
            return db.query(Photo).filter(
                Photo.user_id == user_id,
                Photo.is_primary == True
            ).first()
        except Exception:
            return None
    
    @staticmethod
    async def upload_photo(
        db: Session,
        user_id: str,
        file: UploadFile,
        is_primary: bool = False
    ) -> Photo:
        """Upload a photo for a user"""
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        photo_count = db.query(Photo).filter(Photo.user_id == user_id).count()
        
        # Get max photos allowed based on subscription
        if user.subscription_status.value == "free":
            max_photos = settings.FREE_TIER["max_photos"]
        else:
            max_photos = settings.PREMIUM_TIER["max_photos"]
        
        if photo_count >= max_photos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {max_photos} photos allowed for your subscription plan"
            )
        
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"{user_id}_{uuid.uuid4().hex}{file_extension}"
        
        # For MVP, save locally (in production, upload to S3)
        upload_dir = os.path.join(settings.DATA_DIR, "photos", user_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        
        # Save original file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Create thumbnails
        img = Image.open(io.BytesIO(content))
        
        # Create thumbnail (200x200)
        thumbnail_path = os.path.join(upload_dir, f"thumb_{filename}")
        img_copy = img.copy()
        img_copy.thumbnail((200, 200))
        img_copy.save(thumbnail_path)
        
        # Create medium (600x600)
        medium_path = os.path.join(upload_dir, f"medium_{filename}")
        img_copy = img.copy()
        img_copy.thumbnail((600, 600))
        img_copy.save(medium_path)
        
        # Create large (1200x1200)
        large_path = os.path.join(upload_dir, f"large_{filename}")
        img_copy = img.copy()
        img_copy.thumbnail((1200, 1200))
        img_copy.save(large_path)
        
        # Create photo record
        photo = Photo(
            id=str(uuid.uuid4()),
            user_id=user_id,
            url_original=f"/photos/{user_id}/{filename}",
            url_thumbnail=f"/photos/{user_id}/thumb_{filename}",
            url_medium=f"/photos/{user_id}/medium_{filename}",
            url_large=f"/photos/{user_id}/large_{filename}",
            s3_key=f"{user_id}/{filename}",
            file_size=len(content),
            width=img.width,
            height=img.height,
            order=photo_count,
            is_primary=is_primary
        )
        
        db.add(photo)
        
        # If this is the first photo, make it primary
        if photo_count == 0:
            photo.is_primary = True
        
        # If setting as primary, unset others
        if is_primary:
            db.query(Photo).filter(Photo.user_id == user_id).update({"is_primary": False})
            photo.is_primary = True
        
        db.commit()
        db.refresh(photo)
        
        return photo
    
    @staticmethod
    def delete_photo(db: Session, user_id: str, photo_id: str) -> bool:
        """Delete a photo"""
        photo = db.query(Photo).filter(
            Photo.id == photo_id,
            Photo.user_id == user_id
        ).first()
        
        if not photo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Photo not found"
            )
        
        # Delete files from disk
        upload_dir = os.path.join(settings.DATA_DIR, "photos", user_id)
        for url in [photo.url_original, photo.url_thumbnail, photo.url_medium, photo.url_large]:
            if url:
                file_path = os.path.join(upload_dir, os.path.basename(url))
                if os.path.exists(file_path):
                    os.remove(file_path)
        
        db.delete(photo)
        db.commit()
        
        # If deleted photo was primary, set another as primary
        if photo.is_primary:
            next_photo = db.query(Photo).filter(Photo.user_id == user_id).first()
            if next_photo:
                next_photo.is_primary = True
                db.commit()
        
        return True
    
    @staticmethod
    def set_primary_photo(db: Session, user_id: str, photo_id: str) -> Photo:
        """Set a photo as primary"""
        photo = db.query(Photo).filter(
            Photo.id == photo_id,
            Photo.user_id == user_id
        ).first()
        
        if not photo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Photo not found"
            )
        
        # Unset all other primary photos
        db.query(Photo).filter(Photo.user_id == user_id).update({"is_primary": False})
        
        photo.is_primary = True
        db.commit()
        db.refresh(photo)
        
        return photo
    
    @staticmethod
    def reorder_photos(db: Session, user_id: str, photo_order: List[str]) -> bool:
        """Reorder photos"""
        photos = db.query(Photo).filter(Photo.user_id == user_id).all()
        
        # Create a mapping of photo_id to order
        order_map = {photo_id: idx for idx, photo_id in enumerate(photo_order)}
        
        for photo in photos:
            if str(photo.id) in order_map:
                photo.order = order_map[str(photo.id)]
        
        db.commit()
        return True