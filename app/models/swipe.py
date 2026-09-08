from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.utils.constants import MatchStatus
import uuid

class Swipe(Base):
    __tablename__ = "swipes"
    
    # ============================================================
    # PRIMARY KEY
    # ============================================================
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # ============================================================
    # FOREIGN KEYS
    # ============================================================
    swiper_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    swiped_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # ============================================================
    # SWIPE DATA
    # ============================================================
    direction = Column(String(10), nullable=False)  # 'like' or 'pass'
    status = Column(String(20), default="pending")  # pending, matched, rejected
    
    # ============================================================
    # TIMESTAMPS
    # ============================================================
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # ============================================================
    # RELATIONSHIPS
    # ============================================================
    swiper = relationship("User", foreign_keys=[swiper_id], back_populates="swipes_made")
    swiped = relationship("User", foreign_keys=[swiped_id], back_populates="swipes_received")
    
    # ============================================================
    # INDEXES
    # ============================================================
    __table_args__ = (
        Index("ix_swipes_swiper_swiped", "swiper_id", "swiped_id"),
        Index("ix_swipes_swiper_id", "swiper_id"),
        Index("ix_swipes_swiped_id", "swiped_id"),
        Index("ix_swipes_created_at", "created_at"),
    )
    
    def __repr__(self):
        return f"<Swipe {self.swiper_id} -> {self.swiped_id} ({self.direction})>"