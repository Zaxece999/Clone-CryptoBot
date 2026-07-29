from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from app.models.base import Base


class AdminRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"
    SUPPORT = "support"
    ANALYST = "analyst"


class AdminPermission(str, Enum):
    USER_VIEW = "user_view"
    USER_EDIT = "user_edit"
    USER_BAN = "user_ban"
    USER_DELETE = "user_delete"

    FINANCE_VIEW = "finance_view"
    FINANCE_EDIT = "finance_edit"
    WALLET_MANAGE = "wallet_manage"
    TRANSACTION_MANAGE = "transaction_manage"

    SYSTEM_CONFIG = "system_config"
    SYSTEM_MAINTENANCE = "system_maintenance"
    SYSTEM_LOGS = "system_logs"

    CONTENT_MANAGE = "content_manage"
    ANNOUNCEMENT_MANAGE = "announcement_manage"

    ANALYTICS_VIEW = "analytics_view"
    REPORTS_GENERATE = "reports_generate"

    SUPPORT_TICKETS = "support_tickets"
    SUPPORT_CHAT = "support_chat"


class ActionType(str, Enum):
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_BANNED = "user_banned"
    USER_UNBANNED = "user_unbanned"
    USER_DELETED = "user_deleted"

    TRANSACTION_CREATED = "transaction_created"
    TRANSACTION_CANCELLED = "transaction_cancelled"
    WITHDRAWAL_APPROVED = "withdrawal_approved"
    WITHDRAWAL_REJECTED = "withdrawal_rejected"

    SYSTEM_CONFIG_CHANGED = "system_config_changed"
    MAINTENANCE_STARTED = "maintenance_started"
    MAINTENANCE_ENDED = "maintenance_ended"

    ANNOUNCEMENT_CREATED = "announcement_created"
    ANNOUNCEMENT_UPDATED = "announcement_updated"
    ANNOUNCEMENT_DELETED = "announcement_deleted"


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    role = Column(SQLEnum(AdminRole), nullable=False, index=True)
    permissions = Column(JSON, nullable=False, default=list)

    is_active = Column(Boolean, default=True, nullable=False)
    is_super_admin = Column(Boolean, default=False, nullable=False)

    created_by = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    last_login_at = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="admin_profile")
    created_by_admin = relationship("AdminUser", remote_side=[id])
    action_logs = relationship("AdminActionLog", back_populates="admin_user")

    def __repr__(self):
        return f"<AdminUser(id={self.id}, user_id={self.user_id}, role={self.role})>"

    def has_permission(self, permission: AdminPermission) -> bool:
        if self.is_super_admin:
            return True
        return permission.value in self.permissions

    def has_any_permission(self, permissions: list[AdminPermission]) -> bool:
        if self.is_super_admin:
            return True
        return any(perm.value in self.permissions for perm in permissions)


