from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.database import get_db
from app.config import settings
from app.dependencies_admin import require_admin
from app.services.admin_service import AdminService

router = APIRouter(tags=["Admin"])
_bearer = HTTPBearer(auto_error=False)


# ============================================================
# LOGIN
# ============================================================
@router.post("/login")
async def admin_login(request: Dict[str, Any]):
    password = request.get("password")
    if not password:
        raise HTTPException(status_code=400, detail="password is required")
    if password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")

    payload = {
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(hours=settings.ADMIN_JWT_EXPIRE_HOURS),
    }
    token = jwt.encode(payload, settings.ADMIN_JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}


# ============================================================
# STATS
# ============================================================
@router.get("/stats")
async def stats(
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    return AdminService.get_stats(db)


# ============================================================
# USERS
# ============================================================
@router.get("/users")
async def list_users(
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    return AdminService.list_users(db, search=search, limit=limit, offset=offset)


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    return AdminService.get_user_detail(db, user_id)


@router.put("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    return AdminService.set_user_active(db, user_id, False)


@router.put("/users/{user_id}/unban")
async def unban_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    return AdminService.set_user_active(db, user_id, True)


@router.put("/users/{user_id}/credits")
async def adjust_credits(
    user_id: str,
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    delta = request.get("delta")
    if delta is None or not isinstance(delta, int):
        raise HTTPException(status_code=400, detail="delta (integer) is required")
    return AdminService.adjust_credits(db, user_id, delta)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    return AdminService.delete_user(db, user_id)

# ============================================================
# REPORTS
# ============================================================
@router.get("/reports")
async def list_reports(
    status_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    return AdminService.list_reports(db, status_filter=status_filter, limit=limit, offset=offset)


@router.put("/reports/{report_id}/action")
async def action_report(
    report_id: str,
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    action = request.get("action")
    if action not in ("dismiss", "warn", "ban"):
        raise HTTPException(status_code=400, detail="action must be dismiss | warn | ban")
    return AdminService.action_report(db, report_id, action)


# ============================================================
# BLOCKS
# ============================================================
@router.get("/blocks")
async def list_blocks(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    return AdminService.list_blocks(db, limit=limit)


# ============================================================
# MATCHES
# ============================================================
@router.get("/matches")
async def list_matches(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    return AdminService.list_real_matches(db, limit=limit)


@router.delete("/matches/{match_id}")
async def force_unmatch(
    match_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    return AdminService.force_unmatch(db, match_id)


# ============================================================
# MODERATION
# ============================================================
@router.get("/moderation")
async def list_moderation(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    return AdminService.list_moderation(db, limit=limit)


# ============================================================
# AUDIT
# ============================================================
@router.get("/audit")
async def list_audit(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    return AdminService.list_audit(db, limit=limit)