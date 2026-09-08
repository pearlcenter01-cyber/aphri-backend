from sqlalchemy import Column, String, Integer, Boolean, Float, DateTime, ForeignKey
from app.database import Base
import uuid
from datetime import datetime

class MatchQuestionGame(Base):
    __tablename__ = "match_question_game"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()).replace('-', ''))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    candidate_id = Column(String, ForeignKey("users.id"), nullable=False)
    question_index = Column(Integer, default=0)
    custom_question = Column(String, nullable=True)
    candidate_answer = Column(String, nullable=True)
    rating = Column(Integer, nullable=True)
    is_complete = Column(Boolean, default=False)
    final_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)