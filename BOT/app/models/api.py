from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from typing import Optional
import enum
import secrets
import hashlib

from app.models.base import Base


class ApiKeyStatus(enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ApiKeyScope(enum.Enum):
    READ = "read"
    WRITE = "write"
    WALLET_READ = "wallet:read"
    WALLET_WRITE = "wallet:write"
    INVOICE_READ = "invoice:read"
    INVOICE_WRITE = "invoice:write"
    CHECK_READ = "check:read"
    CHECK_WRITE = "check:write"
    P2P_READ = "p2p:read"
    P2P_WRITE = "p2p:write"
    EXCHANGE_READ = "exchange:read"
    EXCHANGE_WRITE = "exchange:write"
    SUBSCRIPTION_READ = "subscription:read"
    SUBSCRIPTION_WRITE = "subscription:write"
    ADMIN = "admin"


class ApiApplication(Base):
    __tablename__ = "api_applications"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(String(32), unique=True, nullable=False, index=True)

    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    website_url = Column(String(500), nullable=True)
    callback_url = Column(String(500), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)

    rate_limit_per_minute = Column(Integer, nullable=False, default=60)
    rate_limit_per_hour = Column(Integer, nullable=False, default=1000)
    rate_limit_per_day = Column(Integer, nullable=False, default=10000)

    total_requests = Column(Integer, nullable=False, default=0)
    successful_requests = Column(Integer, nullable=False, default=0)
    failed_requests = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", back_populates="api_applications")
    api_keys = relationship("ApiKey", back_populates="application", cascade="all, delete-orphan")
    api_requests = relationship("ApiRequest", back_populates="application", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_api_applications_owner_id', 'owner_id'),
        Index('idx_api_applications_active', 'is_active'),
        Index('idx_api_applications_verified', 'is_verified'),
        Index('idx_api_applications_created_at', 'created_at'),
    )

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(String(32), unique=True, nullable=False, index=True)

    application_id = Column(Integer, ForeignKey("api_applications.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    key_hash = Column(String(128), nullable=False, index=True)
    key_prefix = Column(String(8), nullable=False)

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active")

    scopes = Column(Text, nullable=False)

    allowed_ips = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    rate_limit_per_minute = Column(Integer, nullable=True)
    rate_limit_per_hour = Column(Integer, nullable=True)
    rate_limit_per_day = Column(Integer, nullable=True)

    total_requests = Column(Integer, nullable=False, default=0)
    successful_requests = Column(Integer, nullable=False, default=0)
    failed_requests = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    application = relationship("ApiApplication", back_populates="api_keys")
    user = relationship("User", back_populates="api_keys")
    api_requests = relationship("ApiRequest", back_populates="api_key", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_api_keys_application_id', 'application_id'),
        Index('idx_api_keys_user_id', 'user_id'),
        Index('idx_api_keys_status', 'status'),
        Index('idx_api_keys_expires_at', 'expires_at'),
        Index('idx_api_keys_created_at', 'created_at'),
    )

    @classmethod
    def generate_key(cls) -> tuple[str, str]:
        key = secrets.token_urlsafe(32)

        key_hash = hashlib.sha256(key.encode()).hexdigest()

        return key, key_hash

    @property
    def is_active(self) -> bool:
        if self.status != ApiKeyStatus.ACTIVE.value:
            return False

        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False

        return True

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100


class ApiRequest(Base):
    __tablename__ = "api_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(32), unique=True, nullable=False, index=True)

    application_id = Column(Integer, ForeignKey("api_applications.id", ondelete="CASCADE"), nullable=False)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    method = Column(String(10), nullable=False)
    endpoint = Column(String(200), nullable=False)
    status_code = Column(Integer, nullable=False)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_size = Column(Integer, nullable=True)
    response_size = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    application = relationship("ApiApplication", back_populates="api_requests")
    api_key = relationship("ApiKey", back_populates="api_requests")
    user = relationship("User")

    __table_args__ = (
        Index('idx_api_requests_application_id', 'application_id'),
        Index('idx_api_requests_api_key_id', 'api_key_id'),
        Index('idx_api_requests_user_id', 'user_id'),
        Index('idx_api_requests_created_at', 'created_at'),
        Index('idx_api_requests_endpoint', 'endpoint'),
        Index('idx_api_requests_status_code', 'status_code'),
        Index('idx_api_requests_method', 'method'),
    )

    @property
    def is_successful(self) -> bool:
        return 200 <= self.status_code < 300


class ApiWebhook(Base):
    __tablename__ = "api_webhooks"

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(String(32), unique=True, nullable=False, index=True)

    application_id = Column(Integer, ForeignKey("api_applications.id", ondelete="CASCADE"), nullable=False)

    url = Column(String(500), nullable=False)
    secret = Column(String(128), nullable=True)
    events = Column(Text, nullable=False)

    is_active = Column(Boolean, nullable=False, default=True)

    total_deliveries = Column(Integer, nullable=False, default=0)
    successful_deliveries = Column(Integer, nullable=False, default=0)
    failed_deliveries = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_delivery_at = Column(DateTime(timezone=True), nullable=True)

    application = relationship("ApiApplication")
    webhook_deliveries = relationship("ApiWebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_api_webhooks_application_id', 'application_id'),
        Index('idx_api_webhooks_active', 'is_active'),
        Index('idx_api_webhooks_created_at', 'created_at'),
    )

    @property
    def success_rate(self) -> float:
        if self.total_deliveries == 0:
            return 0.0
        return (self.successful_deliveries / self.total_deliveries) * 100


class ApiWebhookDelivery(Base):
    __tablename__ = "api_webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(String(32), unique=True, nullable=False, index=True)

    webhook_id = Column(Integer, ForeignKey("api_webhooks.id", ondelete="CASCADE"), nullable=False)

    event_type = Column(String(50), nullable=False)
    payload = Column(Text, nullable=False)

    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    error_message = Column(Text, nullable=True)

    attempt_count = Column(Integer, nullable=False, default=1)
    max_attempts = Column(Integer, nullable=False, default=3)
    next_attempt_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    webhook = relationship("ApiWebhook", back_populates="webhook_deliveries")

    __table_args__ = (
        Index('idx_api_webhook_deliveries_webhook_id', 'webhook_id'),
        Index('idx_api_webhook_deliveries_event_type', 'event_type'),
        Index('idx_api_webhook_deliveries_created_at', 'created_at'),
        Index('idx_api_webhook_deliveries_next_attempt', 'next_attempt_at'),
    )

    @property
    def is_successful(self) -> bool:
        return self.status_code and 200 <= self.status_code < 300

    @property
    def can_retry(self) -> bool:
        return self.attempt_count < self.max_attempts and not self.is_successful


class ApiRateLimit(Base):
    __tablename__ = "api_rate_limits"

    id = Column(Integer, primary_key=True, index=True)

    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_type = Column(String(10), nullable=False)

    request_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    api_key = relationship("ApiKey")

    __table_args__ = (
        Index('idx_api_rate_limits_key_window', 'api_key_id', 'window_start', 'window_type'),
        Index('idx_api_rate_limits_window_start', 'window_start'),
    )
