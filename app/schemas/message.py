from pydantic import BaseModel, Field
from typing import Optional

class MessageSend(BaseModel):
    content: Optional[str] = None
    message_type: str = Field("text", pattern="^(text|photo|video|audio|system|location)$")
    media_url: Optional[str] = None
    media_thumbnail: Optional[str] = None

class MessageResponse(BaseModel):
    id: str
    match_id: str
    sender_id: str
    receiver_id: str
    message_type: str
    content: Optional[str]
    media_url: Optional[str]
    media_thumbnail: Optional[str]
    is_read: bool
    created_at: str