from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from app.models.base import Base


class AddressBookEntry(Base):
    __tablename__ = "address_book_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    network = Column(String(50), nullable=False)
    currency = Column(String(20), nullable=False)

    description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="address_book_entries")

    __table_args__ = (
        Index('idx_address_book_user_network', 'user_id', 'network'),
        Index('idx_address_book_user_currency', 'user_id', 'currency'),
        Index('idx_address_book_address', 'address'),
    )

    def __repr__(self):
        return f"<AddressBookEntry(id={self.id}, name={self.name}, network={self.network}, address={self.address[:10]}...)>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "address": self.address,
            "network": self.network,
            "currency": self.currency,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }

    @property
    def display_address(self) -> str:
        if len(self.address) > 16:
            return f"{self.address[:8]}...{self.address[-8:]}"
        return self.address

    def update_last_used(self):
        self.last_used_at = datetime.utcnow()
