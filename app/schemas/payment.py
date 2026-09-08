from pydantic import BaseModel, Field

class PaymentInitiate(BaseModel):
    plan_type: str = Field(..., pattern="^(monthly|quarterly|yearly)$")

class PaymentVerify(BaseModel):
    tx_ref: str