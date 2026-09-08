from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.database import Base
import uuid
from datetime import datetime

class Answer(Base):
    __tablename__ = "answers"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(String, nullable=False)
    answer = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_answer_user_question', 'user_id', 'question_id'),
    )