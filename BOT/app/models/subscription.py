from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, Text, ForeignKey, Index, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional
import enum

from app.models.base import Base


class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"


class SubscriptionType(enum.Enum):
    CHANNEL = "channel"
    GROUP = "group"
    BOT = "bot"
    SERVICE = "service"


class BillingPeriod(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(String(32), unique=True, nullable=False, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    subscription_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pending")

    price = Column(Numeric(20, 8), nullable=False)
    currency = Column(String(10), nullable=False)
    billing_period = Column(String(20), nullable=False)

    chat_id = Column(String(50), nullable=True)
    chat_username = Column(String(100), nullable=True)
    chat_title = Column(String(200), nullable=True)
    invite_link = Column(String(500), nullable=True)

    starts_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    next_billing_at = Column(DateTime(timezone=True), nullable=True)

    trial_days = Column(Integer, nullable=True, default=0)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)

    total_payments = Column(Integer, nullable=False, default=0)
    total_amount_paid = Column(Numeric(20, 8), nullable=False, default=0)
    failed_payments = Column(Integer, nullable=False, default=0)

    auto_renew = Column(Boolean, nullable=False, default=True)
    send_reminders = Column(Boolean, nullable=False, default=True)

    extra_data = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="subscriptions")
    payments = relationship("SubscriptionPayment", back_populates="subscription", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_subscriptions_user_id', 'user_id'),
        Index('idx_subscriptions_status', 'status'),
        Index('idx_subscriptions_type', 'subscription_type'),
        Index('idx_subscriptions_chat_id', 'chat_id'),
        Index('idx_subscriptions_expires_at', 'expires_at'),
        Index('idx_subscriptions_next_billing', 'next_billing_at'),
        Index('idx_subscriptions_created_at', 'created_at'),
    )

    @property
    def is_active(self) -> bool:
        if self.status != SubscriptionStatus.ACTIVE.value:
            return False

        now = datetime.utcnow()

        if self.trial_ends_at and now <= self.trial_ends_at:
            return True

        if self.expires_at and now > self.expires_at:
            return False

        return True

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_trial(self) -> bool:
        if not self.trial_ends_at:
            return False
        return datetime.utcnow() <= self.trial_ends_at

    @property
    def days_until_expiry(self) -> Optional[int]:
        if not self.expires_at:
            return None

        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)

    @property
    def next_payment_amount(self) -> Decimal:
        return Decimal(str(self.price))


class SubscriptionPayment(Base):
    __tablename__ = "subscription_payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String(32), unique=True, nullable=False, index=True)

    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    amount = Column(Numeric(20, 8), nullable=False)
    currency = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, default="pending")

    billing_period_start = Column(DateTime(timezone=True), nullable=False)
    billing_period_end = Column(DateTime(timezone=True), nullable=False)

    transaction_id = Column(String(64), nullable=True)

    failure_reason = Column(Text, nullable=True)
    refund_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    refunded_at = Column(DateTime(timezone=True), nullable=True)

    subscription = relationship("Subscription", back_populates="payments")
    user = relationship("User")

    __table_args__ = (
        Index('idx_subscription_payments_subscription_id', 'subscription_id'),
        Index('idx_subscription_payments_user_id', 'user_id'),
        Index('idx_subscription_payments_status', 'status'),
        Index('idx_subscription_payments_created_at', 'created_at'),
        Index('idx_subscription_payments_billing_period', 'billing_period_start', 'billing_period_end'),
    )

    @property
    def is_paid(self) -> bool:
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(String(32), unique=True, nullable=False, index=True)

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    subscription_type = Column(String(20), nullable=False)

    price = Column(Numeric(20, 8), nullable=False)
    currency = Column(String(10), nullable=False)
    billing_period = Column(String(20), nullable=False)

    trial_days = Column(Integer, nullable=True, default=0)

    max_subscribers = Column(Integer, nullable=True)
    features = Column(Text, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    is_public = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_subscription_plans_type', 'subscription_type'),
        Index('idx_subscription_plans_active', 'is_active'),
        Index('idx_subscription_plans_public', 'is_public'),
        Index('idx_subscription_plans_price', 'price'),
    )


class SubscriptionInvite(Base):
    __tablename__ = "subscription_invites"

    id = Column(Integer, primary_key=True, index=True)
    invite_id = Column(String(32), unique=True, nullable=False, index=True)

    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    max_uses = Column(Integer, nullable=True)
    uses_count = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    subscription = relationship("Subscription")
    creator = relationship("User")

    __table_args__ = (
        Index('idx_subscription_invites_subscription_id', 'subscription_id'),
        Index('idx_subscription_invites_creator_id', 'creator_id'),
        Index('idx_subscription_invites_active', 'is_active'),
        Index('idx_subscription_invites_expires_at', 'expires_at'),
    )

    @property
    def is_valid(self) -> bool:
        if not self.is_active:
            return False

        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False

        if self.max_uses and self.uses_count >= self.max_uses:
            return False

        return True


class SubscriptionStats(Base):
    __tablename__ = "subscription_stats"

    id = Column(Integer, primary_key=True, index=True)

    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)

    date = Column(DateTime(timezone=True), nullable=False)

    active_subscribers = Column(Integer, nullable=False, default=0)
    new_subscribers = Column(Integer, nullable=False, default=0)
    cancelled_subscribers = Column(Integer, nullable=False, default=0)
    revenue = Column(Numeric(20, 8), nullable=False, default=0)
    failed_payments = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    subscription = relationship("Subscription")

    __table_args__ = (
        Index('idx_subscription_stats_subscription_date', 'subscription_id', 'date'),
        Index('idx_subscription_stats_date', 'date'),
    )


class SubscriptionNotification(Base):
    __tablename__ = "subscription_notifications"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String(32), unique=True, nullable=False, index=True)

    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    notification_type = Column(String(50), nullable=False)

    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    is_sent = Column(Boolean, nullable=False, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    scheduled_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    subscription = relationship("Subscription")
    user = relationship("User")

    __table_args__ = (
        Index('idx_subscription_notifications_subscription_id', 'subscription_id'),
        Index('idx_subscription_notifications_user_id', 'user_id'),
        Index('idx_subscription_notifications_type', 'notification_type'),
        Index('idx_subscription_notifications_sent', 'is_sent'),
        Index('idx_subscription_notifications_scheduled', 'scheduled_at'),
    )
