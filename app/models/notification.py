from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.utils.constants import NotificationType
import uuid

class Notification(Base):
    __tablename__ = "notifications"
    
    # ============================================================
    # PRIMARY KEY
    # ============================================================
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # ============================================================
    # NOTIFICATION DATA
    # ============================================================
    notification_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    
    # ============================================================
    # TARGET
    # ============================================================
    target_id = Column(UUID(as_uuid=True), nullable=True)  # e.g., match_id, message_id
    target_type = Column(String(50), nullable=True)  # match, message, etc.
    
    # ============================================================
    # STATUS
    # ============================================================
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    is_delivered = Column(Boolean, default=False)
    delivered_at = Column(DateTime, nullable=True)
    
    # ============================================================
    # DATA PAYLOAD
    # ============================================================
    data_payload = Column(Text, nullable=True)  # JSON with extra data
    
    # ============================================================
    # TIMESTAMPS
    # ============================================================
    created_at = Column(DateTime, default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    
    # ============================================================
    # RELATIONSHIPS
    # ============================================================
    user = relationship("User", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification {self.user_id} - {self.notification_type}>"