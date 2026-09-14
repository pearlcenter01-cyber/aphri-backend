from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Index
from app.database import Base, UUIDType
import uuid
from datetime import datetime

class Answer(Base):
    __tablename__ = "answers"
    
    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(String, nullable=False)
    answer = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_answer_user_question', 'user_id', 'question_id'),
    )