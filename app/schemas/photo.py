from pydantic import BaseModel
from typing import Optional

class PhotoUpload(BaseModel):
    is_primary: bool = False

class PhotoResponse(BaseModel):
    id: str
    url_thumbnail: str
    url_medium: str
    url_large: str
    is_primary: bool
    order: int