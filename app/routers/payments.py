from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db, SessionLocal
from app.services.auth_service import AuthService
from app.services.payment_service import PaymentService
from app.services.subscription_service import SubscriptionService
from app.models.user import User
from app.models.payment import Payment
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
        db=db,
        user_id=current_user.id,
        plan_type=payment_data.plan_type,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
    )
@router.get("/verify")
async def verify_payment(
    tx_ref: str = "",
    trx_ref: str = "",
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Verify a payment. Public endpoint — called by Chapa (uses trx_ref)
    and by the app after redirect (uses tx_ref).
    """
    ref = trx_ref or tx_ref
    if not ref:
        raise HTTPException(status_code=400, detail="Missing transaction reference")

    # Find the payment record to know which user it belongs to
    payment = db.query(Payment).filter(Payment.chapa_tx_ref == ref).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return await PaymentService.verify_payment(db, ref, str(payment.user_id))

@router.get("/redirect", response_class=HTMLResponse)
async def payment_redirect(tx_ref: str = ""):
    """
    Chapa return_url lands here after checkout.
    Verifies the payment server-side, then shows a success page.
    """
    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.chapa_tx_ref == tx_ref).first()
        if payment:
            try:
                await PaymentService.verify_payment(db, tx_ref, str(payment.user_id))
            except Exception:
                import traceback
                traceback.print_exc()
    finally:
        db.close()

    return """<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Payment Successful</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; text-align: center; padding: 60px 24px; color: #222; background: #fafafa; margin: 0; }
      h1 { font-size: 24px; margin-bottom: 12px; }
      p { font-size: 16px; color: #555; line-height: 1.5; }
      .check { font-size: 64px; margin-bottom: 16px; color: #22c55e; }
      .card { background: #fff; max-width: 380px; margin: 0 auto; padding: 40px 24px; border-radius: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
    </style>
  </head>
  <body>
    <div class="card">
      <div class="check">&#10003;</div>
      <h1>Payment Successful</h1>
      <p>You can close this window and return to the app.</p>
    </div>
  </body>
</html>
"""

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