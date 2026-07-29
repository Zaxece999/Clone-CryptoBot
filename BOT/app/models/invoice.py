from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base
import secrets
import uuid
from enum import Enum
from datetime import datetime, timedelta

class InvoiceType(Enum):
    STANDARD = "standard"
    RECURRING = "recurring"

class InvoiceStatus(Enum):
    ACTIVE = "active"
    PAID = "paid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_code = Column(String(10), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invoice_type = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    allow_anonymous = Column(Boolean, default=True)
    allow_comments = Column(Boolean, default=True)
    hidden_message = Column(Boolean, default=False)

    description = Column(Text)

    user = relationship("User", back_populates="created_invoices", foreign_keys=[user_id])
    creator = relationship("User", back_populates="created_invoices", foreign_keys=[creator_id])
    payments = relationship("InvoicePayment", back_populates="invoice", cascade="all, delete-orphan")

    @classmethod
    def generate_invoice_code(cls):
        return f"IV{secrets.token_hex(4).upper()}"

class InvoicePayment(Base):
    __tablename__ = "invoice_payments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    invoice_id = Column(String(36), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    invoice = relationship("Invoice", back_populates="payments")

    payer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    payer = relationship("User", back_populates="paid_invoices")

    amount_paid = Column(String(50), nullable=False)
    currency = Column(String(10), nullable=False)

    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=True)
    transaction = relationship("Transaction")

    payment_method = Column(String(50), nullable=True)
    payment_source = Column(String(50), nullable=True)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    extra_data = Column(Text, nullable=True)

    paid_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<InvoicePayment(id={self.id}, invoice_id={self.invoice_id}, amount={self.amount_paid})>"


def add_invoice_relationships():
    from app.models.user import User

    User.invoices = relationship(
        "Invoice",
        foreign_keys="Invoice.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    User.created_invoices = relationship(
        "Invoice",
        foreign_keys="Invoice.creator_id",
        back_populates="creator",
        cascade="all, delete-orphan"
    )

    User.paid_invoices = relationship(
        "InvoicePayment",
        back_populates="payer"
    )
