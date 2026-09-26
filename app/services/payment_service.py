from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
import json
import time
import httpx
import uuid
from app.models.user import User
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.config import settings
from app.utils.constants import PaymentStatus, SubscriptionStatus, UserStatus
from app.services.subscription_service import SubscriptionService


CHAPA_API_BASE = "https://api.chapa.co/v1"


class PaymentService:
    """Service for payment processing with Chapa"""

    @staticmethod
    def _auth_headers() -> Dict[str, str]:
        if not settings.CHAPA_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chapa secret key is not configured",
            )
        return {
            "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def get_plan_details(plan_type: str) -> Dict[str, Any]:
        """Get plan details from settings"""
        plan = settings.PLANS.get(plan_type)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid plan type: {plan_type}",
            )
        return plan

    @staticmethod
    async def initialize_payment(
        db: Session,
        user_id: str,
        plan_type: str,
        email: str,
        currency: str = "ETB", 
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Initialize a payment with Chapa"""
        plan = PaymentService.get_plan_details(plan_type)

        user_id = str(user_id)
        tx_ref = f"aph-{uuid.uuid4().hex[:20]}"

        payment = Payment(
            user_id=user_id,
            chapa_tx_ref=tx_ref,
            amount=plan["price"],
            plan_type=plan_type,
            description=plan["name"],
            status=PaymentStatus.PENDING,
        )
        db.add(payment)
        db.flush()

        try:
            payload = {
                "email": email,
                "amount": str(plan["price"]),
                "currency": currency,
                "first_name": first_name or "User",
                "last_name": last_name or "",
                "tx_ref": tx_ref,
                "callback_url": f"{settings.BASE_URL}/api/payments/verify",
                "return_url": f"{settings.BASE_URL}/api/payments/redirect?tx_ref={tx_ref}",
                "customization": {
                    "title": f"Aphri - {plan['name']}",
                    "description": plan["description"],
                },
            }

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{CHAPA_API_BASE}/transaction/initialize",
                    headers=PaymentService._auth_headers(),
                    json=payload,
                )

            try:
                response = resp.json()
            except Exception:
                response = {"raw": resp.text}

            if resp.status_code >= 400 or response.get("status") != "success":
                payment.status = PaymentStatus.FAILED
                payment.chapa_response = json.dumps(response)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Chapa initialize failed: {response}",
                )

            data = response.get("data") or {}
            payment.chapa_transaction_id = data.get("transaction_id")
            payment.chapa_response = json.dumps(response)
            db.commit()

            return {
                "payment_id": str(payment.id),
                "tx_ref": tx_ref,
                "checkout_url": data.get("checkout_url"),
                "amount": plan["price"],
                "plan": plan_type,
                "status": "pending",
            }

        except HTTPException:
            raise
        except Exception as e:
            import traceback
            traceback.print_exc()
            payment.status = PaymentStatus.FAILED
            payment.chapa_response = json.dumps({"error": repr(e)})
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Payment initialization failed: {repr(e)}",
            )

    @staticmethod
    async def verify_payment(db: Session, tx_ref: str, user_id: str) -> Dict[str, Any]:
        """Verify a payment with Chapa"""
        user_id = str(user_id)

        payment = db.query(Payment).filter(
            Payment.chapa_tx_ref == tx_ref,
            Payment.user_id == user_id,
        ).first()

        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found",
            )

        if payment.status == PaymentStatus.SUCCEEDED:
            return {
                "status": "succeeded",
                "message": "Payment already verified",
                "payment_id": str(payment.id),
            }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{CHAPA_API_BASE}/transaction/verify/{tx_ref}",
                    headers=PaymentService._auth_headers(),
                )

            try:
                verification = resp.json()
            except Exception:
                verification = {"raw": resp.text}

            if verification.get("status") == "success":
                payment.status = PaymentStatus.SUCCEEDED
                payment.paid_at = datetime.utcnow()
                payment.chapa_response = json.dumps(verification)
                db.commit()

                subscription = await SubscriptionService.activate_subscription(
                    db, payment.user_id, payment.plan_type, tx_ref
                )

                from app.services.credit_service import CreditService
                CreditService.grant_credits(db, payment.user_id, payment.plan_type)

                return {
                    "status": "succeeded",
                    "message": "Payment verified successfully",
                    "payment_id": str(payment.id),
                    "subscription_id": str(subscription.id),
                }
            else:
                payment.status = PaymentStatus.FAILED
                payment.chapa_response = json.dumps(verification)
                db.commit()

                return {
                    "status": "failed",
                    "message": "Payment verification failed",
                    "payment_id": str(payment.id),
                }

        except HTTPException:
            raise
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Verification failed: {repr(e)}",
            )

    @staticmethod
    async def handle_webhook(db: Session, payload: Dict[str, Any]) -> bool:
        """Handle Chapa webhook"""
        event = payload.get("event")
        data = payload.get("data", {})
        tx_ref = data.get("tx_ref")

        if not tx_ref:
            return False

        payment = db.query(Payment).filter(
            Payment.chapa_tx_ref == tx_ref
        ).first()

        if not payment:
            return False

        if event == "payment.success":
            payment.status = PaymentStatus.SUCCEEDED
            payment.paid_at = datetime.utcnow()
            payment.chapa_response = json.dumps(payload)
            db.commit()

            await SubscriptionService.activate_subscription(
                db, payment.user_id, payment.plan_type, tx_ref
            )

            from app.services.credit_service import CreditService
            CreditService.grant_credits(db, payment.user_id, payment.plan_type)

        elif event == "payment.failed":
            payment.status = PaymentStatus.FAILED
            payment.chapa_response = json.dumps(payload)
            db.commit()

        elif event == "payment.refunded":
            payment.status = PaymentStatus.REFUNDED
            payment.refunded_at = datetime.utcnow()
            payment.chapa_response = json.dumps(payload)
            db.commit()

            await SubscriptionService.deactivate_subscription(db, payment.user_id)

        return True

    @staticmethod
    def get_payment_history(db: Session, user_id: str, limit: int = 20) -> list:
        """Get payment history for a user"""
        user_id = str(user_id)

        payments = db.query(Payment).filter(
            Payment.user_id == user_id
        ).order_by(Payment.created_at.desc()).limit(limit).all()

        result = []
        for payment in payments:
            result.append({
                "id": str(payment.id),
                "amount": payment.amount,
                "plan_type": payment.plan_type,
                "status": payment.status.value if hasattr(payment.status, "value") else payment.status,
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
                "created_at": payment.created_at.isoformat(),
            })

        return result