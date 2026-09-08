from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from app.database import get_db
from app.services.auth_service import AuthService
from app.services.report_service import ReportService
from app.services.user_service import UserService
from app.models.user import User
from app.schemas.report import ReportCreate, BlockCreate
from app.dependencies import get_current_user

router = APIRouter()

# ============================================================
# REPORT ENDPOINTS
# ============================================================

@router.post("/report")
async def create_report(
    report_data: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Report a user
    
    - **reported_user_id**: User being reported
    - **reason**: "spam", "inappropriate", "harassment", "fake_profile", "underage", "offensive", "other"
    - **description**: Optional description
    """
    report = ReportService.create_report(
        db,
        current_user.id,
        report_data.reported_user_id,
        report_data.reason,
        report_data.description
    )
    
    return {
        "id": str(report.id),
        "status": report.status,
        "message": "Report submitted successfully"
    }

@router.post("/block")
async def block_user(
    block_data: BlockCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Block a user
    """
    ReportService.block_user(db, current_user.id, block_data.user_id)
    return {"message": "User blocked successfully"}

@router.delete("/block/{user_id}")
async def unblock_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Unblock a user
    """
    ReportService.unblock_user(db, current_user.id, user_id)
    return {"message": "User unblocked successfully"}

@router.get("/blocked")
async def get_blocked_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get list of blocked users
    """
    blocked_ids = ReportService.get_blocked_users(db, current_user.id)
    
    result = []
    for user_id in blocked_ids:
        user = UserService.get_user_by_id(db, user_id)
        if user:
            result.append({
                "id": str(user.id),
                "first_name": user.first_name,
                "last_name": user.last_name
            })
    
    return result

@router.get("/my-reports")
async def get_my_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get reports I've filed
    """
    return ReportService.get_reports_by_user(db, current_user.id)