from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, ForeignKey, Numeric, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.base import Base


class P2POrderType(str, Enum):
    BUY = "buy"
    SELL = "sell"


class P2POrderStatus(str, Enum):
    ACTIVE = "active"
    MATCHED = "matched"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"
    EXPIRED = "expired"


class P2PPaymentMethod(str, Enum):
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    PAYPAL = "paypal"
    WEBMONEY = "webmoney"
    QIWI = "qiwi"
    YANDEX_MONEY = "yandex_money"
    SBERBANK = "sberbank"
    TINKOFF = "tinkoff"
    OTHER = "other"
    ALFA_BANK = "alfa_bank"
    VTB = "vtb"
    RAIFFEISEN = "raiffeisen"
    ROSBANK = "rosbank"
    GAZPROMBANK = "gazprombank"
    OTKRITIE = "otkritie"
    POCHTA_BANK = "pochta_bank"
    SOVCOMBANK = "sovcombank"
    PROMSVYAZBANK = "promsvyazbank"
    MTS_BANK = "mts_bank"
    HOME_CREDIT = "home_credit"
    RENAISSANCE = "renaissance"
    AK_BARS = "ak_bars"
    URALSIB = "uralsib"
    TOCHKA = "tochka"
    MODULBANK = "modulbank"
    SPB_BANK = "spb_bank"
    MKB = "mkb"
    BCS_BANK = "bcs_bank"
    ROSGOSSTRAKH = "rosgosstrakh"
    UNICREDIT = "unicredit"
    SINARA = "sinara"
    BANK_OF_AMERICA = "bank_of_america"
    CHASE = "chase"
    WELLS_FARGO = "wells_fargo"
    CITI = "citi"
    CAPITAL_ONE = "capital_one"
    US_BANK = "us_bank"
    PNC = "pnc"
    TD_BANK = "td_bank"
    HSBC_US = "hsbc_us"
    SANTANDER_US = "santander_us"
    DEUTSCHE_BANK = "deutsche_bank"
    COMMERZBANK = "commerzbank"
    ING = "ing"
    SANTANDER = "santander"
    BNP_PARIBAS = "bnp_paribas"
    SOCIETE_GENERALE = "societe_generale"
    CREDIT_AGRICOLE = "credit_agricole"
    ABN_AMRO = "abn_amro"
    KBC = "kbc"
    CAIXABANK = "caixabank"
    INTESA_SANPAOLO = "intesa_sanpaolo"
    UBS = "ubs"
    ERSTE = "erste"
    N26 = "n26"
    BUNQ = "bunq"
    REVOLUT = "revolut"
    BARCLAYS = "barclays"
    HSBC = "hsbc"
    LLOYDS = "lloyds"
    NATWEST = "natwest"
    TSB = "tsb"
    HALIFAX = "halifax"
    VIRGIN_MONEY = "virgin_money"
    NATIONWIDE = "nationwide"
    METRO_BANK = "metro_bank"
    MONZO = "monzo"
    STARLING = "starling"
    ICBC = "icbc"
    BANK_OF_CHINA = "bank_of_china"
    CCB = "ccb"
    ABC = "abc"
    CHINA_MERCHANTS_BANK = "china_merchants_bank"
    CIS_BANKS = "cis_banks"
    GEORGIAN_BANKS = "georgian_banks"
    ARMENIAN_BANKS = "armenian_banks"
    TURKISH_BANKS = "turkish_banks"
    THAI_BANKS = "thai_banks"
    INDONESIAN_BANKS = "indonesian_banks"
    MALAYSIAN_BANKS = "malaysian_banks"
    VIETNAMESE_BANKS = "vietnamese_banks"
    PHILIPPINE_BANKS = "philippine_banks"
    INDIAN_BANKS = "indian_banks"
    BRAZILIAN_BANKS = "brazilian_banks"
    MEXICAN_BANKS = "mexican_banks"
    NIGERIAN_BANKS = "nigerian_banks"
    SOUTH_AFRICAN_BANKS = "south_african_banks"
    JAPANESE_BANKS = "japanese_banks"
    KOREAN_BANKS = "korean_banks"
    AUSTRALIAN_BANKS = "australian_banks"
    CANADIAN_BANKS = "canadian_banks"
    MONOBANK = "monobank"
    PRIVATBANK = "privatbank"
    OSCHADBANK = "oschadbank"
    PUMB = "pumb"
    A_BANK = "a_bank"
    UKRGASBANK = "ukrgasbank"
    UKRSIBBANK = "ukrsibbank"
    KREDOBANK = "kredobank"
    IDEA_BANK = "idea_bank"
    OTP_BANK = "otp_bank"
    PIVDENNYI = "pivdennyi"
    MTB_BANK = "mtb_bank"
    BANK_VOSTOK = "bank_vostok"
    SENSE_BANK = "sense_bank"


