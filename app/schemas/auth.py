from pydantic import BaseModel, EmailStr
from typing import Optional, List

class UserRegister(BaseModel):
    # ============================================================
    # BASIC INFO
    # ============================================================
    email: EmailStr
    password: str
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    
    # ============================================================
    # PREFERENCES
    # ============================================================
    looking_for_gender: Optional[str] = None  # men, women, everyone
    looking_for: Optional[str] = None  # Serious Relationship, Intimate Connection
    vibe: Optional[str] = None
    vibe_subcategories: Optional[str] = None
    open_to_never_married: Optional[bool] = True
    
    # Age Range Preference
    looking_for_age_min: Optional[int] = None
    looking_for_age_max: Optional[int] = None
    
    # ============================================================
    # 🆕 RELIGION
    # ============================================================
    religion: Optional[str] = None  # orthodox, catholic, protestant, muslim, other, none
    religion_preferences: Optional[str] = None  # comma-separated list
    
    # ============================================================
    # 🆕 LIFE STATUS
    # ============================================================
    is_single_parent: Optional[bool] = False
    is_divorced: Optional[bool] = False
    open_to_single_parent: Optional[bool] = True
    open_to_divorced: Optional[bool] = True
    
    # ============================================================
    # 🆕 CUSTOM QUESTIONS
    # ============================================================
    custom_questions: Optional[str] = None  # JSON array of custom questions
    
    # ============================================================
    # 🆕 LOCATION
    # ============================================================
    city: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # ============================================================
    # 🆕 QUOTE
    # ============================================================
    quote: Optional[str] = None
    
    # ============================================================
    # COMPATIBILITY QUESTIONS (8 Questions)
    # ============================================================
    q1_core_need: Optional[str] = None
    q2_sex_intimacy: Optional[str] = None
    q3_conflict: Optional[str] = None
    q4_success_response: Optional[str] = None
    q5_gender_roles: Optional[str] = None
    q6_religion: Optional[str] = None
    q7_crisis_response: Optional[str] = None
    q8_emotional_maturity: Optional[str] = None

    # ============================================================
    # 🆕 REGISTRATION STATUS
    # ============================================================
    is_registration_complete: Optional[bool] = True     # ← ADDED


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    subscription_status: str
    is_registration_complete: bool = True 


class RefreshToken(BaseModel):
    refresh_token: str