from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta

from app.models.user import User
from app.models.profile import Profile
from app.models.photo import Photo
from app.utils.constants import UserStatus

class UserService:
    """Service for user management operations"""
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """Get a user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get a user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def update_user(db: Session, user: User, update_data: Dict[str, Any]) -> User:
        """Update user information"""
        for key, value in update_data.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def update_location(db: Session, user: User, latitude: float, longitude: float) -> User:
        """Update user's location"""
        user.latitude = latitude
        user.longitude = longitude
        user.location_updated_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def update_online_status(db: Session, user: User, is_online: bool) -> User:
        """Update user's online status"""
        user.is_online = is_online
        user.last_active_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def get_user_profile_completeness(db: Session, user_id: str) -> int:
        """Calculate profile completeness score (0-100)"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return 0
        
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        if not profile:
            return 0
        
        score = 0
        total_fields = 0
        
        # User fields
        if user.first_name and user.last_name:
            score += 5
        total_fields += 1
        
        if user.date_of_birth:
            score += 5
        total_fields += 1
        
        if user.gender:
            score += 5
        total_fields += 1
        
        # Profile fields
        if profile.bio:
            score += 10
        total_fields += 1
        
        if profile.about_me:
            score += 10
        total_fields += 1
        
        if profile.interests:
            score += 10
        total_fields += 1
        
        if profile.prompt_1_answer and profile.prompt_2_answer and profile.prompt_3_answer:
            score += 15
        total_fields += 1
        
        if profile.education or profile.occupation:
            score += 10
        total_fields += 1
        
        # Photos
        photo_count = db.query(Photo).filter(Photo.user_id == user_id).count()
        if photo_count >= 3:
            score += 20
        elif photo_count >= 1:
            score += 10
        total_fields += 1
        
        # Calculate percentage
        return min(100, int((score / (total_fields * 10)) * 100)) if total_fields > 0 else 0
    
    @staticmethod
    def deactivate_user(db: Session, user: User) -> User:
        """Deactivate a user account"""
        user.is_active = False
        user.is_online = False
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def get_user_stats(db: Session, user_id: str) -> Dict[str, Any]:
        """Get user statistics"""
        from app.models.match import Match
        from app.models.swipe import Swipe
        from app.models.message import Message
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        # Count matches
        matches_count = db.query(Match).filter(
            (Match.user_1_id == user_id) | (Match.user_2_id == user_id),
            Match.is_active == True
        ).count()
        
        # Count messages sent
        messages_sent = db.query(Message).filter(Message.sender_id == user_id).count()
        
        # Count swipes (likes)
        likes_given = db.query(Swipe).filter(
            Swipe.swiper_id == user_id,
            Swipe.direction == "like"
        ).count()
        
        likes_received = db.query(Swipe).filter(
            Swipe.swiped_id == user_id,
            Swipe.direction == "like"
        ).count()
        
        return {
            "user_id": str(user.id),
            "matches": matches_count,
            "messages_sent": messages_sent,
            "likes_given": likes_given,
            "likes_received": likes_received,
            "subscription_status": user.subscription_status.value,
            "is_verified": user.is_verified,
            "profile_completeness": UserService.get_user_profile_completeness(db, user_id)
        }