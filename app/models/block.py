from sqlalchemy import Column, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid

class Block(Base):
    __tablename__ = "blocks"
    
    # ============================================================
    # PRIMARY KEY
    # ============================================================
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ============================================================
    # FOREIGN KEYS
    # ============================================================
    blocker_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    blocked_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # ============================================================
    # TIMESTAMPS
    # ============================================================
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # ============================================================
    # RELATIONSHIPS
    # ============================================================
    blocker = relationship("User", foreign_keys=[blocker_id], back_populates="blocks_made")
    blocked = relationship("User", foreign_keys=[blocked_id], back_populates="blocks_received")
    
    # ============================================================
    # INDEXES
    # ============================================================
    __table_args__ = (
        Index("ix_blocks_blocker_id", "blocker_id"),
        Index("ix_blocks_blocked_id", "blocked_id"),
        Index("ix_blocks_unique", "blocker_id", "blocked_id", unique=True),
    )
    
    def __repr__(self):
        return f"<Block {self.blocker_id} blocked {self.blocked_id}>"