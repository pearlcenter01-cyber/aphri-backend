from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
import os
import json

from app.models.user import User
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.config import settings
from app.utils.constants import PaymentStatus, SubscriptionStatus, UserStatus

# Chapa SDK
try:
    from chapa import Chapa
    CHAPA_AVAILABLE = True
except ImportError:
    CHAPA_AVAILABLE = False
    print("⚠️  Chapa SDK not installed. Install with: pip install chapa-py9")

class PaymentService:
    """Service for payment processing with Chapa"""
    
    @staticmethod
    def get_chapa_client():
        """Get Chapa client instance"""
        if not CHAPA_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment service is not configured"
            )
        
        if not settings.CHAPA_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chapa secret key is not configured"
            )
        
        return Chapa(settings.CHAPA_SECRET_KEY)
    
    @staticmethod
    def get_plan_details(plan_type: str) -> Dict[str, Any]:
        """Get plan details from settings"""
        plan = settings.PLANS.get(plan_type)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid plan type: {plan_type}"
            )
        return plan
    
    @staticmethod
    async def initialize_payment(
        db: Session,
        user_id: str,
        plan_type: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initialize a payment with Chapa"""
        # Get plan details
        plan = PaymentService.get_plan_details(plan_type)
        
        # Generate unique transaction reference
        import time
        tx_ref = f"aphri-{user_id}-{int(time.time())}"
        
        # Create payment record
        payment = Payment(
            user_id=user_id,
            chapa_tx_ref=tx_ref,
            amount=plan["price"],
            plan_type=plan_type,
            description=plan["name"],
            status=PaymentStatus.PENDING
        )
        db.add(payment)
        db.flush()
        
        try:
            # Initialize with Chapa
            chapa = PaymentService.get_chapa_client()
            
            response = chapa.initialize(
                email=email,
                amount=plan["price"],
                first_name=first_name or "User",
                last_name=last_name or "",
                tx_ref=tx_ref,
                callback_url=f"{settings.BASE_URL}/api/payments/verify",
                customization={
                    "title": f"Aphri - {plan['name']}",
                    "description": plan["description"]
                }
            )
            
            # Update payment with transaction ID
            payment.chapa_transaction_id = response.get('data', {}).get('transaction_id')
            payment.chapa_response = json.dumps(response)
            db.commit()
            
            return {
                "payment_id": str(payment.id),
                "tx_ref": tx_ref,
                "checkout_url": response.get('data', {}).get('checkout_url'),
                "amount": plan["price"],
                "plan": plan_type,
                "status": "pending"
            }
            
        except Exception as e:
            payment.status = PaymentStatus.FAILED
            payment.chapa_response = json.dumps({"error": str(e)})
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Payment initialization failed: {str(e)}"
            )
    
    @staticmethod
    async def verify_payment(db: Session, tx_ref: str, user_id: str) -> Dict[str, Any]:
        """Verify a payment with Chapa"""
        # Get payment record
        payment = db.query(Payment).filter(
            Payment.chapa_tx_ref == tx_ref,
            Payment.user_id == user_id
        ).first()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        if payment.status == PaymentStatus.SUCCEEDED:
            return {
                "status": "succeeded",
                "message": "Payment already verified",
                "payment_id": str(payment.id)
            }
        
        try:
            chapa = PaymentService.get_chapa_client()
            verification = chapa.verify(tx_ref)
            
            if verification.get('status') == 'success':
                # Update payment
                payment.status = PaymentStatus.SUCCEEDED
                payment.paid_at = datetime.utcnow()
                payment.chapa_response = json.dumps(verification)
                db.commit()
                
                # Activate subscription
                subscription = await SubscriptionService.activate_subscription(
                    db, user_id, payment.plan_type, tx_ref
                )
                
                return {
                    "status": "succeeded",
                    "message": "Payment verified successfully",
                    "payment_id": str(payment.id),
                    "subscription_id": str(subscription.id)
                }
            else:
                payment.status = PaymentStatus.FAILED
                payment.chapa_response = json.dumps(verification)
                db.commit()
                
                return {
                    "status": "failed",
                    "message": "Payment verification failed",
                    "payment_id": str(payment.id)
                }
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Verification failed: {str(e)}"
            )
    
    @staticmethod
    async def handle_webhook(db: Session, payload: Dict[str, Any]) -> bool:
        """Handle Chapa webhook"""
        event = payload.get('event')
        data = payload.get('data', {})
        tx_ref = data.get('tx_ref')
        
        if not tx_ref:
            return False
        
        # Get payment
        payment = db.query(Payment).filter(
            Payment.chapa_tx_ref == tx_ref
        ).first()
        
        if not payment:
            return False
        
        if event == 'payment.success':
            payment.status = PaymentStatus.SUCCEEDED
            payment.paid_at = datetime.utcnow()
            payment.chapa_response = json.dumps(payload)
            db.commit()
            
            # Activate subscription
            await SubscriptionService.activate_subscription(
                db, payment.user_id, payment.plan_type, tx_ref
            )
            
        elif event == 'payment.failed':
            payment.status = PaymentStatus.FAILED
            payment.chapa_response = json.dumps(payload)
            db.commit()
            
        elif event == 'payment.refunded':
            payment.status = PaymentStatus.REFUNDED
            payment.refunded_at = datetime.utcnow()
            payment.chapa_response = json.dumps(payload)
            db.commit()
            
            # Deactivate subscription
            await SubscriptionService.deactivate_subscription(db, payment.user_id)
        
        return True
    
    @staticmethod
    def get_payment_history(db: Session, user_id: str, limit: int = 20) -> list:
        """Get payment history for a user"""
        payments = db.query(Payment).filter(
            Payment.user_id == user_id
        ).order_by(Payment.created_at.desc()).limit(limit).all()
        
        result = []
        for payment in payments:
            result.append({
                "id": str(payment.id),
                "amount": payment.amount,
                "plan_type": payment.plan_type,
                "status": payment.status.value if hasattr(payment.status, 'value') else payment.status,
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
                "created_at": payment.created_at.isoformat()
            })
        
        return result