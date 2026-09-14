from pydantic import BaseModel, Field

class PaymentInitiate(BaseModel):
    plan_type: str = Field(..., pattern="^(starter|standard|premium)$")

class PaymentVerify(BaseModel):
    tx_ref: str