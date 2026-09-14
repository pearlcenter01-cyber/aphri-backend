from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.credit_service import CreditService

router = APIRouter()


@router.get("/balance")
async def get_credit_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get the current user's credit balance"""
    return CreditService.get_balance(db, current_user.id)