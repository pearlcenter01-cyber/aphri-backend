from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, RefreshToken
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.models.user import User  # ✅ ADD THIS
from app.dependencies import get_current_user  # ✅ ADD THIS
from app.services.firebase_service import FirebaseService
from pydantic import BaseModel

class FirebaseTokenRequest(BaseModel):
    id_token: str

router = APIRouter()

# ============================================================
# AUTH ENDPOINTS
# ============================================================

@router.post("/register", response_model=TokenResponse)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Register a new user
    
    - **email**: Valid email address
    - **password**: Minimum 8 characters
    - **first_name**: Optional first name
    - **last_name**: Optional last name
    - **phone**: Optional phone number
    """
    return await AuthService.register_user(db, user_data)

@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Login a user
    
    - **email**: Registered email address
    - **password**: Account password
    """
    return await AuthService.login_user(db, credentials)

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshToken,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Refresh access token using refresh token
    
    - **refresh_token**: Valid refresh token
    """
    return await AuthService.refresh_access_token(db, refresh_data.refresh_token)

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Logout user (invalidate token)
    """
    # JWT is stateless, so we just return success
    return {"message": "Logged out successfully"}

@router.post("/verify-email")
async def verify_email(
    email: str,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Verify email address (send verification code)
    
    Note: This is a placeholder. In production, you'd send an email.
    """
    # For MVP, just check if user exists
    user = UserService.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "Verification email sent"}

@router.post("/reset-password")
async def reset_password(
    email: str,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Request password reset
    
    Note: This is a placeholder. In production, you'd send an email.
    """
    user = UserService.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "Password reset email sent"}

@router.post("/google", response_model=TokenResponse)
async def login_with_google(
    body: FirebaseTokenRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Verify a Firebase Google ID token and return app JWTs."""
    decoded = FirebaseService.verify_id_token(body.id_token)
    return await AuthService.login_with_firebase(db, decoded, provider="google")


@router.post("/phone/verify", response_model=TokenResponse)
async def login_with_phone(
    body: FirebaseTokenRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Verify a Firebase Phone ID token and return app JWTs."""
    decoded = FirebaseService.verify_id_token(body.id_token)
    return await AuthService.login_with_firebase(db, decoded, provider="phone")    