class P2POrder(Base):
    __tablename__ = "p2p_orders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(20), unique=True, nullable=False, index=True)

    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    creator = relationship("User", foreign_keys=[creator_id], back_populates="p2p_orders")

    type = Column(String(10), nullable=False, index=True)
    status = Column(String(20), nullable=False, default=P2POrderStatus.ACTIVE.value, index=True)

    crypto_currency = Column(String(10), nullable=False, index=True)
    crypto_amount = Column(String(50), nullable=False)

    fiat_currency = Column(String(10), nullable=False, index=True)
    fiat_amount = Column(String(50), nullable=False)
    price_per_unit = Column(String(50), nullable=False)

    min_amount = Column(String(50), nullable=True)
    max_amount = Column(String(50), nullable=True)

    payment_methods = Column(Text, nullable=False)
    payment_details = Column(Text, nullable=True)

    terms = Column(Text, nullable=True)
    auto_reply = Column(Text, nullable=True)

    payment_timeout_minutes = Column(Integer, nullable=False, default=30)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    min_trades = Column(Integer, nullable=False, default=0)
    min_completion_rate = Column(Numeric(5, 2), nullable=False, default=0)

    country = Column(String(10), nullable=True)
    city = Column(String(100), nullable=True)

    views_count = Column(Integer, nullable=False, default=0)
    matches_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    trades = relationship("P2PTrade", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<P2POrder(id={self.id}, order_id={self.order_id}, type={self.type}, crypto={self.crypto_currency})>"

    @property
    def is_active(self) -> bool:
        if self.status != P2POrderStatus.ACTIVE:
            return False

        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False

        return True

    @property
    def is_expired(self) -> bool:
        return self.expires_at and datetime.utcnow() > self.expires_at

    def can_match_with_user(self, user_id: int, user_stats: dict) -> bool:
        if not self.is_active:
            return False

        if self.creator_id == user_id:
            return False

        if user_stats.get("trades_count", 0) < self.min_trades:
            return False

        if user_stats.get("completion_rate", 0) < float(self.min_completion_rate):
            return False

        return True

    def get_payment_methods_list(self) -> list:
        import json
        try:
            return json.loads(self.payment_methods)
        except:
            return []

    def set_payment_methods_list(self, methods: list):
        import json
        self.payment_methods = json.dumps(methods)

    def calculate_fiat_amount(self, crypto_amount: str) -> str:
        crypto_decimal = Decimal(crypto_amount)
        price_decimal = Decimal(self.price_per_unit)
        return str(crypto_decimal * price_decimal)

    def calculate_crypto_amount(self, fiat_amount: str) -> str:
        fiat_decimal = Decimal(fiat_amount)
        price_decimal = Decimal(self.price_per_unit)
        return str(fiat_decimal / price_decimal)

    @classmethod
    def generate_order_id(cls) -> str:
        import random
        import string

        chars = string.ascii_uppercase + string.digits
        chars = chars.replace('0', '').replace('O', '').replace('I', '').replace('1', '')

        return 'P2P' + ''.join(random.choice(chars) for _ in range(5))


class P2PTrade(Base):
    __tablename__ = "p2p_trades"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trade_id = Column(String(20), unique=True, nullable=False, index=True)

    order_id = Column(String(36), ForeignKey("p2p_orders.id", ondelete="CASCADE"), nullable=False)
    order = relationship("P2POrder", back_populates="trades")

    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    buyer = relationship("User", foreign_keys=[buyer_id])

    seller_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    seller = relationship("User", foreign_keys=[seller_id])

    crypto_currency = Column(String(10), nullable=False)
    crypto_amount = Column(String(50), nullable=False)
    fiat_currency = Column(String(10), nullable=False)
    fiat_amount = Column(String(50), nullable=False)
    price_per_unit = Column(String(50), nullable=False)

    status = Column(String(20), nullable=False, default=P2POrderStatus.MATCHED.value, index=True)

    payment_method = Column(String(50), nullable=False)
    payment_details = Column(Text, nullable=True)

    payment_timeout_at = Column(DateTime(timezone=True), nullable=True)

    payment_confirmed_by_buyer = Column(Boolean, nullable=False, default=False)
    payment_confirmed_by_seller = Column(Boolean, nullable=False, default=False)
    crypto_released = Column(Boolean, nullable=False, default=False)

    chat_messages = relationship("P2PChatMessage", back_populates="trade", cascade="all, delete-orphan")

    dispute_reason = Column(Text, nullable=True)
    dispute_created_at = Column(DateTime(timezone=True), nullable=True)
    dispute_resolved_at = Column(DateTime(timezone=True), nullable=True)
    dispute_resolution = Column(Text, nullable=True)

    buyer_rating = Column(Integer, nullable=True)
    seller_rating = Column(Integer, nullable=True)
    buyer_feedback = Column(Text, nullable=True)
    seller_feedback = Column(Text, nullable=True)

    matched_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<P2PTrade(id={self.id}, trade_id={self.trade_id}, status={self.status})>"

    @property
    def is_payment_expired(self) -> bool:
        return self.payment_timeout_at and datetime.utcnow() > self.payment_timeout_at

    def start_trade(self):
        self.status = P2POrderStatus.IN_PROGRESS.value
        self.started_at = datetime.utcnow()

        timeout_minutes = 30
        if self.order and self.order.payment_timeout_minutes:
            timeout_minutes = self.order.payment_timeout_minutes

        self.payment_timeout_at = datetime.utcnow() + timedelta(minutes=timeout_minutes)

    def confirm_payment_by_buyer(self):
        self.payment_confirmed_by_buyer = True

    def confirm_payment_by_seller(self):
        self.payment_confirmed_by_seller = True

    def release_crypto(self):
        self.crypto_released = True
        self.status = P2POrderStatus.COMPLETED.value
        self.completed_at = datetime.utcnow()

    def cancel_trade(self, reason: str = None):
        self.status = P2POrderStatus.CANCELLED.value
        self.cancelled_at = datetime.utcnow()
        if reason:
            self.dispute_reason = reason

    def create_dispute(self, reason: str):
        self.status = P2POrderStatus.DISPUTED.value
        self.dispute_reason = reason
        self.dispute_created_at = datetime.utcnow()

    def resolve_dispute(self, resolution: str):
        self.dispute_resolution = resolution
        self.dispute_resolved_at = datetime.utcnow()

    @classmethod
    def generate_trade_id(cls) -> str:
        import random
        import string

        chars = string.ascii_uppercase + string.digits
        chars = chars.replace('0', '').replace('O', '').replace('I', '').replace('1')

        return 'TRD' + ''.join(random.choice(chars) for _ in range(5))


class P2PChatMessage(Base):
    __tablename__ = "p2p_chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    trade_id = Column(String(36), ForeignKey("p2p_trades.id", ondelete="CASCADE"), nullable=False)
    trade = relationship("P2PTrade", back_populates="chat_messages")

    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sender = relationship("User")

    message_type = Column(String(20), nullable=False, default="text")
    content = Column(Text, nullable=False)

    is_read = Column(Boolean, nullable=False, default=False)
    is_system = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<P2PChatMessage(id={self.id}, trade_id={self.trade_id}, sender_id={self.sender_id})>"


class P2PUserStats(Base):
    __tablename__ = "p2p_user_stats"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    user = relationship("User", back_populates="p2p_stats")

    total_trades = Column(Integer, nullable=False, default=0)
    completed_trades = Column(Integer, nullable=False, default=0)
    cancelled_trades = Column(Integer, nullable=False, default=0)
    disputed_trades = Column(Integer, nullable=False, default=0)

    buy_trades = Column(Integer, nullable=False, default=0)
    buy_volume_usd = Column(String(50), nullable=False, default="0")

    sell_trades = Column(Integer, nullable=False, default=0)
    sell_volume_usd = Column(String(50), nullable=False, default="0")

    average_rating = Column(Numeric(3, 2), nullable=False, default=0)
    total_ratings = Column(Integer, nullable=False, default=0)

    average_payment_time_minutes = Column(Integer, nullable=False, default=0)
    average_release_time_minutes = Column(Integer, nullable=False, default=0)

    first_trade_at = Column(DateTime(timezone=True), nullable=True)
    last_trade_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<P2PUserStats(user_id={self.user_id}, total_trades={self.total_trades})>"

    @property
    def completion_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.completed_trades / self.total_trades) * 100

    @property
    def dispute_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.disputed_trades / self.total_trades) * 100

    def update_stats_after_trade(self, trade: P2PTrade, is_buyer: bool):
        self.total_trades += 1

        if trade.status == P2POrderStatus.COMPLETED:
            self.completed_trades += 1
        elif trade.status == P2POrderStatus.CANCELLED:
            self.cancelled_trades += 1
        elif trade.status == P2POrderStatus.DISPUTED:
            self.disputed_trades += 1

        if is_buyer:
            self.buy_trades += 1
            current_volume = Decimal(self.buy_volume_usd)
            self.buy_volume_usd = str(current_volume + Decimal(trade.fiat_amount))
        else:
            self.sell_trades += 1
            current_volume = Decimal(self.sell_volume_usd)
            self.sell_volume_usd = str(current_volume + Decimal(trade.fiat_amount))

        if not self.first_trade_at:
            self.first_trade_at = trade.matched_at
        self.last_trade_at = datetime.utcnow()


def add_p2p_relationships():
    from app.models.user import User

    User.created_p2p_orders = relationship(
        "P2POrder",
        foreign_keys="P2POrder.creator_id",
        back_populates="creator",
        cascade="all, delete-orphan"
    )

    User.p2p_stats = relationship(
        "P2PUserStats",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
