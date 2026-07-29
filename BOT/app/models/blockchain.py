from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
from datetime import datetime
from enum import Enum
from typing import Optional

from app.models.base import Base


class BlockchainNetwork(str, Enum):
    BITCOIN = "bitcoin"
    ETHEREUM = "ethereum"
    BINANCE_SMART_CHAIN = "bsc"
    POLYGON = "polygon"
    TRON = "tron"
    LITECOIN = "litecoin"
    DOGECOIN = "dogecoin"
    BITCOIN_CASH = "bitcoin_cash"
    DASH = "dash"
    ZCASH = "zcash"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMING = "confirming"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AddressType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    HOT_WALLET = "hot_wallet"
    COLD_WALLET = "cold_wallet"


class BlockchainAddress(Base):
    __tablename__ = "blockchain_addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    network = Column(SQLEnum(BlockchainNetwork), nullable=False, index=True)
    currency = Column(String(10), nullable=False, index=True)
    address = Column(String(255), nullable=False, unique=True, index=True)
    private_key_encrypted = Column(Text, nullable=True)
    address_type = Column(SQLEnum(AddressType), nullable=False, default=AddressType.DEPOSIT)
    is_active = Column(Boolean, default=True, nullable=False)

    derivation_path = Column(String(100), nullable=True)
    public_key = Column(Text, nullable=True)
    memo = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="blockchain_addresses")
    transactions = relationship("BlockchainTransaction", back_populates="address")

    def __repr__(self):
        return f"<BlockchainAddress(id={self.id}, network={self.network}, address={self.address[:10]}...)>"


class BlockchainTransaction(Base):
    __tablename__ = "blockchain_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    address_id = Column(Integer, ForeignKey("blockchain_addresses.id"), nullable=False, index=True)

    tx_hash = Column(String(255), nullable=False, unique=True, index=True)
    network = Column(SQLEnum(BlockchainNetwork), nullable=False, index=True)
    currency = Column(String(10), nullable=False, index=True)

    from_address = Column(String(255), nullable=False, index=True)
    to_address = Column(String(255), nullable=False, index=True)
    amount = Column(Numeric(precision=36, scale=18), nullable=False)
    fee = Column(Numeric(precision=36, scale=18), nullable=True)

    status = Column(SQLEnum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING, index=True)
    confirmations = Column(Integer, default=0, nullable=False)
    required_confirmations = Column(Integer, default=1, nullable=False)

    block_number = Column(Integer, nullable=True, index=True)
    block_hash = Column(String(255), nullable=True)
    transaction_index = Column(Integer, nullable=True)
    gas_used = Column(Integer, nullable=True)
    gas_price = Column(Numeric(precision=36, scale=18), nullable=True)
    nonce = Column(Integer, nullable=True)

    memo = Column(String(255), nullable=True)
    internal_id = Column(String(100), nullable=True, index=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    blockchain_time = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="blockchain_transactions")
    address = relationship("BlockchainAddress", back_populates="transactions")

    def __repr__(self):
        return f"<BlockchainTransaction(id={self.id}, tx_hash={self.tx_hash[:10]}..., status={self.status})>"

    @property
    def is_confirmed(self) -> bool:
        return self.confirmations >= self.required_confirmations and self.status == TransactionStatus.CONFIRMED

    @property
    def confirmation_progress(self) -> float:
        if self.required_confirmations == 0:
            return 100.0
        return min(100.0, (self.confirmations / self.required_confirmations) * 100)


class BlockchainNode(Base):
    __tablename__ = "blockchain_nodes"

    id = Column(Integer, primary_key=True, index=True)
    network = Column(SQLEnum(BlockchainNetwork), nullable=False, index=True)
    name = Column(String(100), nullable=False)

    rpc_url = Column(String(500), nullable=False)
    ws_url = Column(String(500), nullable=True)
    api_key = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    priority = Column(Integer, default=0, nullable=False)

    max_requests_per_second = Column(Integer, default=10, nullable=False)
    max_requests_per_day = Column(Integer, default=100000, nullable=False)

    total_requests = Column(Integer, default=0, nullable=False)
    failed_requests = Column(Integer, default=0, nullable=False)
    last_request_at = Column(DateTime(timezone=True), nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)
    last_error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<BlockchainNode(id={self.id}, network={self.network}, name={self.name})>"

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 100.0
        return ((self.total_requests - self.failed_requests) / self.total_requests) * 100


class TokenContract(Base):
    __tablename__ = "token_contracts"

    id = Column(Integer, primary_key=True, index=True)
    network = Column(SQLEnum(BlockchainNetwork), nullable=False, index=True)
    currency = Column(String(10), nullable=False, index=True)

    contract_address = Column(String(255), nullable=False, index=True)
    decimals = Column(Integer, nullable=False, default=18)
    name = Column(String(100), nullable=False)
    symbol = Column(String(20), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    min_confirmations = Column(Integer, default=12, nullable=False)
    min_deposit_amount = Column(Numeric(precision=36, scale=18), nullable=True)
    max_withdrawal_amount = Column(Numeric(precision=36, scale=18), nullable=True)

    contract_abi = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<TokenContract(id={self.id}, network={self.network}, symbol={self.symbol})>"


class BlockchainBlock(Base):
    __tablename__ = "blockchain_blocks"

    id = Column(Integer, primary_key=True, index=True)
    network = Column(SQLEnum(BlockchainNetwork), nullable=False, index=True)

    block_number = Column(Integer, nullable=False, index=True)
    block_hash = Column(String(255), nullable=False, unique=True, index=True)
    parent_hash = Column(String(255), nullable=True)

    timestamp = Column(DateTime(timezone=True), nullable=False)
    transaction_count = Column(Integer, default=0, nullable=False)
    size = Column(Integer, nullable=True)
    gas_used = Column(Integer, nullable=True)
    gas_limit = Column(Integer, nullable=True)

    is_processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<BlockchainBlock(id={self.id}, network={self.network}, block_number={self.block_number})>"


class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    currency = Column(String(10), nullable=False, index=True)
    network = Column(SQLEnum(BlockchainNetwork), nullable=False, index=True)
    amount = Column(Numeric(precision=36, scale=18), nullable=False)
    fee = Column(Numeric(precision=36, scale=18), nullable=False)

    to_address = Column(String(255), nullable=False)
    memo = Column(String(100), nullable=True)

    status = Column(SQLEnum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING, index=True)
    tx_hash = Column(String(255), nullable=True, index=True)

    requires_approval = Column(Boolean, default=False, nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    internal_id = Column(String(100), nullable=True, unique=True, index=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="withdrawal_requests")
    approver = relationship("User", foreign_keys=[approved_by])

    def __repr__(self):
        return f"<WithdrawalRequest(id={self.id}, user_id={self.user_id}, amount={self.amount}, status={self.status})>"


class DepositAddress(Base):
    __tablename__ = "deposit_addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    currency = Column(String(10), nullable=False, index=True)
    network = Column(SQLEnum(BlockchainNetwork), nullable=False, index=True)

    address = Column(String(255), nullable=False, unique=True, index=True)
    memo = Column(String(100), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    min_deposit_amount = Column(Numeric(precision=36, scale=18), nullable=True)

    total_deposits = Column(Integer, default=0, nullable=False)
    total_amount = Column(Numeric(precision=36, scale=18), default=0, nullable=False)
    last_deposit_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="deposit_addresses")

    def __repr__(self):
        return f"<DepositAddress(id={self.id}, user_id={self.user_id}, currency={self.currency}, address={self.address[:10]}...)>"
