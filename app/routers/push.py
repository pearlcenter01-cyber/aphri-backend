from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db
from app.services.auth_service import AuthService
from app.services.push_service import PushService
from app.models.user import User
from app.schemas.push import PushTokenRegister
from app.dependencies import get_current_user

router = APIRouter()

# ============================================================
# PUSH NOTIFICATION ENDPOINTS
# ============================================================

@router.post("/register")
async def register_push_token(
    data: PushTokenRegister,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Register a device push token
    
    - **token**: FCM or APNs token
    - **device_type**: "ios" or "android"
    """
    PushService.register_token(current_user.id, data.token, data.device_type)
    return {"message": "Push token registered successfully"}

@router.post("/unregister")
async def unregister_push_token(
    data: PushTokenRegister,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Unregister a device push token
    """
    PushService.unregister_token(current_user.id, data.token)
    return {"message": "Push token unregistered successfully"}