from sqlalchemy import Column, BigInteger, String, DateTime, Text, Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
import uuid

from app.models.base import Base


class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    CHECK = "check"
    CHECK_CREATION = "check_creation"
    CHECK_ACTIVATION = "check_activation"
    INVOICE = "invoice"
    P2P = "p2p"
    EXCHANGE = "exchange"
    FEE = "fee"
    REFUND = "refund"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class TransactionDirection(str, enum.Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    INTERNAL = "internal"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_id = Column(String(36), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True)

    type = Column(Enum(TransactionType), nullable=False, index=True)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False, index=True)
    direction = Column(Enum(TransactionDirection), nullable=False, index=True)

    currency = Column(String(20), nullable=False, index=True)
    amount = Column(String(50), nullable=False)
    fee = Column(String(50), default="0", nullable=False)

    from_address = Column(String(255), nullable=True, index=True)
    to_address = Column(String(255), nullable=True, index=True)

    tx_hash = Column(String(255), nullable=True, unique=True, index=True)
    block_number = Column(BigInteger, nullable=True)
    confirmations = Column(BigInteger, default=0, nullable=False)
    required_confirmations = Column(BigInteger, default=1, nullable=False)

    network = Column(String(20), nullable=True)

    related_user_id = Column(Integer, nullable=True, index=True)
    related_object_type = Column(String(50), nullable=True)
    related_object_id = Column(String(36), nullable=True, index=True)

    description = Column(Text, nullable=True)
    extra_data = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="transactions")
    wallet = relationship("Wallet", back_populates="transactions")

    __table_args__ = (
        Index('idx_transaction_user_status', 'user_id', 'status'),
        Index('idx_transaction_wallet_type', 'wallet_id', 'type'),
        Index('idx_transaction_currency_status', 'currency', 'status'),
        Index('idx_transaction_created_at', 'created_at'),
        Index('idx_transaction_hash_network', 'tx_hash', 'network'),
    )

    def __repr__(self):
        return f"<Transaction(id={self.id}, type={self.type}, amount={self.amount}, status={self.status})>"

    @property
    def display_amount(self) -> str:
        from decimal import Decimal

        amount = Decimal(self.amount)

        if self.currency in ["BTC", "ETH", "LTC"]:
            return f"{amount:.8f} {self.currency}"
        elif self.currency in ["USDT", "USDC"]:
            return f"{amount:.2f} {self.currency}"
        else:
            return f"{amount:.4f} {self.currency}"

    @property
    def display_fee(self) -> str:
        from decimal import Decimal

        fee = Decimal(self.fee)
        if fee == 0:
            return "0"

        if self.currency in ["BTC", "ETH", "LTC"]:
            return f"{fee:.8f} {self.currency}"
        elif self.currency in ["USDT", "USDC"]:
            return f"{fee:.2f} {self.currency}"
        else:
            return f"{fee:.4f} {self.currency}"

    @property
    def display_hash(self) -> str:
        if not self.tx_hash:
            return ""

        if len(self.tx_hash) > 16:
            return f"{self.tx_hash[:8]}...{self.tx_hash[-8:]}"
        return self.tx_hash

    @property
    def is_confirmed(self) -> bool:
        return self.confirmations >= self.required_confirmations

    @property
    def is_pending(self) -> bool:
        return self.status == TransactionStatus.PENDING

    @property
    def is_completed(self) -> bool:
        return self.status == TransactionStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.status in [TransactionStatus.FAILED, TransactionStatus.CANCELLED, TransactionStatus.EXPIRED]

    def mark_as_processing(self):
        self.status = TransactionStatus.PROCESSING
        self.processed_at = datetime.utcnow()

    def mark_as_completed(self):
        self.status = TransactionStatus.COMPLETED
        self.confirmed_at = datetime.utcnow()

    def mark_as_failed(self, reason: str = None):
        self.status = TransactionStatus.FAILED
        if reason:
            self.description = f"{self.description or ''}\nFailed: {reason}".strip()

    def add_confirmation(self):
        self.confirmations += 1

        if self.is_confirmed and self.status == TransactionStatus.PROCESSING:
            self.mark_as_completed()

    def set_hash(self, tx_hash: str, block_number: int = None):
        self.tx_hash = tx_hash
        if block_number:
            self.block_number = block_number

        if self.status == TransactionStatus.PENDING:
            self.mark_as_processing()

    def get_explorer_url(self) -> str:
        if not self.tx_hash:
            return ""

        explorers = {
            "BTC": f"https://blockstream.info/tx/{self.tx_hash}",
            "ETH": f"https://etherscan.io/tx/{self.tx_hash}",
            "USDT_ERC20": f"https://etherscan.io/tx/{self.tx_hash}",
            "USDT_TRC20": f"https://tronscan.org/#/transaction/{self.tx_hash}",
            "USDT_BEP20": f"https://bscscan.com/tx/{self.tx_hash}",
            "LTC": f"https://blockchair.com/litecoin/transaction/{self.tx_hash}",
            "BNB": f"https://bscscan.com/tx/{self.tx_hash}",
            "TRX": f"https://tronscan.org/#/transaction/{self.tx_hash}",
            "TON": f"https://tonscan.org/tx/{self.tx_hash}",
        }

        return explorers.get(self.currency, "")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "wallet_id": self.wallet_id,
            "type": self.type.value,
            "status": self.status.value,
            "direction": self.direction.value,
            "currency": self.currency,
            "amount": self.amount,
            "display_amount": self.display_amount,
            "fee": self.fee,
            "display_fee": self.display_fee,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "tx_hash": self.tx_hash,
            "display_hash": self.display_hash,
            "block_number": self.block_number,
            "confirmations": self.confirmations,
            "required_confirmations": self.required_confirmations,
            "network": self.network,
            "related_user_id": self.related_user_id,
            "related_object_type": self.related_object_type,
            "related_object_id": self.related_object_id,
            "description": self.description,
            "explorer_url": self.get_explorer_url(),
            "is_confirmed": self.is_confirmed,
            "is_pending": self.is_pending,
            "is_completed": self.is_completed,
            "is_failed": self.is_failed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
