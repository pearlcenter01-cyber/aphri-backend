from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, Integer, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.utils.constants import MessageType
import uuid

class Message(Base):
    __tablename__ = "messages"
    
    # ============================================================
    # PRIMARY KEY
    # ============================================================
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # ============================================================
    # FOREIGN KEYS
    # ============================================================
    match_id = Column(String(36), ForeignKey("matches.id"), nullable=False)
    sender_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    receiver_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # ============================================================
    # MESSAGE DATA
    # ============================================================
    message_type = Column(String(20), default=MessageType.TEXT)
    content = Column(Text, nullable=True)  # For text messages
    media_url = Column(String(512), nullable=True)  # For photo/video
    media_thumbnail = Column(String(512), nullable=True)  # Thumbnail for media
    session_id = Column(String(36), nullable=True)  # ✅ ADD THIS - for compatibility requests
    
    # ============================================================
    # STATUS
    # ============================================================
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    is_delivered = Column(Boolean, default=False)
    delivered_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False)
    
    # ============================================================
    # TIMESTAMPS
    # ============================================================
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # ============================================================
    # RELATIONSHIPS
    # ============================================================
    match = relationship("Match", foreign_keys=[match_id])
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
    
    # ============================================================
    # INDEXES
    # ============================================================
    __table_args__ = (
        Index("ix_messages_match_id", "match_id"),
        Index("ix_messages_sender_id", "sender_id"),
        Index("ix_messages_receiver_id", "receiver_id"),
        Index("ix_messages_created_at", "created_at"),
        Index("ix_messages_is_read", "is_read"),
        Index("ix_messages_match_created", "match_id", "created_at"),
    )
    
    def __repr__(self):
        return f"<Message {self.id} from {self.sender_id}>"