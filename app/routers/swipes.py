from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from app.database import get_db
from app.services.auth_service import AuthService
from app.services.swipe_service import SwipeService
from app.services.match_service import MatchService
from app.models.user import User
from app.schemas.swipe import SwipeRequest, SwipeResponse
from app.dependencies import get_current_user

router = APIRouter()

# ============================================================
# SWIPE ENDPOINTS
# ============================================================

@router.get("/candidates")
async def get_candidates(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get candidates based on user type:
    - Serious users: get 50%+ compatibility matches
    - Casual users: get all active casual users
    """
    return SwipeService.get_candidates(db, current_user.id, limit)


@router.get("/matches")
async def get_matches(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get all serious matches (50%+ compatibility)
    Only for serious relationship users
    """
    if current_user.looking_for != "Serious Relationship":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only for serious relationship users"
        )
    return SwipeService.get_matches(db, current_user.id, limit)


@router.post("", response_model=SwipeResponse)
async def create_swipe(
    swipe_data: SwipeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a swipe (like or pass)
    
    - **target_user_id**: User to swipe on
    - **direction**: "like" or "pass"
    """
    return SwipeService.create_swipe(
        db,
        current_user.id,
        swipe_data.target_user_id,
        swipe_data.direction
    )


@router.get("/history")
async def get_swipe_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get swipe history
    """
    return SwipeService.get_swipe_history(db, current_user.id, limit)


@router.get("/daily-count")
async def get_daily_swipe_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get daily swipe count and remaining swipes
    """
    daily_count = SwipeService.get_daily_swipe_count(db, current_user.id)
    can_swipe = SwipeService.can_swipe(db, current_user.id)
    
    max_swipes = 10  # Free tier limit
    
    return {
        "daily_swipes": daily_count,
        "max_swipes": max_swipes if current_user.subscription_status.value == "free" else "unlimited",
        "remaining": max_swipes - daily_count if current_user.subscription_status.value == "free" else "unlimited",
        "can_swipe": can_swipe
    }


# ============================================================
# 🆕 MATCH APPROVAL ENDPOINTS
# ============================================================

@router.post("/matches/{match_id}/approve")
async def approve_match(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Approve a match - unlocks chat when both users approve
    """
    result = MatchService.approve_match(db, match_id, current_user.id)
    return result


@router.get("/matches/{match_id}/chat-status")
async def get_chat_status(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Check if chat is unlocked for a match
    """
    result = MatchService.get_match_with_chat_status(db, match_id, current_user.id)
    return result


@router.get("/matches/count")
async def get_match_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get total match count for the current user
    """
    count = MatchService.get_match_count(db, current_user.id)
    return {"count": count}