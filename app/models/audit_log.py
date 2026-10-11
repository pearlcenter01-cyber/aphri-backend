from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base
import uuid


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action = Column(String(64), nullable=False)          # e.g. "ban_user", "unban_user"
    target_type = Column(String(32), nullable=True)      # e.g. "user", "report", "match"
    target_id = Column(String(36), nullable=True)
    details = Column(Text, nullable=True)                # JSON string
    created_at = Column(DateTime, default=func.now(), nullable=False)

    def __repr__(self):
        return f"<AdminAuditLog {self.action} {self.target_type}:{self.target_id}>"