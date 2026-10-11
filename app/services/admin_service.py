import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, func
from fastapi import HTTPException, status

from app.models.user import User
from app.models.match import Match
from app.models.report import Report
from app.models.block import Block
from app.models.real_match import RealMatch
from app.models.audit_log import AdminAuditLog
from app.models.moderation_log import ModerationLog


class AdminService:

    # ============================================================
    # AUDIT LOG
    # ============================================================
    @staticmethod
    def log_action(
        db: Session,
        action: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = AdminAuditLog(
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            details=json.dumps(details) if details else None,
        )
        db.add(entry)
        db.commit()

    # ============================================================
    # STATS
    # ============================================================
    @staticmethod
    def get_stats(db: Session) -> Dict[str, int]:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        total_matches = db.query(Match).count()
        active_matches = db.query(Match).filter(Match.is_active == True).count()
        real_matches = db.query(RealMatch).count()
        pending_reports = db.query(Report).filter(Report.status == "pending").count()
        total_blocks = db.query(Block).count()
        nsfw_rejections = db.query(ModerationLog).filter(
            ModerationLog.kind == "photo_nsfw"
        ).count()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_matches": total_matches,
            "active_matches": active_matches,
            "real_matches": real_matches,
            "pending_reports": pending_reports,
            "total_blocks": total_blocks,
            "nsfw_rejections": nsfw_rejections,
        }

    # ============================================================
    # USERS
    # ============================================================
    @staticmethod
    def list_users(
        db: Session,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        query = db.query(User)
        if search:
            term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(User.email).like(term),
                    func.lower(User.first_name).like(term),
                    func.lower(User.last_name).like(term),
                )
            )
        users = query.order_by(desc(User.created_at)).offset(offset).limit(limit).all()
        return [AdminService._user_summary(u) for u in users]

    @staticmethod
    def _user_summary(u: User) -> Dict[str, Any]:
        return {
            "id": str(u.id),
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "gender": u.gender,
            "is_active": u.is_active,
            "is_online": getattr(u, "is_online", False),
            "subscription_status": getattr(u.subscription_status, "value", str(u.subscription_status)),
            "credits_remaining": u.credits_remaining,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }

    @staticmethod
    def get_user_detail(db: Session, user_id: str) -> Dict[str, Any]:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")
        d = AdminService._user_summary(u)
        d["last_active_at"] = u.last_active_at.isoformat() if getattr(u, "last_active_at", None) else None
        d["looking_for"] = getattr(u, "looking_for", None)
        d["religion"] = getattr(u, "religion", None)
        d["city"] = getattr(u, "city", None)
        d["bio"] = None
        return d

    @staticmethod
    def set_user_active(db: Session, user_id: str, active: bool) -> Dict[str, Any]:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")
        u.is_active = active
        db.commit()
        AdminService.log_action(
            db,
            action="unban_user" if active else "ban_user",
            target_type="user",
            target_id=user_id,
        )
        return AdminService._user_summary(u)

    @staticmethod
    def adjust_credits(db: Session, user_id: str, delta: int) -> Dict[str, Any]:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")
        current = u.credits_remaining or 0
        new_val = current + delta
        if new_val < 0:
            raise HTTPException(status_code=400, detail="Credits cannot go below 0")
        u.credits_remaining = new_val
        db.commit()
        AdminService.log_action(
            db,
            action="adjust_credits",
            target_type="user",
            target_id=user_id,
            details={"delta": delta, "from": current, "to": new_val},
        )
        return AdminService._user_summary(u)

    # ============================================================
    # REPORTS
    # ============================================================
    @staticmethod
    def list_reports(
        db: Session,
        status_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        q = db.query(Report)
        if status_filter:
            q = q.filter(Report.status == status_filter)
        reports = q.order_by(desc(Report.created_at)).offset(offset).limit(limit).all()
        return [AdminService._report_summary(r, db) for r in reports]

    @staticmethod
    def _report_summary(r: Report, db: Session) -> Dict[str, Any]:
        reporter = db.query(User).filter(User.id == r.reporter_id).first()
        reported = db.query(User).filter(User.id == r.reported_id).first()
        return {
            "id": str(r.id),
            "reporter": {"id": str(reporter.id), "email": reporter.email} if reporter else None,
            "reported": {"id": str(reported.id), "email": reported.email} if reported else None,
            "reason": r.reason.value if hasattr(r.reason, "value") else r.reason,
            "description": r.description,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }

    @staticmethod
    def action_report(db: Session, report_id: str, action: str) -> Dict[str, Any]:
        r = db.query(Report).filter(Report.id == report_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Report not found")

        if action == "dismiss":
            r.status = "dismissed"
        elif action == "warn":
            r.status = "warned"
        elif action == "ban":
            r.status = "actioned"
            target = db.query(User).filter(User.id == r.reported_id).first()
            if target:
                target.is_active = False
        else:
            raise HTTPException(status_code=400, detail="Invalid action")

        db.commit()
        AdminService.log_action(
            db,
            action=f"report_{action}",
            target_type="report",
            target_id=report_id,
            details={"reported_user": str(r.reported_id)},
        )
        return AdminService._report_summary(r, db)

    # ============================================================
    # BLOCKS
    # ============================================================
    @staticmethod
    def list_blocks(db: Session, limit: int = 200) -> List[Dict[str, Any]]:
        rows = db.query(Block).order_by(desc(Block.created_at)).limit(limit).all()
        out = []
        for b in rows:
            blocker = db.query(User).filter(User.id == b.blocker_id).first()
            blocked = db.query(User).filter(User.id == b.blocked_id).first()
            out.append({
                "id": str(b.id),
                "blocker": {"id": str(blocker.id), "email": blocker.email} if blocker else None,
                "blocked": {"id": str(blocked.id), "email": blocked.email} if blocked else None,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            })
        return out

    # ============================================================
    # MATCHES
    # ============================================================
    @staticmethod
    def list_real_matches(db: Session, limit: int = 200) -> List[Dict[str, Any]]:
        rows = db.query(RealMatch).order_by(desc(RealMatch.created_at)).limit(limit).all()
        out = []
        for rm in rows:
            u1 = db.query(User).filter(User.id == rm.user_id).first()
            u2 = db.query(User).filter(User.id == rm.matched_user_id).first()
            out.append({
                "id": str(rm.id),
                "user": {"id": str(u1.id), "email": u1.email} if u1 else None,
                "matched_user": {"id": str(u2.id), "email": u2.email} if u2 else None,
                "final_score": rm.final_score,
                "created_at": rm.created_at.isoformat() if rm.created_at else None,
            })
        return out

    @staticmethod
    def force_unmatch(db: Session, match_id: str) -> Dict[str, Any]:
        m = db.query(Match).filter(Match.id == match_id).first()
        if not m:
            raise HTTPException(status_code=404, detail="Match not found")
        m.is_active = False
        db.commit()
        AdminService.log_action(
            db,
            action="force_unmatch",
            target_type="match",
            target_id=match_id,
        )
        return {"id": match_id, "is_active": False}

    # ============================================================
    # MODERATION
    # ============================================================
    @staticmethod
    def list_moderation(db: Session, limit: int = 200) -> List[Dict[str, Any]]:
        rows = (
            db.query(ModerationLog)
            .order_by(desc(ModerationLog.created_at))
            .limit(limit)
            .all()
        )
        out = []
        for ml in rows:
            u = db.query(User).filter(User.id == ml.user_id).first()
            out.append({
                "id": str(ml.id),
                "user": {"id": str(u.id), "email": u.email} if u else None,
                "kind": ml.kind,
                "details": ml.details,
                "created_at": ml.created_at.isoformat() if ml.created_at else None,
            })
        return out

    # ============================================================
    # AUDIT
    # ============================================================
    @staticmethod
    def list_audit(db: Session, limit: int = 200) -> List[Dict[str, Any]]:
        rows = (
            db.query(AdminAuditLog)
            .order_by(desc(AdminAuditLog.created_at))
            .limit(limit)
            .all()
        )
        return [{
            "id": str(a.id),
            "action": a.action,
            "target_type": a.target_type,
            "target_id": a.target_id,
            "details": a.details,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        } for a in rows]