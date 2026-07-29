from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum

from app.models.user import UserRole, UserStatus


class UserBase(BaseModel):
    username: Optional[str] = Field(None, max_length=255)
    first_name: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    language_code: str = Field("ru", max_length=10)
    timezone: str = Field("UTC", max_length=50)


class UserCreate(UserBase):
    telegram_id: int = Field(..., gt=0)
    is_premium: bool = False


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=255)
    first_name: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    language_code: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    telegram_id: int
    status: UserStatus
    role: UserRole
    is_verified: bool
    is_premium: bool
    notifications_enabled: bool
    email_notifications: bool
    sms_notifications: bool
    email: Optional[str]
    phone: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    total_transactions: int
    total_volume_usd: str
    referral_code: Optional[str]
    referrals_count: int
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime

    class Config:
        from_attributes = True


class UserPublic(BaseModel):
    id: int
    username: Optional[str]
    first_name: Optional[str]
    display_name: str
    is_verified: bool
    is_premium: bool
    total_transactions: int
    referrals_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserStats(BaseModel):
    total_transactions: int
    total_volume_usd: str
    referrals_count: int
    wallets_count: int
    checks_created: int
    invoices_created: int
    p2p_orders_count: int
    subscriptions_count: int


class TelegramAuthData(BaseModel):
    telegram_id: int = Field(..., gt=0)
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = "ru"
    is_premium: bool = False


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    refresh_token: str


class PinCodeSet(BaseModel):
    pin_code: str = Field(..., min_length=4, max_length=6)

    @validator('pin_code')
    def validate_pin_code(cls, v):
        if not v.isdigit():
            raise ValueError('PIN code must contain only digits')
        return v


class PinCodeVerify(BaseModel):
    pin_code: str = Field(..., min_length=4, max_length=6)


class UserBlock(BaseModel):
    reason: Optional[str] = None
    until: Optional[datetime] = None


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserStatusUpdate(BaseModel):
    status: UserStatus


class ReferralInfo(BaseModel):
    referral_code: str
    referrals_count: int
    total_earned: str
    referral_link: str


class UserSettings(BaseModel):
    language_code: str
    timezone: str
    notifications_enabled: bool
    email_notifications: bool
    sms_notifications: bool
    two_factor_enabled: bool


class UserSettingsUpdate(BaseModel):
    language_code: Optional[str] = None
    timezone: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None


class UserList(BaseModel):
    users: list[UserResponse]
    total: int
    page: int
    per_page: int
    pages: int


class UserSearch(BaseModel):
    query: Optional[str] = None
    status: Optional[UserStatus] = None
    role: Optional[UserRole] = None
    is_verified: Optional[bool] = None
    is_premium: Optional[bool] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


class UserActivity(BaseModel):
    user_id: int
    action: str
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserActivityList(BaseModel):
    activities: list[UserActivity]
    total: int
    page: int
    per_page: int
    pages: int
