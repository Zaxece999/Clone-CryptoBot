from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from app.models.base import Base


class NotificationType(str, Enum):
    DEPOSIT_RECEIVED = "deposit_received"
    WITHDRAWAL_COMPLETED = "withdrawal_completed"
    WITHDRAWAL_FAILED = "withdrawal_failed"
    CHECK_ACTIVATED = "check_activated"
    INVOICE_PAID = "invoice_paid"
    P2P_ORDER_CREATED = "p2p_order_created"
    P2P_ORDER_MATCHED = "p2p_order_matched"
    P2P_ORDER_COMPLETED = "p2p_order_completed"
    P2P_ORDER_CANCELLED = "p2p_order_cancelled"
    EXCHANGE_COMPLETED = "exchange_completed"
    SUBSCRIPTION_ACTIVATED = "subscription_activated"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    SECURITY_ALERT = "security_alert"
    SYSTEM_MAINTENANCE = "system_maintenance"
    PROMOTIONAL = "promotional"


class NotificationChannel(str, Enum):
    TELEGRAM = "telegram"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"
    WEBHOOK = "webhook"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    channels = Column(JSON, nullable=False, default=list)

    priority = Column(SQLEnum(NotificationPriority), nullable=False, default=NotificationPriority.NORMAL)
    status = Column(SQLEnum(NotificationStatus), nullable=False, default=NotificationStatus.PENDING, index=True)

    data = Column(JSON, nullable=True)
    template_id = Column(String(100), nullable=True)

    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    max_attempts = Column(Integer, default=3, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)

    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    read_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="notifications")
    delivery_logs = relationship("NotificationDeliveryLog", back_populates="notification", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Notification(id={self.id}, type={self.type}, user_id={self.user_id})>"

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    @property
    def is_delivered(self) -> bool:
        return self.status == NotificationStatus.DELIVERED

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at


class NotificationDeliveryLog(Base):
    __tablename__ = "notification_delivery_logs"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False, index=True)

    channel = Column(SQLEnum(NotificationChannel), nullable=False, index=True)

    status = Column(SQLEnum(NotificationStatus), nullable=False, index=True)

    recipient = Column(String(255), nullable=True)
    provider = Column(String(100), nullable=True)
    external_id = Column(String(255), nullable=True)

    response_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    notification = relationship("Notification", back_populates="delivery_logs")

    def __repr__(self):
        return f"<NotificationDeliveryLog(id={self.id}, channel={self.channel}, status={self.status})>"


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True, index=True)

    template_id = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    supported_channels = Column(JSON, nullable=False, default=list)

    telegram_template = Column(JSON, nullable=True)
    email_template = Column(JSON, nullable=True)
    push_template = Column(JSON, nullable=True)
    sms_template = Column(JSON, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(SQLEnum(NotificationPriority), nullable=False, default=NotificationPriority.NORMAL)

    language = Column(String(10), nullable=False, default="ru")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<NotificationTemplate(id={self.id}, template_id={self.template_id})>"


class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    enabled = Column(Boolean, default=True, nullable=False)

    deposit_notifications = Column(Boolean, default=True, nullable=False)
    withdrawal_notifications = Column(Boolean, default=True, nullable=False)
    trading_notifications = Column(Boolean, default=True, nullable=False)
    security_notifications = Column(Boolean, default=True, nullable=False)
    promotional_notifications = Column(Boolean, default=False, nullable=False)

    telegram_enabled = Column(Boolean, default=True, nullable=False)
    email_enabled = Column(Boolean, default=False, nullable=False)
    push_enabled = Column(Boolean, default=True, nullable=False)
    sms_enabled = Column(Boolean, default=False, nullable=False)

    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)

    quiet_hours_start = Column(String(5), nullable=True)
    quiet_hours_end = Column(String(5), nullable=True)
    timezone = Column(String(50), nullable=False, default="UTC")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="notification_settings")

    def __repr__(self):
        return f"<NotificationSettings(id={self.id}, user_id={self.user_id})>"

    def is_type_enabled(self, notification_type: NotificationType) -> bool:
        if not self.enabled:
            return False

        type_mapping = {
            NotificationType.DEPOSIT_RECEIVED: self.deposit_notifications,
            NotificationType.WITHDRAWAL_COMPLETED: self.withdrawal_notifications,
            NotificationType.WITHDRAWAL_FAILED: self.withdrawal_notifications,
            NotificationType.P2P_ORDER_CREATED: self.trading_notifications,
            NotificationType.P2P_ORDER_MATCHED: self.trading_notifications,
            NotificationType.P2P_ORDER_COMPLETED: self.trading_notifications,
            NotificationType.EXCHANGE_COMPLETED: self.trading_notifications,
            NotificationType.SECURITY_ALERT: self.security_notifications,
            NotificationType.PROMOTIONAL: self.promotional_notifications,
        }

        return type_mapping.get(notification_type, True)

    def is_channel_enabled(self, channel: NotificationChannel) -> bool:
        channel_mapping = {
            NotificationChannel.TELEGRAM: self.telegram_enabled,
            NotificationChannel.EMAIL: self.email_enabled,
            NotificationChannel.PUSH: self.push_enabled,
            NotificationChannel.SMS: self.sms_enabled,
        }

        return channel_mapping.get(channel, False)


class NotificationQueue(Base):
    __tablename__ = "notification_queue"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False, index=True)

    priority = Column(Integer, default=0, nullable=False, index=True)

    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(String(20), nullable=False, default="pending", index=True)
    attempts = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    notification = relationship("Notification")

    def __repr__(self):
        return f"<NotificationQueue(id={self.id}, notification_id={self.notification_id}, status={self.status})>"


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=True)

    event_types = Column(JSON, nullable=False, default=list)

    is_active = Column(Boolean, default=True, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    timeout_seconds = Column(Integer, default=30, nullable=False)

    total_requests = Column(Integer, default=0, nullable=False)
    successful_requests = Column(Integer, default=0, nullable=False)
    failed_requests = Column(Integer, default=0, nullable=False)
    last_request_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    last_error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="webhook_endpoints")

    def __repr__(self):
        return f"<WebhookEndpoint(id={self.id}, user_id={self.user_id}, url={self.url})>"

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100
