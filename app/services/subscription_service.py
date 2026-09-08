from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from uuid import UUID

from app.models.user import User
from app.models.subscription import Subscription
from app.models.payment import Payment
from app.config import settings
from app.utils.constants import UserStatus, SubscriptionStatus

class SubscriptionService:
    """Service for subscription management"""
    
    @staticmethod
    def _ensure_uuid(value: str | UUID) -> UUID:
        """Convert string to UUID if needed, or return UUID as-is"""
        if isinstance(value, UUID):
            return value
        try:
            return UUID(value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid UUID format: {value}"
            )
    
    @staticmethod
    async def activate_subscription(
        db: Session,
        user_id: str,
        plan_type: str,
        tx_ref: str
    ) -> Subscription:
        """Activate a subscription for a user"""
        # Get plan details
        plan = settings.PLANS.get(plan_type)
        if not plan:
            raise ValueError(f"Invalid plan type: {plan_type}")
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Deactivate any existing active subscriptions
        existing_subs = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).all()
        
        for sub in existing_subs:
            sub.status = SubscriptionStatus.EXPIRED
        
        # Create new subscription
        now = datetime.utcnow()
        subscription = Subscription(
            user_id=user_id,
            chapa_tx_ref=tx_ref,
            plan_type=plan_type,
            plan_name=plan["name"],
            amount=plan["price"],
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=now + timedelta(days=plan["duration_days"])
        )
        
        db.add(subscription)
        
        # Update user status
        user.subscription_status = UserStatus.PREMIUM
        
        db.commit()
        db.refresh(subscription)
        
        return subscription
    
    @staticmethod
    async def deactivate_subscription(db: Session, user_id: str) -> bool:
        """Deactivate a user's subscription"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Update user status
        user.subscription_status = UserStatus.FREE
        
        # Update active subscriptions
        active_subs = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).all()
        
        for sub in active_subs:
            sub.status = SubscriptionStatus.EXPIRED
            sub.canceled_at = datetime.utcnow()
        
        db.commit()
        return True
    
    @staticmethod
    def get_current_subscription(db: Session, user_id: str) -> Optional[Subscription]:
        """Get the current active subscription for a user"""
        # ✅ GUARD - Skip if user_id is empty or invalid
        if not user_id or user_id == "{}" or user_id == "null" or user_id == "undefined":
            return None
        
        try:
            user_uuid = SubscriptionService._ensure_uuid(user_id)
        except HTTPException:
            return None
        
        return db.query(Subscription).filter(
            Subscription.user_id == user_uuid,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).first()
    
    @staticmethod
    def get_subscription_history(db: Session, user_id: str) -> list:
        """Get subscription history for a user"""
        # ✅ GUARD - Skip if user_id is empty or invalid
        if not user_id or user_id == "{}" or user_id == "null" or user_id == "undefined":
            return []
        
        try:
            user_uuid = SubscriptionService._ensure_uuid(user_id)
        except HTTPException:
            return []
        
        subscriptions = db.query(Subscription).filter(
            Subscription.user_id == user_uuid
        ).order_by(Subscription.created_at.desc()).all()
        
        result = []
        for sub in subscriptions:
            result.append({
                "id": str(sub.id),
                "plan_type": sub.plan_type,
                "plan_name": sub.plan_name,
                "amount": sub.amount,
                "status": sub.status.value if hasattr(sub.status, 'value') else sub.status,
                "start_date": sub.current_period_start.isoformat(),
                "end_date": sub.current_period_end.isoformat(),
                "created_at": sub.created_at.isoformat()
            })
        
        return result
    
    @staticmethod
    def check_and_expire_subscriptions(db: Session) -> int:
        """Check and expire subscriptions that have ended"""
        now = datetime.utcnow()
        
        expired_subs = db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.current_period_end < now
        ).all()
        
        count = 0
        for sub in expired_subs:
            sub.status = SubscriptionStatus.EXPIRED
            
            # Update user status
            user = db.query(User).filter(User.id == sub.user_id).first()
            if user:
                # Check if user has any other active subscription
                other_active = db.query(Subscription).filter(
                    Subscription.user_id == user.id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.id != sub.id
                ).first()
                
                if not other_active:
                    user.subscription_status = UserStatus.FREE
            
            count += 1
        
        if count > 0:
            db.commit()
        
        return count
    
    @staticmethod
    def cancel_subscription(db: Session, user_id: str) -> bool:
        """Cancel subscription (at end of period)"""
        subscription = SubscriptionService.get_current_subscription(db, user_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        subscription.cancel_at_period_end = True
        subscription.canceled_at = datetime.utcnow()
        db.commit()
        
        return True
    
    @staticmethod
    def get_subscription_plan_info(db: Session, user_id: str) -> Dict[str, Any]:
        """Get subscription plan info for a user"""
        # ✅ GUARD - Skip if user_id is empty or invalid
        if not user_id or user_id == "{}" or user_id == "null" or user_id == "undefined":
            return {
                "status": "free",
                "plan": None,
                "features": settings.FREE_TIER
            }
        
        try:
            user_uuid = SubscriptionService._ensure_uuid(user_id)
        except HTTPException:
            return {
                "status": "free",
                "plan": None,
                "features": settings.FREE_TIER
            }
        
        subscription = SubscriptionService.get_current_subscription(db, user_uuid)
        
        if not subscription:
            return {
                "status": "free",
                "plan": None,
                "features": settings.FREE_TIER
            }
        
        # Get plan features
        if subscription.plan_type in settings.PLANS:
            features = settings.PREMIUM_TIER
        else:
            features = settings.FREE_TIER
        
        # Calculate days remaining
        now = datetime.utcnow()
        days_remaining = (subscription.current_period_end - now).days
        
        return {
            "status": "premium",
            "plan": {
                "type": subscription.plan_type,
                "name": subscription.plan_name,
                "amount": subscription.amount
            },
            "features": features,
            "start_date": subscription.current_period_start.isoformat(),
            "end_date": subscription.current_period_end.isoformat(),
            "days_remaining": max(0, days_remaining),
            "cancel_at_period_end": subscription.cancel_at_period_end
        }