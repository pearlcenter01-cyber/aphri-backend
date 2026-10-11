from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base
import uuid


class ModerationLog(Base):
    __tablename__ = "moderation_log"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    kind = Column(String(32), nullable=False)            # e.g. "photo_nsfw"
    details = Column(Text, nullable=True)                # JSON string
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)

    def __repr__(self):
        return f"<ModerationLog {self.kind} user={self.user_id}>"