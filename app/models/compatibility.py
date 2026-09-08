from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref
from datetime import datetime
from app.database import Base
import uuid

class CompatibilitySession(Base):
    __tablename__ = "compatibility_sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    partner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")  # pending, both_agreed, answering, analyzing, complete, declined
    request_sent_at = Column(DateTime, default=datetime.utcnow)
    agreed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    report = Column(JSON, nullable=True)
    score = Column(Float, nullable=True)
    
    # Relationships - simpler approach
    user = relationship("User", foreign_keys=[user_id])
    partner = relationship("User", foreign_keys=[partner_id])

class CompatibilityQuestion(Base):
    __tablename__ = "compatibility_questions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("compatibility_sessions.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    options = Column(Text, nullable=True)  # ✅ ADD THIS - JSON string of options
    category = Column(String(50))  # gottman, attachment, big_five
    question_index = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("CompatibilitySession", backref="questions")

class CompatibilityResponse(Base):
    __tablename__ = "compatibility_responses"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("compatibility_sessions.id"), nullable=False)
    question_id = Column(String(36), ForeignKey("compatibility_questions.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    response_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    analyzed = Column(Boolean, default=False)
    
    # Relationships
    session = relationship("CompatibilitySession", backref="responses")
    question = relationship("CompatibilityQuestion", backref="responses")