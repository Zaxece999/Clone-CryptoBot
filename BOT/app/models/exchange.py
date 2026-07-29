from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
from datetime import datetime
from typing import Optional
import enum

from app.models.base import Base


class ExchangeStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ExchangeType(enum.Enum):
    CRYPTO_TO_CRYPTO = "crypto_to_crypto"
    CRYPTO_TO_FIAT = "crypto_to_fiat"
    FIAT_TO_CRYPTO = "fiat_to_crypto"


class Exchange(Base):
    __tablename__ = "exchanges"

    id = Column(Integer, primary_key=True, index=True)
    exchange_id = Column(String(32), unique=True, nullable=False, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    exchange_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pending")

    from_currency = Column(String(10), nullable=False)
    to_currency = Column(String(10), nullable=False)
    from_amount = Column(Numeric(20, 8), nullable=False)
    to_amount = Column(Numeric(20, 8), nullable=False)

    exchange_rate = Column(Numeric(20, 8), nullable=False)

    fee_amount = Column(Numeric(20, 8), nullable=False, default=0)
    fee_currency = Column(String(10), nullable=True)
    fee_percentage = Column(Numeric(5, 4), nullable=False, default=0)

    expires_at = Column(DateTime(timezone=True), nullable=True)

    debit_transaction_id = Column(String(64), nullable=True)
    credit_transaction_id = Column(String(64), nullable=True)

    external_exchange_id = Column(String(100), nullable=True)
    external_provider = Column(String(50), nullable=True)

    notes = Column(Text, nullable=True)
    failure_reason = Column(Text, nullable=True)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="exchanges")

    __table_args__ = (
        Index('idx_exchanges_user_id', 'user_id'),
        Index('idx_exchanges_status', 'status'),
        Index('idx_exchanges_created_at', 'created_at'),
        Index('idx_exchanges_from_currency', 'from_currency'),
        Index('idx_exchanges_to_currency', 'to_currency'),
        Index('idx_exchanges_expires_at', 'expires_at'),
        Index('idx_exchanges_external_id', 'external_exchange_id'),
    )

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_pending(self) -> bool:
        return self.status == ExchangeStatus.PENDING.value

    @property
    def is_completed(self) -> bool:
        return self.status == ExchangeStatus.COMPLETED.value

    @property
    def is_failed(self) -> bool:
        return self.status == ExchangeStatus.FAILED.value

    @property
    def total_from_amount(self) -> Decimal:
        if self.fee_currency == self.from_currency:
            return Decimal(str(self.from_amount)) + Decimal(str(self.fee_amount))
        return Decimal(str(self.from_amount))

    @property
    def net_to_amount(self) -> Decimal:
        if self.fee_currency == self.to_currency:
            return Decimal(str(self.to_amount)) - Decimal(str(self.fee_amount))
        return Decimal(str(self.to_amount))


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id = Column(Integer, primary_key=True, index=True)

    from_currency = Column(String(10), nullable=False)
    to_currency = Column(String(10), nullable=False)

    rate = Column(Numeric(20, 8), nullable=False)
    buy_rate = Column(Numeric(20, 8), nullable=False)
    sell_rate = Column(Numeric(20, 8), nullable=False)
    spread_percentage = Column(Numeric(5, 4), nullable=False, default=0)

    source = Column(String(50), nullable=False)

    min_amount = Column(Numeric(20, 8), nullable=True)
    max_amount = Column(Numeric(20, 8), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_exchange_rates_pair', 'from_currency', 'to_currency'),
        Index('idx_exchange_rates_active', 'is_active'),
        Index('idx_exchange_rates_source', 'source'),
        Index('idx_exchange_rates_updated_at', 'updated_at'),
    )

    @property
    def pair_name(self) -> str:
        return f"{self.from_currency}/{self.to_currency}"

    @property
    def spread_amount(self) -> Decimal:
        return Decimal(str(self.sell_rate)) - Decimal(str(self.buy_rate))


class ExchangeProvider(Base):
    __tablename__ = "exchange_providers"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    api_url = Column(String(255), nullable=True)
    api_key = Column(String(255), nullable=True)
    api_secret = Column(String(255), nullable=True)

    supported_currencies = Column(Text, nullable=True)

    default_fee_percentage = Column(Numeric(5, 4), nullable=False, default=0)
    min_fee_amount = Column(Numeric(20, 8), nullable=True)
    max_fee_amount = Column(Numeric(20, 8), nullable=True)

    min_exchange_amount = Column(Numeric(20, 8), nullable=True)
    max_exchange_amount = Column(Numeric(20, 8), nullable=True)
    daily_limit = Column(Numeric(20, 8), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=0)

    total_exchanges = Column(Integer, nullable=False, default=0)
    successful_exchanges = Column(Integer, nullable=False, default=0)
    failed_exchanges = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('idx_exchange_providers_active', 'is_active'),
        Index('idx_exchange_providers_priority', 'priority'),
        Index('idx_exchange_providers_name', 'name'),
    )

    @property
    def success_rate(self) -> float:
        if self.total_exchanges == 0:
            return 0.0
        return (self.successful_exchanges / self.total_exchanges) * 100

    @property
    def is_available(self) -> bool:
        return self.is_active and bool(self.api_url)


class ExchangeLimit(Base):
    __tablename__ = "exchange_limits"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    currency = Column(String(10), nullable=False)

    daily_limit = Column(Numeric(20, 8), nullable=False)
    monthly_limit = Column(Numeric(20, 8), nullable=False)
    yearly_limit = Column(Numeric(20, 8), nullable=False)

    daily_used = Column(Numeric(20, 8), nullable=False, default=0)
    monthly_used = Column(Numeric(20, 8), nullable=False, default=0)
    yearly_used = Column(Numeric(20, 8), nullable=False, default=0)

    daily_reset_at = Column(DateTime(timezone=True), nullable=False)
    monthly_reset_at = Column(DateTime(timezone=True), nullable=False)
    yearly_reset_at = Column(DateTime(timezone=True), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="exchange_limits")

    __table_args__ = (
        Index('idx_exchange_limits_user_currency', 'user_id', 'currency'),
        Index('idx_exchange_limits_daily_reset', 'daily_reset_at'),
        Index('idx_exchange_limits_monthly_reset', 'monthly_reset_at'),
    )

    @property
    def daily_remaining(self) -> Decimal:
        return Decimal(str(self.daily_limit)) - Decimal(str(self.daily_used))

    @property
    def monthly_remaining(self) -> Decimal:
        return Decimal(str(self.monthly_limit)) - Decimal(str(self.monthly_used))

    @property
    def yearly_remaining(self) -> Decimal:
        return Decimal(str(self.yearly_limit)) - Decimal(str(self.yearly_used))

    def can_exchange(self, amount: Decimal) -> bool:
        return (
            amount <= self.daily_remaining and
            amount <= self.monthly_remaining and
            amount <= self.yearly_remaining
        )


class ExchangeHistory(Base):
    __tablename__ = "exchange_history"

    id = Column(Integer, primary_key=True, index=True)

    from_currency = Column(String(10), nullable=False)
    to_currency = Column(String(10), nullable=False)

    rate = Column(Numeric(20, 8), nullable=False)
    volume_24h = Column(Numeric(20, 8), nullable=True)
    change_24h = Column(Numeric(10, 4), nullable=True)

    source = Column(String(50), nullable=False)

    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_exchange_history_pair_time', 'from_currency', 'to_currency', 'timestamp'),
        Index('idx_exchange_history_timestamp', 'timestamp'),
        Index('idx_exchange_history_source', 'source'),
    )
