from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, Boolean
from app.database import UUIDType
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid

class Profile(Base):
    __tablename__ = "profiles"
    
    # ============================================================
    # PRIMARY KEY
    # ============================================================
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUIDType, ForeignKey("users.id"), unique=True, nullable=False)
    
    # ============================================================
    # BIO & DESCRIPTION
    # ============================================================
    bio = Column(Text, nullable=True)  # Short bio/description
    about_me = Column(Text, nullable=True)  # Longer description
    headline = Column(String(100), nullable=True)  # e.g., "Adventure seeker"
    favorite_quote = Column(Text, nullable=True)
    # ============================================================
    # INTERESTS & PREFERENCES
    # ============================================================
    interests = Column(Text, nullable=True)  # JSON array or comma-separated
    looking_for = Column(String(50), nullable=True)  # Relationship type
    
    # ============================================================
    # QUESTIONS & PROMPTS
    # ============================================================
    prompt_1 = Column(String(200), nullable=True)
    prompt_1_answer = Column(Text, nullable=True)
    prompt_2 = Column(String(200), nullable=True)
    prompt_2_answer = Column(Text, nullable=True)
    prompt_3 = Column(String(200), nullable=True)
    prompt_3_answer = Column(Text, nullable=True)
    
    # ============================================================
    # BASIC INFO
    # ============================================================
    height = Column(Integer, nullable=True)  # In cm
    education = Column(String(100), nullable=True)
    occupation = Column(String(100), nullable=True)
    company = Column(String(100), nullable=True)
    hometown = Column(String(100), nullable=True)
    
    # ============================================================
    # LIFESTYLE
    # ============================================================
    smoking = Column(String(20), nullable=True)  # never, occasionally, regularly
    drinking = Column(String(20), nullable=True)  # never, occasionally, regularly
    religion = Column(String(50), nullable=True)
    zodiac = Column(String(20), nullable=True)
    
    # ============================================================
    # VERIFICATION
    # ============================================================
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)
    
    # ============================================================
    # COMPLETENESS SCORE
    # ============================================================
    completeness_score = Column(Integer, default=0)  # 0-100
    
    # ============================================================
    # TIMESTAMPS
    # ============================================================
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # ============================================================
    # RELATIONSHIPS
    # ============================================================
    user = relationship("User", back_populates="profile")
    
    def __repr__(self):
        return f"<Profile user_id={self.user_id}>"