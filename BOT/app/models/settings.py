from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from app.models.base import Base


class ReferralPeriod(str, Enum):
    ALL_TIME = "all_time"
    YESTERDAY = "yesterday"
    WEEK = "week"
    MONTH = "month"


class NotificationGroup(str, Enum):
    BROADCASTS = "broadcasts"
    REFERRALS = "referrals"
    CRYPTO_PAY = "crypto_pay"
    P2P_MARKET = "p2p_market"
    GIVEAWAYS = "giveaways"
    SUBSCRIPTIONS_CREATOR = "subscriptions_creator"
    SUBSCRIPTIONS_SUBSCRIBER = "subscriptions_subscriber"


class NotificationSubtype(str, Enum):
    NEWS_BROADCASTS = "news_broadcasts"
    MARKETING_BROADCASTS = "marketing_broadcasts"

    REFERRAL_REWARDS = "referral_rewards"

    PAYMENT_NOTIFICATIONS = "payment_notifications"

    NEW_REVIEW = "new_review"

    INVITATION_PARTICIPATION = "invitation_participation"

    NEW_SUBSCRIBERS = "new_subscribers"
    SUBSCRIPTION_RENEWALS = "subscription_renewals"
    SUBSCRIPTION_CANCELLATIONS = "subscription_cancellations"

    RENEWAL_NOTIFICATIONS = "renewal_notifications"
    INSUFFICIENT_BALANCE = "insufficient_balance"
    CANCELLATION_NOTIFICATIONS = "cancellation_notifications"


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    timezone = Column(String(50), default="UTC", nullable=False)
    local_currency = Column(String(10), default="USD", nullable=False)
    bot_language = Column(String(10), default="ru", nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="user_settings")
    notification_preferences = relationship("NotificationPreferences", back_populates="user_settings", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserSettings(id={self.id}, user_id={self.user_id})>"


class ReferralStats(Base):
    __tablename__ = "referral_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    period = Column(SQLEnum(ReferralPeriod), nullable=False, index=True)

    invited_count = Column(Integer, default=0, nullable=False)
    active_users_count = Column(Integer, default=0, nullable=False)
    earnings_usd = Column(String(20), default="0.00", nullable=False)

    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")

    def __repr__(self):
        return f"<ReferralStats(id={self.id}, user_id={self.user_id}, period={self.period})>"


class NotificationPreferences(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_settings_id = Column(Integer, ForeignKey("user_settings.id"), nullable=False, unique=True, index=True)

    news_broadcasts_enabled = Column(Boolean, default=True, nullable=False)
    news_broadcasts_sound = Column(Boolean, default=True, nullable=False)
    marketing_broadcasts_enabled = Column(Boolean, default=True, nullable=False)
    marketing_broadcasts_sound = Column(Boolean, default=True, nullable=False)

    referral_rewards_enabled = Column(Boolean, default=True, nullable=False)
    referral_rewards_sound = Column(Boolean, default=True, nullable=False)

    payment_notifications_enabled = Column(Boolean, default=True, nullable=False)
    payment_notifications_sound = Column(Boolean, default=True, nullable=False)

    new_review_enabled = Column(Boolean, default=True, nullable=False)
    new_review_sound = Column(Boolean, default=True, nullable=False)

    invitation_participation_enabled = Column(Boolean, default=True, nullable=False)
    invitation_participation_sound = Column(Boolean, default=True, nullable=False)

    new_subscribers_enabled = Column(Boolean, default=True, nullable=False)
    new_subscribers_sound = Column(Boolean, default=True, nullable=False)
    subscription_renewals_enabled = Column(Boolean, default=True, nullable=False)
    subscription_renewals_sound = Column(Boolean, default=True, nullable=False)
    subscription_cancellations_enabled = Column(Boolean, default=True, nullable=False)
    subscription_cancellations_sound = Column(Boolean, default=True, nullable=False)

    renewal_notifications_enabled = Column(Boolean, default=True, nullable=False)
    renewal_notifications_sound = Column(Boolean, default=True, nullable=False)
    insufficient_balance_sound = Column(Boolean, default=True, nullable=False)
    cancellation_notifications_enabled = Column(Boolean, default=True, nullable=False)
    cancellation_notifications_sound = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user_settings = relationship("UserSettings", back_populates="notification_preferences")

    def __repr__(self):
        return f"<NotificationPreferences(id={self.id}, user_settings_id={self.user_settings_id})>"

    def get_notification_setting(self, subtype: NotificationSubtype) -> dict:
        mapping = {
            NotificationSubtype.NEWS_BROADCASTS: {
                'enabled': self.news_broadcasts_enabled,
                'sound': self.news_broadcasts_sound
            },
            NotificationSubtype.MARKETING_BROADCASTS: {
                'enabled': self.marketing_broadcasts_enabled,
                'sound': self.marketing_broadcasts_sound
            },
            NotificationSubtype.REFERRAL_REWARDS: {
                'enabled': self.referral_rewards_enabled,
                'sound': self.referral_rewards_sound
            },
            NotificationSubtype.PAYMENT_NOTIFICATIONS: {
                'enabled': self.payment_notifications_enabled,
                'sound': self.payment_notifications_sound
            },
            NotificationSubtype.NEW_REVIEW: {
                'enabled': self.new_review_enabled,
                'sound': self.new_review_sound
            },
            NotificationSubtype.INVITATION_PARTICIPATION: {
                'enabled': self.invitation_participation_enabled,
                'sound': self.invitation_participation_sound
            },
            NotificationSubtype.NEW_SUBSCRIBERS: {
                'enabled': self.new_subscribers_enabled,
                'sound': self.new_subscribers_sound
            },
            NotificationSubtype.SUBSCRIPTION_RENEWALS: {
                'enabled': self.subscription_renewals_enabled,
                'sound': self.subscription_renewals_sound
            },
            NotificationSubtype.SUBSCRIPTION_CANCELLATIONS: {
                'enabled': self.subscription_cancellations_enabled,
                'sound': self.subscription_cancellations_sound
            },
            NotificationSubtype.RENEWAL_NOTIFICATIONS: {
                'enabled': self.renewal_notifications_enabled,
                'sound': self.renewal_notifications_sound
            },
            NotificationSubtype.INSUFFICIENT_BALANCE: {
                'enabled': True,
                'sound': self.insufficient_balance_sound
            },
            NotificationSubtype.CANCELLATION_NOTIFICATIONS: {
                'enabled': self.cancellation_notifications_enabled,
                'sound': self.cancellation_notifications_sound
            },
        }

        return mapping.get(subtype, {'enabled': True, 'sound': True})

    def update_notification_setting(self, subtype: NotificationSubtype, enabled: bool = None, sound: bool = None):
        mapping = {
            NotificationSubtype.NEWS_BROADCASTS: ('news_broadcasts_enabled', 'news_broadcasts_sound'),
            NotificationSubtype.MARKETING_BROADCASTS: ('marketing_broadcasts_enabled', 'marketing_broadcasts_sound'),
            NotificationSubtype.REFERRAL_REWARDS: ('referral_rewards_enabled', 'referral_rewards_sound'),
            NotificationSubtype.PAYMENT_NOTIFICATIONS: ('payment_notifications_enabled', 'payment_notifications_sound'),
            NotificationSubtype.NEW_REVIEW: ('new_review_enabled', 'new_review_sound'),
            NotificationSubtype.INVITATION_PARTICIPATION: ('invitation_participation_enabled', 'invitation_participation_sound'),
            NotificationSubtype.NEW_SUBSCRIBERS: ('new_subscribers_enabled', 'new_subscribers_sound'),
            NotificationSubtype.SUBSCRIPTION_RENEWALS: ('subscription_renewals_enabled', 'subscription_renewals_sound'),
            NotificationSubtype.SUBSCRIPTION_CANCELLATIONS: ('subscription_cancellations_enabled', 'subscription_cancellations_sound'),
            NotificationSubtype.RENEWAL_NOTIFICATIONS: ('renewal_notifications_enabled', 'renewal_notifications_sound'),
            NotificationSubtype.INSUFFICIENT_BALANCE: (None, 'insufficient_balance_sound'),
            NotificationSubtype.CANCELLATION_NOTIFICATIONS: ('cancellation_notifications_enabled', 'cancellation_notifications_sound'),
        }

        if subtype in mapping:
            enabled_attr, sound_attr = mapping[subtype]

            if enabled is not None and enabled_attr:
                setattr(self, enabled_attr, enabled)

            if sound is not None and sound_attr:
                setattr(self, sound_attr, sound)
