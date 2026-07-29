from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.base import Base


class CheckStatus(str, Enum):
    ACTIVE = "active"
    ACTIVATED = "activated"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class CheckType(str, Enum):
    PERSONAL = "personal"
    MULTI_USE = "multi_use"
    ONE_TIME = "one_time"


class Check(Base):
    __tablename__ = "checks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    check_id = Column(String(20), unique=True, nullable=False, index=True)
    activation_code = Column(String(15), unique=True, nullable=False, index=True)

    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_checks")

    activator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    activator = relationship("User", foreign_keys=[activator_id])

    currency = Column(String(10), nullable=False, index=True)
    amount = Column(String(50), nullable=False)
    password = Column(String(255), nullable=True)

    type = Column(String(20), nullable=False, default=CheckType.ONE_TIME.value)
    status = Column(String(20), nullable=False, default=CheckStatus.ACTIVE.value, index=True)

    max_activations = Column(Integer, nullable=True)
    current_activations = Column(Integer, nullable=False, default=0)

    target_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_user = relationship("User", foreign_keys=[target_user_id])
    target_username = Column(String(50), nullable=True)

    expires_at = Column(DateTime(timezone=True), nullable=True)

    description = Column(Text, nullable=True)
    comment = Column(Text, nullable=True)

    extra_data = Column(Text, nullable=True)

    notify_on_activation = Column(Boolean, nullable=False, default=True)

    activated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    activations = relationship("CheckActivation", back_populates="check", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Check(id={self.id}, check_id={self.check_id}, amount={self.amount}, currency={self.currency})>"

    restrictions = Column(Text, nullable=True)
    image_file_id = Column(String(255), nullable=True)
    is_gift = Column(Boolean, nullable=False, default=False)

    @property
    def is_active(self) -> bool:
        if self.status != CheckStatus.ACTIVE:
            return False

        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False

        if self.max_activations and self.current_activations >= self.max_activations:
            return False

        return True

    @property
    def is_expired(self) -> bool:
        return self.expires_at and datetime.utcnow() > self.expires_at

    def can_be_activated_by(self, user_id: int, username: str = None) -> bool:
        if not self.is_active:
            return False

        if self.creator_id == user_id:
            return False

        if self.type == CheckType.PERSONAL:
            if self.target_user_id and self.target_user_id != user_id:
                return False
            elif self.target_username and username and self.target_username.lower() != username.lower():
                return False

        if self.type == CheckType.ONE_TIME and self.current_activations > 0:
            return False

        return True

    def activate(self, user_id: int) -> bool:
        if not self.can_be_activated_by(user_id):
            return False

        self.activator_id = user_id
        self.current_activations += 1
        self.activated_at = datetime.utcnow()

        if self.type == CheckType.ONE_TIME or (
            self.max_activations and self.current_activations >= self.max_activations
        ):
            self.status = CheckStatus.ACTIVATED

        return True

    def cancel(self) -> bool:
        if self.status not in [CheckStatus.ACTIVE]:
            return False

        self.status = CheckStatus.CANCELLED
        return True

    def expire(self) -> bool:
        if self.status not in [CheckStatus.ACTIVE]:
            return False

        self.status = CheckStatus.EXPIRED
        return True

    def get_remaining_activations(self) -> int:
        if not self.max_activations:
            return float('inf')

        return max(0, self.max_activations - self.current_activations)

    def get_expiry_info(self) -> dict:
        if not self.expires_at:
            return {"has_expiry": False}

        now = datetime.utcnow()
        if now > self.expires_at:
            return {
                "has_expiry": True,
                "is_expired": True,
                "expires_at": self.expires_at
            }

        time_left = self.expires_at - now
        return {
            "has_expiry": True,
            "is_expired": False,
            "expires_at": self.expires_at,
            "time_left_seconds": int(time_left.total_seconds()),
            "time_left_human": self._format_time_left(time_left)
        }

    def _format_time_left(self, time_left: timedelta) -> str:
        days = time_left.days
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        if days > 0:
            return f"{days}д {hours}ч {minutes}м"
        elif hours > 0:
            return f"{hours}ч {minutes}м"
        else:
            return f"{minutes}м"

    @classmethod
    def generate_check_id(cls) -> str:
        import random
        import string

        chars = string.ascii_uppercase + string.digits
        chars = chars.replace('0', '').replace('O', '').replace('I', '').replace('1', '')

        return ''.join(random.choice(chars) for _ in range(8))

    @classmethod
    def generate_activation_code(cls) -> str:
        import random

        return ''.join(random.choice('0123456789') for _ in range(15))


class CheckActivation(Base):
    __tablename__ = "check_activations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    check_id = Column(String(36), ForeignKey("checks.id", ondelete="CASCADE"), nullable=False)
    check = relationship("Check", back_populates="activations")

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="activated_checks")

    amount_received = Column(String(50), nullable=False)
    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=True)
    transaction = relationship("Transaction")

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    activated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<CheckActivation(id={self.id}, check_id={self.check_id}, user_id={self.user_id})>"


def add_check_relationships():
    from app.models.user import User

    User.created_checks = relationship(
        "Check",
        foreign_keys="Check.creator_id",
        back_populates="creator",
        cascade="all, delete-orphan"
    )

    User.activated_checks = relationship(
        "CheckActivation",
        back_populates="user"
    )
