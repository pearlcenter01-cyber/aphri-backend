from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db
from app.services.auth_service import AuthService
from app.services.payment_service import PaymentService
from app.services.subscription_service import SubscriptionService
from app.models.user import User
from app.schemas.payment import PaymentInitiate, PaymentVerify
from app.dependencies import get_current_user

router = APIRouter()

# ============================================================
# PAYMENT ENDPOINTS
# ============================================================

@router.post("/initiate")
async def initiate_payment(
    payment_data: PaymentInitiate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Initiate a payment for subscription
    
    - **plan_type**: "monthly", "quarterly", or "yearly"
    """
    return await PaymentService.initialize_payment(
        db,
        current_user.id,
        payment_data.plan_type,
        current_user.email,
        current_user.first_name,
        current_user.last_name
    )

@router.get("/verify")
async def verify_payment(
    tx_ref: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Verify a payment after user returns from Chapa checkout
    """
    return await PaymentService.verify_payment(db, tx_ref, current_user.id)

@router.post("/webhook")
async def payment_webhook(
    request: Request,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Chapa webhook endpoint for payment status updates
    """
    try:
        payload = await request.json()
        await PaymentService.handle_webhook(db, payload)
        return {"status": "received"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )

@router.get("/history")
async def get_payment_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list:
    """
    Get payment history for current user
    """
    return PaymentService.get_payment_history(db, current_user.id, limit)

@router.get("/plans")
async def get_subscription_plans() -> Dict[str, Any]:
    """
    Get available subscription plans
    """
    from app.config import settings
    return {
        "plans": settings.PLANS,
        "currency": "ETB"
    }