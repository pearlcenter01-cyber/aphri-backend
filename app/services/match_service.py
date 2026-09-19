from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
from datetime import datetime

from app.models.user import User
from app.models.match import Match
from app.models.message import Message
from app.models.swipe import Swipe
from app.utils.constants import MatchStatus

class MatchService:
    """Service for match management"""
    
    @staticmethod
    def get_user_matches(db: Session, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all matches for a user — only mutual potential matches"""
        from app.services.swipe_service import SwipeService

        current_user = db.query(User).filter(User.id == user_id).first()
        matches = db.query(Match).filter(
            or_(
                Match.user_1_id == user_id,
                Match.user_2_id == user_id
            ),
            Match.is_active == True,
            Match.status == MatchStatus.MATCHED
        ).order_by(Match.matched_at.desc()).limit(limit).all()

        # ✅ Ask SwipeService for the real mutual matches
        try:
            valid_candidates = SwipeService.get_matches(db, user_id, 200)
            valid_user_ids = {str(c.get('id')) for c in valid_candidates if c.get('id')}
        except Exception as e:
            print(f"⚠️ SwipeService.get_matches failed: {e}")
            valid_user_ids = set()

        result = []
        for match in matches:
            if not match.id or match.id == '{}' or match.id == 'null':
                continue

            other_user_id = match.get_other_user_id(user_id)
            other_user = db.query(User).filter(User.id == other_user_id).first()

            # ✅ Skip if the other user is not a mutual match
            if str(other_user_id) not in valid_user_ids:
                print(f"🔴 Skipping non-mutual match: {other_user.email if other_user else other_user_id}")
                continue

            last_message = None
            try:
                last_message = db.query(Message).filter(
                    Message.match_id == match.id
                ).order_by(Message.created_at.desc()).first()
            except Exception as e:
                print(f"Error getting last message for match {match.id}: {e}")

            unread_count = 0
            try:
                unread_count = db.query(Message).filter(
                    Message.match_id == match.id,
                    Message.receiver_id == user_id,
                    Message.is_read == False
                ).count()
            except Exception as e:
                print(f"Error getting unread count for match {match.id}: {e}")

            result.append({
                "match_id": str(match.id),
                "user": {
                    "id": str(other_user.id) if other_user else None,
                    "first_name": other_user.first_name if other_user else None,
                    "last_name": other_user.last_name if other_user else None,
                } if other_user else None,
                "matched_at": match.matched_at.isoformat(),
                "chat_unlocked": match.is_chat_unlocked,
                "last_message": {
                    "content": last_message.content if last_message else None,
                    "created_at": last_message.created_at.isoformat() if last_message else None,
                } if last_message else None,
                "unread_count": unread_count,
                "is_active": match.is_active
            })

        return result
    
    @staticmethod
    def get_match_by_id(db: Session, match_id: str, user_id: str) -> Optional[Match]:
        """Get a match by ID, verifying user is part of it"""
        # ✅ Guard against invalid match_id
        if not match_id or match_id == '{}' or match_id == 'null' or match_id == 'undefined':
            return None
            
        match = db.query(Match).filter(
            Match.id == match_id,
            or_(
                Match.user_1_id == user_id,
                Match.user_2_id == user_id
            ),
            Match.is_active == True
        ).first()
        
        return match
    
    @staticmethod
    def get_match_with_chat_status(db: Session, match_id: str, user_id: str) -> Dict[str, Any]:
        """Get match details including chat unlock status"""
        match = MatchService.get_match_by_id(db, match_id, user_id)
        if not match:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
        
        other_user_id = match.get_other_user_id(user_id)
        other_user = db.query(User).filter(User.id == other_user_id).first()
        
        return {
            "match_id": str(match.id),
            "user": {
                "id": str(other_user.id) if other_user else None,
                "first_name": other_user.first_name if other_user else None,
                "last_name": other_user.last_name if other_user else None,
            } if other_user else None,
            "matched_at": match.matched_at.isoformat(),
            "chat_unlocked": match.is_chat_unlocked,
            "chat_unlocked_at": match.chat_unlocked_at.isoformat() if match.chat_unlocked_at else None,
            "is_active": match.is_active
        }
    
    @staticmethod
    def can_user_chat(db: Session, match_id: str, user_id: str) -> bool:
        """Check if a user can send messages in a match"""
        # ✅ Guard against invalid match_id
        if not match_id or match_id == '{}' or match_id == 'null' or match_id == 'undefined':
            return False
            
        match = db.query(Match).filter(
            Match.id == match_id,
            or_(
                Match.user_1_id == user_id,
                Match.user_2_id == user_id
            ),
            Match.is_active == True
        ).first()
        
        if not match:
            return False
        
        # Chat is unlocked if chat_unlocked_at is set and not in the future
        if match.chat_unlocked_at:
            return datetime.utcnow() >= match.chat_unlocked_at
        
        return False
    
    @staticmethod
    def approve_match(db: Session, match_id: str, user_id: str) -> Dict[str, Any]:
        """Approve a match - unlocks chat when both users approve"""
        match = db.query(Match).filter(
            Match.id == match_id,
            or_(
                Match.user_1_id == user_id,
                Match.user_2_id == user_id
            ),
            Match.is_active == True
        ).first()
        
        if not match:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
        
        match.chat_unlocked_at = datetime.utcnow()
        db.commit()
        db.refresh(match)
        
        return {
            "match_id": str(match.id),
            "chat_unlocked": True,
            "chat_unlocked_at": match.chat_unlocked_at.isoformat()
        }
    
    @staticmethod
    def update_match_activity(db: Session, match_id: str) -> None:
        """Update match activity timestamp"""
        match = db.query(Match).filter(Match.id == match_id).first()
        if match:
            match.updated_at = datetime.utcnow()
            db.commit()
    
    @staticmethod
    def unmatch(db: Session, match_id: str, user_id: str) -> bool:
        """Unmatch - deactivate a match"""
        match = db.query(Match).filter(
            Match.id == match_id,
            or_(
                Match.user_1_id == user_id,
                Match.user_2_id == user_id
            )
        ).first()
        
        if not match:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
        
        match.is_active = False
        match.status = MatchStatus.EXPIRED
        match.updated_at = datetime.utcnow()
        db.commit()
        
        return True
    
    @staticmethod
    def get_match_messages(db: Session, match_id: str, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get messages in a match"""
        # ✅ Guard against invalid match_id
        if not match_id or match_id == '{}' or match_id == 'null' or match_id == 'undefined':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid match ID")
            
        match = MatchService.get_match_by_id(db, match_id, user_id)
        if not match:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
        
        messages = db.query(Message).filter(
            Message.match_id == match_id,
            Message.is_deleted == False
        ).order_by(Message.created_at.desc()).limit(limit).offset(offset).all()
        
        # Mark messages as read
        db.query(Message).filter(
            Message.match_id == match_id,
            Message.receiver_id == user_id,
            Message.is_read == False
        ).update({"is_read": True, "read_at": datetime.utcnow()})
        db.commit()
        
        result = []
        for msg in reversed(messages):  # Show in chronological order
            result.append({
                "id": str(msg.id),
                "sender_id": str(msg.sender_id),
                "message_type": msg.message_type,
                "content": msg.content,
                "media_url": msg.media_url,
                "is_read": msg.is_read,
                "created_at": msg.created_at.isoformat(),
                "session_id": msg.session_id
            })
        
        return result
    
    @staticmethod
    def get_match_count(db: Session, user_id: str) -> int:
        """Get total match count for a user"""
        return db.query(Match).filter(
            or_(
                Match.user_1_id == user_id,
                Match.user_2_id == user_id
            ),
            Match.is_active == True,
            Match.status == MatchStatus.MATCHED
        ).count()