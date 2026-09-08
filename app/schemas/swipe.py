from pydantic import BaseModel, Field
from typing import Optional

class SwipeRequest(BaseModel):
    target_user_id: str
    direction: str = Field(..., pattern="^(like|pass)$")

class SwipeResponse(BaseModel):
    swipe_id: str
    direction: str
    is_match: bool = False
    match: Optional[dict] = None