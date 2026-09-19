from sqlalchemy import Column, String, DateTime, Boolean, Enum, Integer, Text, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base, UUIDType
import uuid


class CasualQuestion(Base):
    """Casual "Who's Ready for Fun?" questions"""
    __tablename__ = "casual_questions"

    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    asker_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)

    question_text = Column(String(255), default="Who's ready for fun today?")
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=False)  # 12 hours from creation

    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    asker = relationship("User", back_populates="casual_questions")
    responses = relationship("CasualResponse", back_populates="question", cascade="all, delete-orphan")


class CasualResponse(Base):
    """Responses to casual questions"""
    __tablename__ = "casual_responses"

    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(UUIDType, ForeignKey("casual_questions.id"), nullable=False)
    responder_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)

    response_type = Column(String(20), nullable=False)  # "payment" or "mutual_fun"
    is_selected = Column(Boolean, default=False)  # Whether asker selected this responder
    is_accepted = Column(Boolean, default=False)  # Whether responder accepted

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    question = relationship("CasualQuestion", back_populates="responses")
    responder = relationship("User", back_populates="casual_responses")


class CasualPayment(Base):
    """Records that a user has paid the casual chat fee for a specific partner.
    One row per (user_id, partner_id) pair. Once a row exists, no further
    charges apply for that pair."""
    __tablename__ = "casual_payments"

    id = Column(UUIDType, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    partner_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    paid_at = Column(DateTime, default=func.now(), nullable=False)    