from pydantic import BaseModel, Field

class PushTokenRegister(BaseModel):
    token: str
    device_type: str = Field(..., pattern="^(ios|android)$")