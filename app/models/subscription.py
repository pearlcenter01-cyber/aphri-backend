from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.utils.constants import SubscriptionStatus
import uuid

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    # ============================================================
    # PRIMARY KEY
    # ============================================================
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # ============================================================
    # CHAPA DATA
    # ============================================================
    chapa_subscription_id = Column(String(255), nullable=True)  # If using recurring
    chapa_tx_ref = Column(String(255), nullable=True)  # Transaction reference
    chapa_customer_id = Column(String(255), nullable=True)
    
    # ============================================================
    # PLAN DATA
    # ============================================================
    plan_type = Column(String(20), nullable=False)  # monthly, quarterly, yearly
    plan_name = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)  # In ETB
    currency = Column(String(3), default="ETB")
    
    # ============================================================
    # STATUS
    # ============================================================
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    cancel_at_period_end = Column(Boolean, default=False)
    
    # ============================================================
    # DATES
    # ============================================================
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    canceled_at = Column(DateTime, nullable=True)
    
    # ============================================================
    # TRIAL
    # ============================================================
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    
    # ============================================================
    # TIMESTAMPS
    # ============================================================
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # ============================================================
    # RELATIONSHIPS
    # ============================================================
    user = relationship("User", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Subscription {self.user_id} - {self.plan_type} ({self.status})>"
    
    @property
    def is_active(self):
        return self.status == SubscriptionStatus.ACTIVE
    
    @property
    def days_remaining(self):
        from datetime import datetime
        if self.current_period_end and self.is_active:
            delta = self.current_period_end - datetime.now()
            return max(0, delta.days)
        return 0