from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.message import Message
from app.services.storage_service import StorageService

router = APIRouter()


@router.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    return await StorageService.upload_image(file)


@router.post("/upload/voice")
async def upload_voice(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    return await StorageService.upload_audio(file)


@router.patch("/{message_id}")
async def edit_message(
    message_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(404, "Message not found")
    if msg.sender_id != current_user.id:
        raise HTTPException(403, "You can only edit your own messages")
    if msg.message_type != "text":
        raise HTTPException(400, "Only text messages can be edited")
    if msg.is_deleted:
        raise HTTPException(400, "Cannot edit a deleted message")

    new_content = (payload.get("content") or "").strip()
    if not new_content:
        raise HTTPException(400, "Content is required")

    msg.content = new_content
    msg.is_edited = True
    db.commit()
    db.refresh(msg)

    return {
        "id": str(msg.id),
        "content": msg.content,
        "is_edited": msg.is_edited,
    }