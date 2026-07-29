from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.models.base import Base


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    SUSPENDED = "suspended"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    p2p_nickname = Column(String(255), nullable=True, unique=True)

    language_code = Column(String(10), default="ru", nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)

    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)

    is_verified = Column(Boolean, default=False, nullable=False)
    is_premium = Column(Boolean, default=False, nullable=False)

    pin_code_hash = Column(String(255), nullable=True)
    two_factor_enabled = Column(Boolean, default=False, nullable=False)

    notifications_enabled = Column(Boolean, default=True, nullable=False)
    email_notifications = Column(Boolean, default=False, nullable=False)
    sms_notifications = Column(Boolean, default=False, nullable=False)

    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)

    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)

    total_transactions = Column(BigInteger, default=0, nullable=False)
    total_volume_usd = Column(String(50), default="0", nullable=False)

    referrer_id = Column(BigInteger, nullable=True, index=True)
    referral_code = Column(String(20), unique=True, nullable=True, index=True)
    referrals_count = Column(BigInteger, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    blocked_at = Column(DateTime(timezone=True), nullable=True)
    blocked_reason = Column(Text, nullable=True)
    blocked_until = Column(DateTime(timezone=True), nullable=True)

    wallets = relationship("Wallet", back_populates="user", cascade="all, delete-orphan")
    wallet_balances = relationship("WalletBalance", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    created_checks = relationship("Check", foreign_keys="Check.creator_id", back_populates="creator", cascade="all, delete-orphan")
    created_invoices = relationship("Invoice", foreign_keys="Invoice.creator_id", back_populates="creator", cascade="all, delete-orphan")
    p2p_orders = relationship("P2POrder", foreign_keys="P2POrder.creator_id", back_populates="creator", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    p2p_stats = relationship("P2PUserStats", back_populates="user", uselist=False, cascade="all, delete-orphan")
    activated_checks = relationship("CheckActivation", back_populates="user", cascade="all, delete-orphan")
    paid_invoices = relationship("InvoicePayment", back_populates="payer", cascade="all, delete-orphan")

    notification_settings = relationship("NotificationSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    webhook_endpoints = relationship("WebhookEndpoint", back_populates="user", cascade="all, delete-orphan")
    exchanges = relationship("Exchange", back_populates="user", cascade="all, delete-orphan")
    exchange_limits = relationship("ExchangeLimit", back_populates="user", cascade="all, delete-orphan")
    blockchain_addresses = relationship("BlockchainAddress", back_populates="user", cascade="all, delete-orphan")
    blockchain_transactions = relationship("BlockchainTransaction", back_populates="user", cascade="all, delete-orphan")
    withdrawal_requests = relationship("WithdrawalRequest", foreign_keys="WithdrawalRequest.user_id", back_populates="user", cascade="all, delete-orphan")
    deposit_addresses = relationship("DepositAddress", back_populates="user", cascade="all, delete-orphan")
    api_applications = relationship("ApiApplication", back_populates="owner", cascade="all, delete-orphan")
    admin_profile = relationship("AdminUser", back_populates="user", uselist=False, cascade="all, delete-orphan")
    address_book_entries = relationship("AddressBookEntry", back_populates="user", cascade="all, delete-orphan")

    user_settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    referral_stats = relationship("ReferralStats", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"

    @property
    def full_name(self) -> str:
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) or self.username or f"User {self.telegram_id}"

    @property
    def display_name(self) -> str:
        if self.username:
            return f"@{self.username}"
        return self.full_name

    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    def is_blocked(self) -> bool:
        if self.status == UserStatus.BLOCKED:
            return True

        if self.blocked_until and self.blocked_until > datetime.utcnow():
            return True

        return False

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def is_moderator(self) -> bool:
        return self.role in [UserRole.ADMIN, UserRole.MODERATOR]

    def can_create_api_key(self) -> bool:
        return self.is_verified and self.is_active()

    def update_activity(self):
        self.last_activity_at = datetime.utcnow()

    def block(self, reason: str = None, until: datetime = None):
        self.status = UserStatus.BLOCKED
        self.blocked_at = datetime.utcnow()
        self.blocked_reason = reason
        self.blocked_until = until

    def unblock(self):
        self.status = UserStatus.ACTIVE
        self.blocked_at = None
        self.blocked_reason = None
        self.blocked_until = None

    def verify(self):
        self.is_verified = True

    def set_premium(self, premium: bool = True):
        self.is_premium = premium

    def generate_referral_code(self) -> str:
        import secrets
        import string

        if not self.referral_code:
            alphabet = string.ascii_uppercase + string.digits
            code = ''.join(secrets.choice(alphabet) for _ in range(8))
            self.referral_code = f"REF{code}"

        return self.referral_code

    def generate_p2p_nickname(self) -> str:
        if not self.p2p_nickname:
            import random
            first_names = ["John", "Peter", "Michael", "David", "Chris", "Alex", "Ben"]
            last_names = ["Smith", "Jones", "Williams", "Brown", "Davis", "Miller", "Wilson"]
            self.p2p_nickname = f"{random.choice(first_names)} {random.choice(last_names)}"
        return self.p2p_nickname

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "display_name": self.display_name,
            "p2p_nickname": self.p2p_nickname,
            "language_code": self.language_code,
            "timezone": self.timezone,
            "status": self.status.value,
            "role": self.role.value,
            "is_verified": self.is_verified,
            "is_premium": self.is_premium,
            "notifications_enabled": self.notifications_enabled,
            "email": self.email,
            "phone": self.phone,
            "total_transactions": self.total_transactions,
            "total_volume_usd": self.total_volume_usd,
            "referral_code": self.referral_code,
            "referrals_count": self.referrals_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
        }
