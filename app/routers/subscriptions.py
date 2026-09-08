from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db
from app.services.auth_service import AuthService
from app.services.subscription_service import SubscriptionService
from app.models.user import User
from app.dependencies import get_current_user

router = APIRouter()

# ============================================================
# SUBSCRIPTION ENDPOINTS
# ============================================================

@router.get("/current")
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current user's subscription details
    """
    return SubscriptionService.get_subscription_plan_info(db, current_user.id)

@router.get("/history")
async def get_subscription_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list:
    """
    Get subscription history for current user
    """
    return SubscriptionService.get_subscription_history(db, current_user.id)

@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Cancel current subscription (at end of period)
    """
    SubscriptionService.cancel_subscription(db, current_user.id)
    return {"message": "Subscription will be cancelled at the end of the current period"}

@router.post("/reactivate")
async def reactivate_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Reactivate a cancelled subscription
    """
    subscription = SubscriptionService.get_current_subscription(db, current_user.id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    if not subscription.cancel_at_period_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription is not set to cancel"
        )
    
    subscription.cancel_at_period_end = False
    db.commit()
    
    return {"message": "Subscription reactivated successfully"}