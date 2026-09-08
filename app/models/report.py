from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.utils.constants import ReportReason
import uuid

class Report(Base):
    __tablename__ = "reports"
    
    # ============================================================
    # PRIMARY KEY
    # ============================================================
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ============================================================
    # FOREIGN KEYS
    # ============================================================
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reported_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # ============================================================
    # REPORT DATA
    # ============================================================
    reason = Column(Enum(ReportReason), nullable=False)
    description = Column(Text, nullable=True)
    
    # ============================================================
    # STATUS
    # ============================================================
    status = Column(String(20), default="pending")  # pending, reviewed, dismissed, action_taken
    admin_notes = Column(Text, nullable=True)
    
    # ============================================================
    # TIMESTAMPS
    # ============================================================
    created_at = Column(DateTime, default=func.now(), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # ============================================================
    # RELATIONSHIPS
    # ============================================================
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="reports_made")
    reported = relationship("User", foreign_keys=[reported_id], back_populates="reports_received")
    
    def __repr__(self):
        return f"<Report {self.reporter_id} -> {self.reported_id} ({self.reason})>"