from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.utils.constants import MatchStatus
import uuid

class Match(Base):
    __tablename__ = "matches"
    
    # ============================================================
    # PRIMARY KEY
    # ============================================================
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # ============================================================
    # FOREIGN KEYS
    # ============================================================
    user_1_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    user_2_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # ============================================================
    # MATCH DATA
    # ============================================================
    status = Column(Enum(MatchStatus), default=MatchStatus.MATCHED)
    is_active = Column(Boolean, default=True)
    
    # ============================================================
    # USER ACTIONS
    # ============================================================
    user_1_swiped_at = Column(DateTime, nullable=False)
    user_2_swiped_at = Column(DateTime, nullable=False)
    matched_at = Column(DateTime, default=func.now(), nullable=False)
    
    chat_unlocked_at = Column(DateTime, nullable=True)
    
    # ============================================================
    # CHAT CREDIT TRACKING
    # ============================================================
    chat_charge_paid_by_user_1 = Column(Boolean, default=False, nullable=False)
    chat_charge_paid_by_user_2 = Column(Boolean, default=False, nullable=False)
    
    # ============================================================
    # MESSAGE STATS
    # ============================================================
    last_message_at = Column(DateTime, nullable=True)
    last_message_preview = Column(String(200), nullable=True)
    message_count = Column(Integer, default=0)
    
    # ============================================================
    # TIMESTAMPS
    # ============================================================
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # ============================================================
    # RELATIONSHIPS
    # ============================================================
    user_1 = relationship("User", foreign_keys=[user_1_id], back_populates="matches_as_user1")
    user_2 = relationship("User", foreign_keys=[user_2_id], back_populates="matches_as_user2")
    
    messages = relationship("Message", back_populates="match", cascade="all, delete-orphan")
    
    # ============================================================
    # INDEXES
    # ============================================================
    __table_args__ = (
        Index("ix_matches_user_1_id", "user_1_id"),
        Index("ix_matches_user_2_id", "user_2_id"),
        Index("ix_matches_status", "status"),
        Index("ix_matches_is_active", "is_active"),
        Index("ix_matches_matched_at", "matched_at"),
        Index("ix_matches_unique_users", "user_1_id", "user_2_id", unique=True),
    )
    
    def __repr__(self):
        return f"<Match {self.user_1_id} - {self.user_2_id} ({self.status})>"
    
    def get_other_user_id(self, user_id):
        if self.user_1_id == user_id:
            return self.user_2_id
        elif self.user_2_id == user_id:
            return self.user_1_id
        return None
    
    @property
    def is_chat_unlocked(self):
        if self.chat_unlocked_at:
            from datetime import datetime
            return datetime.now() >= self.chat_unlocked_at
        return False