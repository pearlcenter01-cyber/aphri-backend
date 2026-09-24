from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProfileUpdate(BaseModel):
    # Basic info
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None

    # Preferences
    looking_for: Optional[str] = None
    looking_for_gender: Optional[str] = None
    looking_for_age_min: Optional[int] = None
    looking_for_age_max: Optional[int] = None
    vibe: Optional[str] = None
    vibe_subcategories: Optional[str] = None

    # Location
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Religion & life status
    religion: Optional[str] = None
    religion_preferences: Optional[str] = None
    is_single_parent: Optional[bool] = None
    is_divorced: Optional[bool] = None
    open_to_single_parent: Optional[bool] = None
    open_to_divorced: Optional[bool] = None
    open_to_never_married: Optional[bool] = None

    # Compatibility questions
    q1_core_need: Optional[str] = None
    q2_sex_intimacy: Optional[str] = None
    q3_conflict: Optional[str] = None
    q4_success_response: Optional[str] = None
    q5_gender_roles: Optional[str] = None
    q6_religion: Optional[str] = None
    q7_crisis_response: Optional[str] = None
    q8_emotional_maturity: Optional[str] = None

    # Custom questions + registration status
    custom_questions: Optional[str] = None
    is_registration_complete: Optional[bool] = None

    # Profile-only fields (kept for compatibility)
    bio: Optional[str] = None
    about_me: Optional[str] = None
    favorite_quote: Optional[str] = None
    headline: Optional[str] = None
    interests: Optional[str] = None
    prompt_1: Optional[str] = None
    prompt_1_answer: Optional[str] = None
    prompt_2: Optional[str] = None
    prompt_2_answer: Optional[str] = None
    prompt_3: Optional[str] = None
    prompt_3_answer: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    company: Optional[str] = None
    hometown: Optional[str] = None
    smoking: Optional[str] = None
    drinking: Optional[str] = None
    zodiac: Optional[str] = None

class ProfileResponse(BaseModel):
    id: str
    user_id: str
    bio: Optional[str]
    about_me: Optional[str]
    headline: Optional[str]
    interests: Optional[str]
    looking_for: Optional[str]
    prompts: List[dict]
    education: Optional[str]
    occupation: Optional[str]
    company: Optional[str]
    hometown: Optional[str]
    completeness_score: int
    created_at: datetime
    updated_at: datetime
    is_registration_complete: bool