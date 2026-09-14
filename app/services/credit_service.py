from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.models.user import User
from app.config import settings


class CreditService:
    """Service for managing user credits"""

    # ============================================================
    # BALANCE
    # ============================================================
    @staticmethod
    def get_balance(db: Session, user_id: str) -> Dict[str, Any]:
        """Get current credit balance for a user"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Auto-reset expired credits
        CreditService._check_and_reset_expired(db, user)

        return {
            "credits_remaining": user.credits_remaining,
            "plan_type": user.plan_type,
            "credits_reset_at": user.credits_reset_at.isoformat() if user.credits_reset_at else None,
            "has_unlimited": user.has_unlimited_credits,
        }

    # ============================================================
    # SPEND
    # ============================================================
    @staticmethod
    def spend_credits(
        db: Session,
        user_id: str,
        amount: int,
        action: str,
    ) -> Dict[str, Any]:
        """
        Deduct credits from a user.
        Returns the new balance.
        Raises HTTPException if insufficient credits.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Auto-reset expired credits
        CreditService._check_and_reset_expired(db, user)

        # Unlimited credits
        if user.has_unlimited_credits:
            return {
                "success": True,
                "credits_remaining": -1,
                "action": action,
                "unlimited": True,
            }

        # Insufficient credits
        if user.credits_remaining < amount:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits. Need {amount}, have {user.credits_remaining}.",
            )

        # Deduct
        user.credits_remaining -= amount
        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "credits_remaining": user.credits_remaining,
            "action": action,
            "unlimited": False,
        }

    # ============================================================
    # GRANT (on payment success)
    # ============================================================
    @staticmethod
    def grant_credits(
        db: Session,
        user_id: str,
        plan_type: str,
    ) -> Dict[str, Any]:
        """
        Grant credits to a user after successful payment.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        plan = settings.PLANS.get(plan_type)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid plan: {plan_type}"
            )

        credits = plan["credits"]
        duration_days = plan["duration_days"]

        # Set plan and credits
        user.plan_type = plan_type
        user.credits_remaining = credits
        user.credits_reset_at = datetime.utcnow() + timedelta(days=duration_days)

        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "plan_type": plan_type,
            "credits_remaining": credits,
            "credits_reset_at": user.credits_reset_at.isoformat(),
        }

    # ============================================================
    # INTERNAL: RESET EXPIRED
    # ============================================================
    @staticmethod
    def _check_and_reset_expired(db: Session, user: User) -> None:
        """Reset credits if the plan has expired"""
        if not user.credits_reset_at:
            return

        if datetime.utcnow() < user.credits_reset_at:
            return

        # Expired — reset
        user.credits_remaining = 0
        user.plan_type = None
        user.credits_reset_at = None
        db.commit()
        db.refresh(user)

    # ============================================================
    # CAN AFFORD
    # ============================================================
    @staticmethod
    def can_afford(db: Session, user_id: str, amount: int) -> bool:
        """Check if user can afford an action"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        CreditService._check_and_reset_expired(db, user)

        if user.has_unlimited_credits:
            return True

        return user.credits_remaining >= amount