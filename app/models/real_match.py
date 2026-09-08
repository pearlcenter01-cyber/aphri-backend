from sqlalchemy import Column, String, Float, DateTime, ForeignKey, UniqueConstraint
from app.database import Base
import uuid
from datetime import datetime

class RealMatch(Base):
    __tablename__ = "real_matches"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()).replace('-', ''))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    matched_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    final_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'matched_user_id', name='unique_real_match'),
    )