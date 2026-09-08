from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
from uuid import UUID

from app.models.user import User
from app.models.report import Report
from app.models.block import Block
from app.utils.constants import ReportReason

class ReportService:
    """Service for user reports and blocks"""
    
    @staticmethod
    def _ensure_uuid(value: str | UUID) -> UUID:
        """Convert string to UUID if needed, or return UUID as-is"""
        if isinstance(value, UUID):
            return value
        try:
            return UUID(value)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid UUID format: {value}"
            )
    
    @staticmethod
    def create_report(
        db: Session,
        reporter_id: str | UUID,
        reported_id: str | UUID,
        reason: str,
        description: Optional[str] = None
    ) -> Report:
        """Create a report against a user"""
        try:
            reporter_uuid = ReportService._ensure_uuid(reporter_id)
            reported_uuid = ReportService._ensure_uuid(reported_id)
        except HTTPException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ID format: {e.detail}"
            )
        
        if reporter_uuid == reported_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot report yourself"
            )
        
        # Check if reporter exists
        reporter = db.query(User).filter(User.id == reporter_uuid).first()
        if not reporter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reporter not found"
            )
        
        # Check if reported exists
        reported = db.query(User).filter(User.id == reported_uuid).first()
        if not reported:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reported user not found"
            )
        
        # Check if already reported (prevent duplicate)
        existing_report = db.query(Report).filter(
            Report.reporter_id == reporter_uuid,
            Report.reported_id == reported_uuid,
            Report.status == "pending"
        ).first()
        
        if existing_report:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reported this user"
            )
        
        # Create report
        report = Report(
            reporter_id=reporter_uuid,
            reported_id=reported_uuid,
            reason=reason,
            description=description,
            status="pending"
        )
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        return report
    
    @staticmethod
    def block_user(db: Session, blocker_id: str | UUID, blocked_id: str | UUID) -> bool:
        """Block a user"""
        try:
            blocker_uuid = ReportService._ensure_uuid(blocker_id)
            blocked_uuid = ReportService._ensure_uuid(blocked_id)
        except HTTPException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ID format: {e.detail}"
            )
        
        if blocker_uuid == blocked_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot block yourself"
            )
        
        # Check if already blocked
        existing_block = db.query(Block).filter(
            Block.blocker_id == blocker_uuid,
            Block.blocked_id == blocked_uuid
        ).first()
        
        if existing_block:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already blocked"
            )
        
        # Create block
        block = Block(
            blocker_id=blocker_uuid,
            blocked_id=blocked_uuid
        )
        
        db.add(block)
        
        # Also deactivate any active matches between these users
        from app.models.match import Match
        from app.utils.constants import MatchStatus
        
        matches = db.query(Match).filter(
            (
                (Match.user_1_id == blocker_uuid) & (Match.user_2_id == blocked_uuid)
            ) | (
                (Match.user_1_id == blocked_uuid) & (Match.user_2_id == blocker_uuid)
            ),
            Match.is_active == True
        ).all()
        
        for match in matches:
            match.is_active = False
            match.status = MatchStatus.BLOCKED
        
        db.commit()
        
        return True
    
    @staticmethod
    def unblock_user(db: Session, blocker_id: str | UUID, blocked_id: str | UUID) -> bool:
        """Unblock a user"""
        try:
            blocker_uuid = ReportService._ensure_uuid(blocker_id)
            blocked_uuid = ReportService._ensure_uuid(blocked_id)
        except HTTPException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ID format: {e.detail}"
            )
        
        block = db.query(Block).filter(
            Block.blocker_id == blocker_uuid,
            Block.blocked_id == blocked_uuid
        ).first()
        
        if not block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Block not found"
            )
        
        db.delete(block)
        db.commit()
        
        return True
    
    @staticmethod
    def is_blocked(db: Session, user_id: str | UUID, target_id: str | UUID) -> bool:
        """Check if user_id is blocked by target_id"""
        try:
            user_uuid = ReportService._ensure_uuid(user_id)
            target_uuid = ReportService._ensure_uuid(target_id)
        except HTTPException:
            return False
        
        block = db.query(Block).filter(
            Block.blocker_id == target_uuid,
            Block.blocked_id == user_uuid
        ).first()
        
        return block is not None
    
    @staticmethod
    def get_blocked_users(db: Session, user_id: str | UUID) -> List[str]:
        """Get list of user IDs that a user has blocked"""
        try:
            user_uuid = ReportService._ensure_uuid(user_id)
        except HTTPException:
            return []
        
        blocks = db.query(Block).filter(Block.blocker_id == user_uuid).all()
        return [str(b.blocked_id) for b in blocks]
    
    @staticmethod
    def get_users_who_blocked(db: Session, user_id: str | UUID) -> List[str]:
        """Get list of user IDs who have blocked a user"""
        try:
            user_uuid = ReportService._ensure_uuid(user_id)
        except HTTPException:
            return []
        
        blocks = db.query(Block).filter(Block.blocked_id == user_uuid).all()
        return [str(b.blocker_id) for b in blocks]
    
    @staticmethod
    def get_reports_by_user(db: Session, user_id: str | UUID) -> List[Dict[str, Any]]:
        """Get all reports filed by a user"""
        try:
            user_uuid = ReportService._ensure_uuid(user_id)
        except HTTPException:
            return []
        
        reports = db.query(Report).filter(
            Report.reporter_id == user_uuid
        ).order_by(Report.created_at.desc()).all()
        
        result = []
        for report in reports:
            reported_user = db.query(User).filter(User.id == report.reported_id).first()
            result.append({
                "id": str(report.id),
                "reported_user": {
                    "id": str(reported_user.id) if reported_user else None,
                    "name": f"{reported_user.first_name} {reported_user.last_name}" if reported_user else None
                } if reported_user else None,
                "reason": report.reason.value if hasattr(report.reason, 'value') else report.reason,
                "description": report.description,
                "status": report.status,
                "created_at": report.created_at.isoformat()
            })
        
        return result
    
    @staticmethod
    def get_reports_against_user(db: Session, user_id: str | UUID) -> List[Dict[str, Any]]:
        """Get all reports filed against a user"""
        try:
            user_uuid = ReportService._ensure_uuid(user_id)
        except HTTPException:
            return []
        
        reports = db.query(Report).filter(
            Report.reported_id == user_uuid
        ).order_by(Report.created_at.desc()).all()
        
        result = []
        for report in reports:
            reporter = db.query(User).filter(User.id == report.reporter_id).first()
            result.append({
                "id": str(report.id),
                "reporter": {
                    "id": str(reporter.id) if reporter else None,
                    "name": f"{reporter.first_name} {reporter.last_name}" if reporter else None
                } if reporter else None,
                "reason": report.reason.value if hasattr(report.reason, 'value') else report.reason,
                "description": report.description,
                "status": report.status,
                "created_at": report.created_at.isoformat()
            })
        
        return result