from pydantic import BaseModel
from typing import Optional

class MatchResponse(BaseModel):
    match_id: str
    user: dict
    matched_at: str
    last_message: Optional[dict] = None
    unread_count: int
    is_active: bool