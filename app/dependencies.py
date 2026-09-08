from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.auth_service import AuthService
from app.models.user import User

security = HTTPBearer()

# ============================================================
# MAIN get_current_user - for all routers
# ============================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from Authorization header"""
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token"
        )
    
    user = await AuthService.get_current_user(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return user


# ============================================================
# OPTIONAL get_current_user - for unauthenticated endpoints
# ============================================================

async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User | None:
    """
    Get current user if authenticated, else return None.
    Useful for endpoints that work for both authenticated and unauthenticated users.
    """
    try:
        return await AuthService.get_current_user(db, credentials.credentials)
    except HTTPException:
        return None


# ============================================================
# PREMIUM USER check
# ============================================================

async def get_premium_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Ensure the user has an active premium subscription.
    """
    if current_user.subscription_status != "premium":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required for this feature"
        )
    return current_user