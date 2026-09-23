from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProfileUpdate(BaseModel):
    custom_questions: Optional[str] = None
    is_registration_complete: Optional[bool] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    bio: Optional[str] = None
    about_me: Optional[str] = None
    favorite_quote: Optional[str] = None
    headline: Optional[str] = None
    interests: Optional[str] = None
    looking_for: Optional[str] = None
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
    religion: Optional[str] = None
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