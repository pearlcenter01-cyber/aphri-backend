from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from app.database import Base
from datetime import datetime

class ChatQuestion(Base):
    __tablename__ = "chat_questions"
    
    id = Column(String, primary_key=True)
    match_id = Column(String, ForeignKey("matches.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)       # Who asked
    candidate_id = Column(String, ForeignKey("users.id"), nullable=False)  # Who answered
    question_index = Column(Integer, nullable=False)  # 0, 1, 2
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5
    is_answered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    answered_at = Column(DateTime, nullable=True)
    rated_at = Column(DateTime, nullable=True)