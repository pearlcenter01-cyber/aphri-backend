from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.auth_service import AuthService
from app.models.user import User

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
    if token.startswith("Bearer "):
        token = token[7:]
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token"
        )
    return await AuthService.get_current_user(db, token)