class AdminActionLog(Base):
    __tablename__ = "admin_action_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(Integer, ForeignKey("admin_users.id"), nullable=False, index=True)

    action_type = Column(SQLEnum(ActionType), nullable=False, index=True)
    description = Column(Text, nullable=False)

    target_type = Column(String(50), nullable=True)
    target_id = Column(String(100), nullable=True)

    old_data = Column(JSON, nullable=True)
    new_data = Column(JSON, nullable=True)
    extra_data = Column(JSON, nullable=True)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    admin_user = relationship("AdminUser", back_populates="action_logs")

    def __repr__(self):
        return f"<AdminActionLog(id={self.id}, action_type={self.action_type}, admin_user_id={self.admin_user_id})>"


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)

    key = Column(String(100), nullable=False, unique=True, index=True)
    value = Column(JSON, nullable=False)

    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, index=True)
    is_public = Column(Boolean, default=False, nullable=False)

    value_type = Column(String(20), nullable=False)
    validation_rules = Column(JSON, nullable=True)

    updated_by = Column(Integer, ForeignKey("admin_users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    updated_by_admin = relationship("AdminUser")

    def __repr__(self):
        return f"<SystemConfig(id={self.id}, key={self.key})>"


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    type = Column(String(50), nullable=False, index=True)
    priority = Column(String(20), nullable=False, default="normal")

    is_published = Column(Boolean, default=False, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)

    published_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    target_audience = Column(JSON, nullable=True)

    views_count = Column(Integer, default=0, nullable=False)
    clicks_count = Column(Integer, default=0, nullable=False)

    created_by = Column(Integer, ForeignKey("admin_users.id"), nullable=False)
    updated_by = Column(Integer, ForeignKey("admin_users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    created_by_admin = relationship("AdminUser", foreign_keys=[created_by])
    updated_by_admin = relationship("AdminUser", foreign_keys=[updated_by])

    def __repr__(self):
        return f"<Announcement(id={self.id}, title={self.title[:50]})>"

    @property
    def is_active(self) -> bool:
        if not self.is_published:
            return False

        now = datetime.utcnow()

        if self.published_at and self.published_at > now:
            return False

        if self.expires_at and self.expires_at < now:
            return False

        return True


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    status = Column(String(20), nullable=False, default="open", index=True)
    priority = Column(String(20), nullable=False, default="normal")
    category = Column(String(50), nullable=False, index=True)

    assigned_to = Column(Integer, ForeignKey("admin_users.id"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")
    assigned_admin = relationship("AdminUser")
    messages = relationship("SupportMessage", back_populates="ticket", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SupportTicket(id={self.id}, subject={self.subject[:50]}, status={self.status})>"


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    admin_user_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)

    message = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False, nullable=False)

    attachments = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ticket = relationship("SupportTicket", back_populates="messages")
    user = relationship("User")
    admin_user = relationship("AdminUser")

    def __repr__(self):
        return f"<SupportMessage(id={self.id}, ticket_id={self.ticket_id})>"

    @property
    def author_name(self) -> str:
        if self.admin_user_id:
            return f"Admin #{self.admin_user_id}"
        elif self.user_id:
            return f"User #{self.user_id}"
        else:
            return "System"


class SystemStats(Base):
    __tablename__ = "system_stats"

    id = Column(Integer, primary_key=True, index=True)

    date = Column(DateTime(timezone=True), nullable=False, index=True)

    total_users = Column(Integer, default=0, nullable=False)
    new_users = Column(Integer, default=0, nullable=False)
    active_users = Column(Integer, default=0, nullable=False)

    total_transactions = Column(Integer, default=0, nullable=False)
    transaction_volume = Column(Numeric(precision=36, scale=18), default=0, nullable=False)

    deposits_count = Column(Integer, default=0, nullable=False)
    deposits_volume = Column(Numeric(precision=36, scale=18), default=0, nullable=False)
    withdrawals_count = Column(Integer, default=0, nullable=False)
    withdrawals_volume = Column(Numeric(precision=36, scale=18), default=0, nullable=False)

    p2p_orders_count = Column(Integer, default=0, nullable=False)
    p2p_volume = Column(Numeric(precision=36, scale=18), default=0, nullable=False)

    exchanges_count = Column(Integer, default=0, nullable=False)
    exchange_volume = Column(Numeric(precision=36, scale=18), default=0, nullable=False)

    api_requests_count = Column(Integer, default=0, nullable=False)
    api_errors_count = Column(Integer, default=0, nullable=False)

    support_tickets_count = Column(Integer, default=0, nullable=False)
    support_resolved_count = Column(Integer, default=0, nullable=False)

    additional_data = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<SystemStats(id={self.id}, date={self.date.date()})>"


class MaintenanceMode(Base):
    __tablename__ = "maintenance_mode"

    id = Column(Integer, primary_key=True, index=True)

    is_enabled = Column(Boolean, default=False, nullable=False)

    title = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    estimated_end_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    allowed_users = Column(JSON, nullable=True)
    allowed_ips = Column(JSON, nullable=True)

    created_by = Column(Integer, ForeignKey("admin_users.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    created_by_admin = relationship("AdminUser")

    def __repr__(self):
        return f"<MaintenanceMode(id={self.id}, is_enabled={self.is_enabled})>"
