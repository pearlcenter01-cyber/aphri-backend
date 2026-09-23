from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.models.profile import Profile
from app.models.photo import Photo  # ✅ ADD THIS
from app.database import get_db
from app.services.auth_service import AuthService
from app.services.profile_service import ProfileService
from app.services.user_service import UserService
from app.schemas.profile import ProfileUpdate, ProfileResponse
from app.models.user import User
from uuid import UUID  # ✅ ADD THIS
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================
# DEPENDENCIES
# ============================================================

async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Header(None, alias="Authorization")
) -> User:
    """Get current user from Authorization header"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token"
        )
    # Remove "Bearer " prefix
    if token.startswith("Bearer "):
        token = token[7:]
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token"
        )
    return await AuthService.get_current_user(db, token)

# ============================================================
# PROFILE ENDPOINTS
# ============================================================

@router.get("/me")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current user's profile
    """
    try:
        profile = ProfileService.get_profile(db, current_user.id)
        
        # If profile doesn't exist, create an empty one
        if not profile:
            profile = Profile(user_id=current_user.id)
            db.add(profile)
            db.commit()
            db.refresh(profile)
        
        return {
            "user": {
                "id": str(current_user.id),
                "email": current_user.email,
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "date_of_birth": current_user.date_of_birth.isoformat() if current_user.date_of_birth else None,
                "gender": current_user.gender,
                "looking_for": current_user.looking_for,
                "intimate_type": current_user.intimate_type,
                "subscription_status": current_user.subscription_status.value,
                "is_verified": current_user.is_verified,
                "is_online": current_user.is_online,
                "last_active_at": current_user.last_active_at.isoformat() if current_user.last_active_at else None,
            },
            "profile": {
                "id": str(profile.id) if profile else None,
                "bio": profile.bio if profile else None,
                "about_me": profile.about_me if profile else None,
                "headline": profile.headline if profile else None,
                "interests": profile.interests.split(",") if profile and profile.interests else [],
                "looking_for": profile.looking_for if profile else None,
                "prompts": [
                    {
                        "question": profile.prompt_1,
                        "answer": profile.prompt_1_answer
                    } if profile else None,
                    {
                        "question": profile.prompt_2,
                        "answer": profile.prompt_2_answer
                    } if profile else None,
                    {
                        "question": profile.prompt_3,
                        "answer": profile.prompt_3_answer
                    } if profile else None,
                ] if profile else [],
                "education": profile.education if profile else None,
                "occupation": profile.occupation if profile else None,
                "company": profile.company if profile else None,
                "hometown": profile.hometown if profile else None,
                "smoking": profile.smoking if profile else None,
                "drinking": profile.drinking if profile else None,
                "religion": profile.religion if profile else None,
                "zodiac": profile.zodiac if profile else None,
                "completeness_score": profile.completeness_score if profile else 0,
                "is_registration_complete": current_user.is_registration_complete,
            }
        }
    except Exception as e:
        logger.error(f"❌ Error loading profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading profile: {str(e)}"
        )

@router.put("/me")
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update current user's profile
    """
    # Update user fields
        
    if profile_data.custom_questions is not None:
        current_user.custom_questions = profile_data.custom_questions
    if profile_data.is_registration_complete is not None:
        current_user.is_registration_complete = profile_data.is_registration_complete
    if profile_data.custom_questions is not None or profile_data.is_registration_complete is not None:
        db.commit()

    user_update = {}

    
    if profile_data.first_name is not None:
        user_update["first_name"] = profile_data.first_name
    if profile_data.last_name is not None:
        user_update["last_name"] = profile_data.last_name
    if profile_data.date_of_birth is not None:
        user_update["date_of_birth"] = profile_data.date_of_birth
    if profile_data.gender is not None:
        user_update["gender"] = profile_data.gender
    
    if user_update:
        UserService.update_user(db, current_user, user_update)
    
    # Update profile fields
    profile_update = profile_data.dict(exclude_none=True)
    profile_update.pop("first_name", None)
    profile_update.pop("last_name", None)
    profile_update.pop("date_of_birth", None)
    profile_update.pop("gender", None)
    profile_update.pop("custom_questions", None)
    profile_update.pop("is_registration_complete", None)
    
    if profile_update:
        ProfileService.create_or_update_profile(db, current_user.id, profile_update)
    
    return {"message": "Profile updated successfully"}

@router.get("/{user_id}")
async def get_public_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get public profile of another user
    """
    print(f"🔍 Looking for user: {user_id}")
    
    # Get the user using string directly
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    
    if not user:
        print(f"❌ User not found: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get profile
    profile = ProfileService.get_profile(db, user_id)
    
    # Get photos
    photos = db.query(Photo).filter(Photo.user_id == user_id).all()
    photo_urls = [photo.url_thumbnail for photo in photos]
    
    return {
        "user": {
            "id": str(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "age": user.age,
            "gender": user.gender,
            "looking_for": user.looking_for,
            "intimate_type": user.intimate_type,
            "is_online": user.is_online,
            "subscription_status": user.subscription_status.value,
        },
        "profile": {
            "bio": profile.bio if profile else None,
            "about_me": profile.about_me if profile else None,  # ✅ ADD THIS
            "favorite_quote": profile.favorite_quote if profile else None,  # ✅ ADD THIS
            "headline": profile.headline if profile else None,
            "interests": profile.interests.split(",") if profile and profile.interests else [],
            "education": profile.education if profile else None,
            "occupation": profile.occupation if profile else None,
            "smoking": profile.smoking if profile else None,
            "drinking": profile.drinking if profile else None,
            "religion": profile.religion if profile else None,
            "zodiac": profile.zodiac if profile else None,  # ✅ ADD THIS (optional)
            "photos": photo_urls,
        }
    }
    
@router.get("/me/completeness")
async def get_profile_completeness(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get profile completeness score
    """
    score = UserService.get_user_profile_completeness(db, current_user.id)
    
    return {
        "completeness_score": score,
        "suggestions": []
    }