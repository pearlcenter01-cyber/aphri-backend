from sqlalchemy import Column, String, DateTime, Boolean, Enum, Integer, Text, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.constants import UserStatus
import uuid
from app.models.casual import CasualQuestion, CasualResponse

class User(Base):
    __tablename__ = "users"
    
    # ============================================================
    # PRIMARY KEY
    # ============================================================
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # ============================================================
    # AUTHENTICATION
    # ============================================================
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    
    # ============================================================
    # PERSONAL INFORMATION
    # ============================================================
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(String(20), nullable=True)  # male, female
    
    # ============================================================
    # LOCATION
    # ============================================================
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    location_updated_at = Column(DateTime, nullable=True)
    
    # ============================================================
    # RELATIONSHIP PREFERENCES
    # ============================================================
    looking_for = Column(String(50), nullable=True)  # serious, casual
    looking_for_gender = Column(String(20), nullable=True)  # men, women, everyone
    intimate_type = Column(String(50), nullable=True)  # massage, physical

    vibe = Column(String(50), nullable=True)  # chill, adventurous, romantic, playful
    vibe_subcategories = Column(String(500), nullable=True)  # JSON array stored as string
    
    # Age Range Preference
    looking_for_age_min = Column(Integer, nullable=True)
    looking_for_age_max = Column(Integer, nullable=True)
    
    # ============================================================
    # RELIGION
    # ============================================================
    religion = Column(String(50), nullable=True)
    religion_preferences = Column(Text, nullable=True)  # comma-separated
    
    # ============================================================
    # LIFE STATUS
    # ============================================================
    is_single_parent = Column(Boolean, default=False)
    is_divorced = Column(Boolean, default=False)
    open_to_single_parent = Column(Boolean, default=True)
    open_to_divorced = Column(Boolean, default=True)
    open_to_never_married = Column(Boolean, default=True)
    
    # ============================================================
    # COMPATIBILITY QUESTIONS (8 Questions)
    # ============================================================
    q1_core_need = Column(String(50), nullable=True)
    q2_sex_intimacy = Column(String(50), nullable=True)
    q3_conflict = Column(String(50), nullable=True)
    q4_success_response = Column(String(50), nullable=True)
    q5_gender_roles = Column(String(50), nullable=True)
    q6_religion = Column(String(50), nullable=True)
    q7_crisis_response = Column(String(50), nullable=True)
    q8_emotional_maturity = Column(String(50), nullable=True)
    
    # ============================================================
    # COMPATIBILITY SCORES
    # ============================================================
    compatibility_score_8q = Column(Float, nullable=True)
    compatibility_score_custom = Column(Float, nullable=True)
    compatibility_score_final = Column(Float, nullable=True)
    
    # ============================================================
    # CUSTOM QUESTIONS
    # ============================================================
    custom_questions = Column(Text, nullable=True)  # JSON array
    
    # ============================================================
    # SUBSCRIPTION
    # ============================================================
    subscription_status = Column(Enum(UserStatus), default=UserStatus.FREE, nullable=False)
    chapa_customer_id = Column(String(255), nullable=True)
    
    # ============================================================
    # CREDITS
    # ============================================================
    credits_remaining = Column(Integer, default=0, nullable=False)
    credits_reset_at = Column(DateTime, nullable=True)
    plan_type = Column(String(20), nullable=True)  # 'starter', 'standard', 'premium'
    
    # ============================================================
    # ACCOUNT STATUS
    # ============================================================
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_online = Column(Boolean, default=False)
    last_active_at = Column(DateTime, default=func.now(), onupdate=func.now())
    photo_reveal_date = Column(DateTime, nullable=True)  # 24 hours after registration
    has_rated_custom_answers = Column(Boolean, default=False)  # 🆕 Whether user has rated custom answers
    
    # ============================================================
    # PROFILE FEATURES
    # ============================================================
    quote = Column(Text, nullable=True)
    voice_note_url = Column(String(255), nullable=True)
    has_voice_note = Column(Boolean, default=False)
    has_quote = Column(Boolean, default=False)
    
    # ============================================================
    # TIMESTAMPS
    # ============================================================
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # ============================================================
    # RELATIONSHIPS
    # ============================================================
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    photos = relationship("Photo", back_populates="user", cascade="all, delete-orphan")
    
    swipes_made = relationship("Swipe", foreign_keys="Swipe.swiper_id", back_populates="swiper", cascade="all, delete-orphan")
    swipes_received = relationship("Swipe", foreign_keys="Swipe.swiped_id", back_populates="swiped")
    
    matches_as_user1 = relationship("Match", foreign_keys="Match.user_1_id", back_populates="user_1")
    matches_as_user2 = relationship("Match", foreign_keys="Match.user_2_id", back_populates="user_2")
    
    messages_sent = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    messages_received = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver")
    
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    reports_made = relationship("Report", foreign_keys="Report.reporter_id", back_populates="reporter")
    reports_received = relationship("Report", foreign_keys="Report.reported_id", back_populates="reported")
    blocks_made = relationship("Block", foreign_keys="Block.blocker_id", back_populates="blocker")
    blocks_received = relationship("Block", foreign_keys="Block.blocked_id", back_populates="blocked")  

    # ============================================================
    # CASUAL DATING
    # ============================================================
    casual_questions = relationship("CasualQuestion", back_populates="asker", cascade="all, delete-orphan")
    casual_responses = relationship("CasualResponse", back_populates="responder", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.email}>"
    
    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.email
    
    @property
    def is_premium(self):
        return self.subscription_status == UserStatus.PREMIUM
    
    @property
    def has_unlimited_credits(self):
        """Premium users have unlimited credits"""
        return self.plan_type == 'premium' or self.credits_remaining == -1
    
    @property
    def age(self):
        if self.date_of_birth:
            from datetime import datetime
            today = datetime.now()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    @property
    def photos_revealed(self):
        """
        Check if photos should be revealed.
        Conditions:
        1. Must have a photo_reveal_date set
        2. Must have passed 24 hours
        3. Must have rated custom answers
        """
        if not self.photo_reveal_date:
            return False
        
        from datetime import datetime
        if datetime.now() < self.photo_reveal_date:
            return False
        
        # Must have rated custom answers
        return self.has_rated_custom_answers
    
    def get_compatibility_answers(self) -> dict:
        """Get all compatibility answers as a dictionary"""
        return {
            'q1': self.q1_core_need,
            'q2': self.q2_sex_intimacy,
            'q3': self.q3_conflict,
            'q4': self.q4_success_response,
            'q5': self.q5_gender_roles,
            'q6': self.q6_religion,
            'q7': self.q7_crisis_response,
            'q8': self.q8_emotional_maturity
        }