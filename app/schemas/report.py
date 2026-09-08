from pydantic import BaseModel, Field
from typing import Optional

class ReportCreate(BaseModel):
    reported_user_id: str
    reason: str = Field(..., pattern="^(spam|inappropriate|harassment|fake_profile|underage|offensive|other)$")
    description: Optional[str] = None

class BlockCreate(BaseModel):
    user_id: str