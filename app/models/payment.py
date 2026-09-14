from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid
import enum

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class PaymentMethod(str, enum.Enum):
    CHAPA = "chapa"
    TELEBIRR = "telebirr"
    CBE_BIRR = "cbe_birr"
    AMOLE = "amole"
    HELLO_CASH = "hello_cash"
    CARD = "card"
    PAYPAL = "paypal"

class Payment(Base):
    __tablename__ = "payments"
    
    # ============================================================
    # PRIMARY KEY
    # ============================================================
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id"), nullable=True)
    
    # ============================================================
    # CHAPA DATA
    # ============================================================
    chapa_tx_ref = Column(String(255), nullable=False)
    chapa_transaction_id = Column(String(255), nullable=True)
    chapa_invoice_id = Column(String(255), nullable=True)
    chapa_response = Column(Text, nullable=True)  # Full response from Chapa
    
    # ============================================================
    # PAYMENT DETAILS
    # ============================================================
    amount = Column(Float, nullable=False)  # In ETB
    currency = Column(String(3), default="ETB")
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.CHAPA)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # ============================================================
    # DESCRIPTION
    # ============================================================
    description = Column(String(255), nullable=True)
    plan_type = Column(String(20), nullable=True)  # monthly, quarterly, yearly
    
    # ============================================================
    # METADATA
    # ============================================================
    metadata_json = Column(Text, nullable=True)  # JSON for extra data
    
    # ============================================================
    # TIMESTAMPS
    # ============================================================
    paid_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # ============================================================
    # RELATIONSHIPS
    # ============================================================
    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment {self.chapa_tx_ref} - {self.status}>"