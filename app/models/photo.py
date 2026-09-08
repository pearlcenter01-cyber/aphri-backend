from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean
from app.database import UUIDType
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid

class Photo(Base):
    __tablename__ = "photos"
    
    # ============================================================
    # PRIMARY KEY
    # ============================================================
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    
    # ============================================================
    # PHOTO URLS
    # ============================================================
    url_original = Column(String(512), nullable=False)
    url_thumbnail = Column(String(512), nullable=True)  # 200x200
    url_medium = Column(String(512), nullable=True)     # 600x600
    url_large = Column(String(512), nullable=True)      # 1200x1200
    
    # ============================================================
    # PHOTO METADATA
    # ============================================================
    s3_key = Column(String(255), nullable=True)  # S3 storage key
    file_size = Column(Integer, nullable=True)  # In bytes
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    # ============================================================
    # ORDERING & STATUS
    # ============================================================
    order = Column(Integer, default=0)  # Display order on profile
    is_primary = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)  # Photo verification
    
    # ============================================================
    # TIMESTAMPS
    # ============================================================
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # ============================================================
    # RELATIONSHIPS
    # ============================================================
    user = relationship("User", back_populates="photos")
    
    def __repr__(self):
        return f"<Photo user_id={self.user_id} primary={self.is_primary}>"