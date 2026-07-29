from sqlalchemy import Column, BigInteger, String, DateTime, Text, Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from decimal import Decimal
import enum
import uuid

from app.models.base import Base


class WalletStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    currency = Column(String(20), nullable=False, index=True)
    network = Column(String(20), nullable=False, index=True)

    balance = Column(String(50), default="0", nullable=False)
    frozen_balance = Column(String(50), default="0", nullable=False)

    address = Column(String(255), nullable=False, unique=True, index=True)
    private_key_encrypted = Column(Text, nullable=False)

    status = Column(Enum(WalletStatus), default=WalletStatus.ACTIVE, nullable=False)
    is_default = Column(String(10), default="false", nullable=False)

    total_received = Column(String(50), default="0", nullable=False)
    total_sent = Column(String(50), default="0", nullable=False)
    transactions_count = Column(BigInteger, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_transaction_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="wallets")
    transactions = relationship("Transaction", back_populates="wallet", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_wallet_user_currency_network', 'user_id', 'currency', 'network', unique=True),
        Index('idx_wallet_currency_status', 'currency', 'status'),
        Index('idx_wallet_network', 'network'),
    )

    def __repr__(self):
        return f"<Wallet(id={self.id}, user_id={self.user_id}, currency={self.currency}, network={self.network}, balance={self.balance})>"

    @property
    def available_balance(self) -> str:
        from decimal import Decimal

        total = Decimal(self.balance)
        frozen = Decimal(self.frozen_balance)
        available = total - frozen

        return str(max(available, Decimal('0')))

    @property
    def display_address(self) -> str:
        if len(self.address) > 16:
            return f"{self.address[:8]}...{self.address[-8:]}"
        return self.address

    def is_active(self) -> bool:
        return self.status == WalletStatus.ACTIVE

    def get_network_display_name(self) -> str:
        network_names = {
            "TON": "TON",
            "TRC20": "TRC20",
            "ERC20": "ERC20",
            "BEP20": "BEP20",
            "SPL": "SPL",
            "BTC": "BTC",
            "LTC": "LTC",
            "DOGE": "DOGE"
        }
        return network_names.get(self.network, self.network)

    def get_full_currency_name(self) -> str:
        if self.currency in ["USDT", "USDC"] and self.network != self.currency:
            return f"{self.currency} ({self.get_network_display_name()})"
        return self.currency

    def add_balance(self, amount: str) -> None:
        from decimal import Decimal

        current_balance = Decimal(self.balance)
        add_amount = Decimal(amount)
        new_balance = current_balance + add_amount

        self.balance = str(new_balance)
        self.total_received = str(Decimal(self.total_received) + add_amount)

    def subtract_balance(self, amount: str) -> bool:
        from decimal import Decimal

        current_balance = Decimal(self.balance)
        subtract_amount = Decimal(amount)

        if current_balance >= subtract_amount:
            new_balance = current_balance - subtract_amount
            self.balance = str(new_balance)
            self.total_sent = str(Decimal(self.total_sent) + subtract_amount)
            return True

        return False

    def freeze_balance(self, amount: str) -> bool:
        from decimal import Decimal

        available = Decimal(self.available_balance)
        freeze_amount = Decimal(amount)

        if available >= freeze_amount:
            current_frozen = Decimal(self.frozen_balance)
            self.frozen_balance = str(current_frozen + freeze_amount)
            return True

        return False

    def unfreeze_balance(self, amount: str) -> bool:
        from decimal import Decimal

        current_frozen = Decimal(self.frozen_balance)
        unfreeze_amount = Decimal(amount)

        if current_frozen >= unfreeze_amount:
            self.frozen_balance = str(current_frozen - unfreeze_amount)
            return True

        return False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "currency": self.currency,
            "network": self.network,
            "balance": self.balance,
            "frozen_balance": self.frozen_balance,
            "available_balance": self.available_balance,
            "address": self.address,
            "display_address": self.display_address,
            "status": self.status.value,
            "is_default": self.is_default == "true",
            "total_received": self.total_received,
            "total_sent": self.total_sent,
            "transactions_count": self.transactions_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_transaction_at": self.last_transaction_at.isoformat() if self.last_transaction_at else None,
        }


class WalletBalance(Base):
    __tablename__ = "wallet_balances"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    currency = Column(String(20), nullable=False, index=True)

    balance = Column(String(50), default="0", nullable=False)
    frozen_balance = Column(String(50), default="0", nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="wallet_balances")

    __table_args__ = (
        Index('idx_wallet_balance_user_currency', 'user_id', 'currency', unique=True),
    )

    def __repr__(self):
        return f"<WalletBalance(id={self.id}, user_id={self.user_id}, currency={self.currency}, balance={self.balance})>"

    @property
    def balance_decimal(self) -> Decimal:
        from decimal import Decimal
        return Decimal(self.balance)

    @property
    def frozen_balance_decimal(self) -> Decimal:
        from decimal import Decimal
        return Decimal(self.frozen_balance)

    @property
    def available_balance(self) -> Decimal:
        from decimal import Decimal

        total = Decimal(self.balance)
        frozen = Decimal(self.frozen_balance)
        available = total - frozen

        return max(available, Decimal('0'))

    def add_balance(self, amount: Decimal) -> None:
        from decimal import Decimal

        current_balance = Decimal(self.balance)
        new_balance = current_balance + amount
        self.balance = str(new_balance)

    def subtract_balance(self, amount: Decimal) -> bool:
        from decimal import Decimal

        current_balance = Decimal(self.balance)

        if current_balance >= amount:
            new_balance = current_balance - amount
            self.balance = str(new_balance)
            return True

        return False

    def freeze_balance(self, amount: Decimal) -> bool:
        from decimal import Decimal

        available = self.available_balance

        if available >= amount:
            current_frozen = Decimal(self.frozen_balance)
            self.frozen_balance = str(current_frozen + amount)
            return True

        return False

    def unfreeze_balance(self, amount: Decimal) -> bool:
        from decimal import Decimal

        current_frozen = Decimal(self.frozen_balance)

        if current_frozen >= amount:
            self.frozen_balance = str(current_frozen - amount)
            return True

        return False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "currency": self.currency,
            "balance": self.balance,
            "frozen_balance": self.frozen_balance,
            "available_balance": str(self.available_balance),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
