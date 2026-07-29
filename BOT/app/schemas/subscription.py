from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from enum import Enum


class SubscriptionStatusEnum(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"


class SubscriptionTypeEnum(str, Enum):
    CHANNEL = "channel"
    GROUP = "group"
    BOT = "bot"
    SERVICE = "service"


class BillingPeriodEnum(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class SubscriptionCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Название подписки")
    description: Optional[str] = Field(None, max_length=1000, description="Описание подписки")
    subscription_type: SubscriptionTypeEnum = Field(..., description="Тип подписки")
    price: Decimal = Field(..., ge=0, description="Цена подписки")
    currency: str = Field(..., min_length=3, max_length=10, description="Валюта")
    billing_period: BillingPeriodEnum = Field(..., description="Период биллинга")
    chat_id: Optional[str] = Field(None, description="ID канала/группы/бота")
    chat_username: Optional[str] = Field(None, description="Username канала/группы/бота")
    chat_title: Optional[str] = Field(None, description="Название канала/группы")
    trial_days: Optional[int] = Field(None, ge=0, le=365, description="Дни пробного периода")
    auto_renew: bool = Field(True, description="Автоматическое продление")

    @validator('currency')
    def validate_currency(cls, v):
        return v.upper()

    @validator('price')
    def validate_price(cls, v):
        if v < 0:
            raise ValueError('Price cannot be negative')
        return v


class SubscriptionUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Название подписки")
    description: Optional[str] = Field(None, max_length=1000, description="Описание подписки")
    price: Optional[Decimal] = Field(None, ge=0, description="Цена подписки")
    auto_renew: Optional[bool] = Field(None, description="Автоматическое продление")
    send_reminders: Optional[bool] = Field(None, description="Отправлять напоминания")

    @validator('price')
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError('Price cannot be negative')
        return v


class SubscriptionActivateRequest(BaseModel):
    subscription_id: str = Field(..., min_length=32, max_length=32, description="ID подписки")


class SubscriptionCancelRequest(BaseModel):
    subscription_id: str = Field(..., min_length=32, max_length=32, description="ID подписки")
    reason: Optional[str] = Field(None, max_length=500, description="Причина отмены")


class SubscriptionRenewRequest(BaseModel):
    subscription_id: str = Field(..., min_length=32, max_length=32, description="ID подписки")


class SubscriptionListRequest(BaseModel):
    status: Optional[SubscriptionStatusEnum] = Field(None, description="Фильтр по статусу")
    subscription_type: Optional[SubscriptionTypeEnum] = Field(None, description="Фильтр по типу")
    limit: int = Field(50, ge=1, le=100, description="Количество записей")
    offset: int = Field(0, ge=0, description="Смещение")


class SubscriptionInviteCreateRequest(BaseModel):
    subscription_id: str = Field(..., min_length=32, max_length=32, description="ID подписки")
    max_uses: Optional[int] = Field(None, ge=1, description="Максимальное количество использований")
    expires_at: Optional[datetime] = Field(None, description="Дата истечения")
    description: Optional[str] = Field(None, max_length=500, description="Описание приглашения")


class SubscriptionInviteUseRequest(BaseModel):
    invite_id: str = Field(..., min_length=32, max_length=32, description="ID приглашения")


class SubscriptionResponse(BaseModel):
    subscription_id: str
    user_id: int
    title: str
    description: Optional[str] = None
    subscription_type: SubscriptionTypeEnum
    status: SubscriptionStatusEnum
    price: str
    currency: str
    billing_period: BillingPeriodEnum
    chat_id: Optional[str] = None
    chat_username: Optional[str] = None
    chat_title: Optional[str] = None
    invite_link: Optional[str] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    next_billing_at: Optional[datetime] = None
    trial_days: Optional[int] = None
    trial_ends_at: Optional[datetime] = None
    total_payments: int
    total_amount_paid: str
    failed_payments: int
    auto_renew: bool
    send_reminders: bool
    metadata: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    activated_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    is_active: Optional[bool] = None
    is_expired: Optional[bool] = None
    is_trial: Optional[bool] = None
    days_until_expiry: Optional[int] = None
    next_payment_amount: Optional[str] = None

    class Config:
        from_attributes = True


class SubscriptionListResponse(BaseModel):
    subscriptions: List[SubscriptionResponse]
    total: int
    has_more: bool


class SubscriptionPaymentResponse(BaseModel):
    payment_id: str
    subscription_id: int
    user_id: int
    amount: str
    currency: str
    status: str
    billing_period_start: datetime
    billing_period_end: datetime
    transaction_id: Optional[str] = None
    failure_reason: Optional[str] = None
    refund_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    paid_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None

    is_paid: Optional[bool] = None
    is_failed: Optional[bool] = None

    class Config:
        from_attributes = True


class SubscriptionPaymentListResponse(BaseModel):
    payments: List[SubscriptionPaymentResponse]
    total: int
    has_more: bool


class SubscriptionPlanResponse(BaseModel):
    plan_id: str
    name: str
    description: Optional[str] = None
    subscription_type: SubscriptionTypeEnum
    price: str
    currency: str
    billing_period: BillingPeriodEnum
    trial_days: Optional[int] = None
    max_subscribers: Optional[int] = None
    features: Optional[List[str]] = None
    is_active: bool
    is_public: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionInviteResponse(BaseModel):
    invite_id: str
    subscription_id: int
    creator_id: int
    max_uses: Optional[int] = None
    uses_count: int
    expires_at: Optional[datetime] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    is_valid: Optional[bool] = None
    invite_url: Optional[str] = None

    class Config:
        from_attributes = True


class SubscriptionStatsResponse(BaseModel):
    subscription_id: str
    title: str
    status: str
    total_payments: int
    total_revenue: str
    currency: str
    active_subscribers: int
    cancelled_subscribers: int
    revenue_this_month: str
    revenue_last_month: str
    growth_rate: float
    churn_rate: float
    average_subscription_length_days: Optional[float] = None
    created_at: datetime
    next_billing_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class SubscriptionNotificationResponse(BaseModel):
    notification_id: str
    subscription_id: int
    user_id: int
    notification_type: str
    title: str
    message: str
    is_sent: bool
    sent_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionPlanCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    subscription_type: SubscriptionTypeEnum = Field(...)
    price: Decimal = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=10)
    billing_period: BillingPeriodEnum = Field(...)
    trial_days: Optional[int] = Field(None, ge=0, le=365)
    max_subscribers: Optional[int] = Field(None, ge=1)
    features: Optional[List[str]] = None
    is_active: bool = Field(True)
    is_public: bool = Field(True)

    @validator('currency')
    def validate_currency(cls, v):
        return v.upper()


class SubscriptionPlanUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[Decimal] = Field(None, ge=0)
    trial_days: Optional[int] = Field(None, ge=0, le=365)
    max_subscribers: Optional[int] = Field(None, ge=1)
    features: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None


class SubscriptionAdminUpdateRequest(BaseModel):
    status: Optional[SubscriptionStatusEnum] = None
    expires_at: Optional[datetime] = None
    next_billing_at: Optional[datetime] = None
    auto_renew: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=1000)


class SubscriptionWebhookData(BaseModel):
    subscription_id: str
    user_id: int
    event_type: str
    subscription_data: SubscriptionResponse
    timestamp: datetime


class SubscriptionErrorResponse(BaseModel):
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None


class SubscriptionSummaryResponse(BaseModel):
    total_subscriptions: int
    active_subscriptions: int
    expired_subscriptions: int
    cancelled_subscriptions: int
    total_spent: str
    currency: str
    next_payment_date: Optional[datetime] = None
    next_payment_amount: Optional[str] = None


class BillingHistoryResponse(BaseModel):
    payments: List[SubscriptionPaymentResponse]
    total_payments: int
    total_amount: str
    currency: str
    period_start: datetime
    period_end: datetime


class SubscriptionAnalyticsResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    total_subscriptions: int
    new_subscriptions: int
    cancelled_subscriptions: int
    renewed_subscriptions: int
    total_revenue: str
    currency: str
    average_subscription_value: str
    churn_rate: float
    growth_rate: float
    popular_billing_periods: List[Dict[str, Any]]
    revenue_by_type: List[Dict[str, Any]]
