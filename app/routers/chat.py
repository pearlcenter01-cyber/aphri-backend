from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from app.database import get_db
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.match_service import MatchService
from app.services.push_service import PushService
from app.services.user_service import UserService
from app.models.user import User
from app.schemas.message import MessageSend, MessageResponse
from app.dependencies import get_current_user

router = APIRouter()

# ============================================================
# CHAT ENDPOINTS
# ============================================================

@router.post("/{match_id}/send", response_model=MessageResponse)
async def send_message(
    match_id: str,
    message_data: MessageSend,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Send a message in a match
    """
    # Check if match exists and user is part of it
    match = MatchService.get_match_by_id(db, match_id, current_user.id)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    # Send message
    message = ChatService.send_message(
        db,
        match_id,
        current_user.id,
        message_data.content,
        message_data.message_type,
        message_data.media_url,
        message_data.media_thumbnail
    )
    
    # Send push notification to receiver
    other_user_id = match.get_other_user_id(current_user.id)
    other_user = UserService.get_user_by_id(db, other_user_id)
    
    if other_user:
        await PushService.send_new_message_notification(
            db,
            other_user_id,
            match_id,
            current_user.first_name or "User",
            message_data.content
        )
    
    return message

@router.put("/messages/{message_id}/read")
async def mark_message_as_read(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Mark a message as read
    """
    ChatService.mark_message_as_read(db, message_id, current_user.id)
    return {"message": "Message marked as read"}

@router.post("/{match_id}/read-all")
async def mark_all_as_read(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, int]:
    """
    Mark all messages in a match as read
    """
    count = ChatService.mark_all_as_read(db, match_id, current_user.id)
    return {"count": count}

@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete a message (for sender only)
    """
    ChatService.delete_message(db, message_id, current_user.id)
    return {"message": "Message deleted"}

@router.get("/unread")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, int]:
    """
    Get total unread messages count
    """
    count = ChatService.get_unread_count(db, current_user.id)
    return {"count": count}