from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
from uuid import UUID

from app.models.user import User
from app.models.profile import Profile

class ProfileService:
    """Service for profile management"""
    
    @staticmethod
    def _ensure_uuid(value: str | UUID) -> UUID:
        """Convert string to UUID if needed, or return UUID as-is"""
        if isinstance(value, UUID):
            return value
        try:
            return UUID(value)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid UUID format: {value}"
            )
    
    @staticmethod
    def get_profile(db: Session, user_id: str) -> Optional[Profile]:
        """Get a user's profile"""
        try:
            user_uuid = ProfileService._ensure_uuid(user_id)
        except HTTPException:
            return None
        
        return db.query(Profile).filter(Profile.user_id == user_uuid).first()
    
    @staticmethod
    def create_or_update_profile(db: Session, user_id: str, profile_data: Dict[str, Any]) -> Profile:
        """Create or update a user's profile"""
        try:
            user_uuid = ProfileService._ensure_uuid(user_id)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        profile = db.query(Profile).filter(Profile.user_id == user_uuid).first()
        
        if not profile:
            # Create new profile
            profile = Profile(user_id=user_uuid)
            db.add(profile)
        
        # Update fields
        for key, value in profile_data.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)
        
        profile.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(profile)
        
        # Update user's profile completeness
        from app.services.user_service import UserService
        completeness_score = UserService.get_user_profile_completeness(db, user_uuid)
        
        # Update the profile's completeness score
        profile.completeness_score = completeness_score
        db.commit()
        db.refresh(profile)
        
        return profile
    
    @staticmethod
    def update_prompt(db: Session, user_id: str, prompt_number: int, question: str, answer: str) -> Profile:
        """Update a specific prompt"""
        try:
            user_uuid = ProfileService._ensure_uuid(user_id)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        profile = ProfileService.get_profile(db, user_uuid)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
        
        if prompt_number == 1:
            profile.prompt_1 = question
            profile.prompt_1_answer = answer
        elif prompt_number == 2:
            profile.prompt_2 = question
            profile.prompt_2_answer = answer
        elif prompt_number == 3:
            profile.prompt_3 = question
            profile.prompt_3_answer = answer
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid prompt number")
        
        profile.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(profile)
        return profile
    
    @staticmethod
    def get_public_profile(db: Session, user_id: str, viewer_id: Optional[str] = None) -> Dict[str, Any]:
        """Get a public-facing profile (with privacy filters)"""
        try:
            user_uuid = ProfileService._ensure_uuid(user_id)
            viewer_uuid = ProfileService._ensure_uuid(viewer_id) if viewer_id else None
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        user = db.query(User).filter(User.id == user_uuid, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        profile = ProfileService.get_profile(db, user_uuid)
        
        # Check if viewer is blocked
        if viewer_id:
            from app.services.report_service import ReportService
            if ReportService.is_blocked(db, user_uuid, viewer_uuid):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are blocked by this user")
        
        # Build public profile
        public_data = {
            "id": str(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "age": user.age,
            "gender": user.gender,
            "bio": profile.bio if profile else None,
            "about_me": profile.about_me if profile else None,
            "headline": profile.headline if profile else None,
            "interests": profile.interests.split(",") if profile and profile.interests else [],
            "looking_for": profile.looking_for if profile else None,
            "education": profile.education if profile else None,
            "occupation": profile.occupation if profile else None,
            "company": profile.company if profile else None,
            "hometown": profile.hometown if profile else None,
            "prompts": [
                {"question": profile.prompt_1, "answer": profile.prompt_1_answer} if profile else None,
                {"question": profile.prompt_2, "answer": profile.prompt_2_answer} if profile else None,
                {"question": profile.prompt_3, "answer": profile.prompt_3_answer} if profile else None,
            ] if profile else [],
            "is_verified": user.is_verified,
            "subscription_status": user.subscription_status.value,
            "is_online": user.is_online,
            "last_active": user.last_active_at.isoformat() if user.last_active_at else None,
        }
        
        # Get photos separately
        from app.services.photo_service import PhotoService
        photos = PhotoService.get_user_photos(db, user_uuid)
        public_data["photos"] = photos
        
        return public_data