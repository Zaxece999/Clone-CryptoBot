from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from enum import Enum


class ExchangeStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ExchangeTypeEnum(str, Enum):
    CRYPTO_TO_CRYPTO = "crypto_to_crypto"
    CRYPTO_TO_FIAT = "crypto_to_fiat"
    FIAT_TO_CRYPTO = "fiat_to_crypto"


class ExchangeRateRequest(BaseModel):
    from_currency: str = Field(..., min_length=3, max_length=10, description="Исходная валюта")
    to_currency: str = Field(..., min_length=3, max_length=10, description="Целевая валюта")
    amount: Optional[Decimal] = Field(None, gt=0, description="Сумма для расчета")

    @validator('from_currency', 'to_currency')
    def validate_currency(cls, v):
        return v.upper()

    @validator('amount')
    def validate_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Amount must be positive')
        return v


class ExchangeCalculateRequest(BaseModel):
    from_currency: str = Field(..., min_length=3, max_length=10, description="Исходная валюта")
    to_currency: str = Field(..., min_length=3, max_length=10, description="Целевая валюта")
    from_amount: Decimal = Field(..., gt=0, description="Сумма для обмена")

    @validator('from_currency', 'to_currency')
    def validate_currency(cls, v):
        return v.upper()

    @validator('from_amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v


class ExchangeCreateRequest(BaseModel):
    from_currency: str = Field(..., min_length=3, max_length=10, description="Исходная валюта")
    to_currency: str = Field(..., min_length=3, max_length=10, description="Целевая валюта")
    from_amount: Decimal = Field(..., gt=0, description="Сумма для обмена")

    @validator('from_currency', 'to_currency')
    def validate_currency(cls, v):
        return v.upper()

    @validator('from_amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v


class ExchangeProcessRequest(BaseModel):
    exchange_id: str = Field(..., min_length=32, max_length=32, description="ID обмена")


class ExchangeCancelRequest(BaseModel):
    exchange_id: str = Field(..., min_length=32, max_length=32, description="ID обмена")
    reason: Optional[str] = Field(None, max_length=500, description="Причина отмены")


class ExchangeListRequest(BaseModel):
    status: Optional[ExchangeStatusEnum] = Field(None, description="Фильтр по статусу")
    from_currency: Optional[str] = Field(None, min_length=3, max_length=10, description="Фильтр по исходной валюте")
    to_currency: Optional[str] = Field(None, min_length=3, max_length=10, description="Фильтр по целевой валюте")
    limit: int = Field(50, ge=1, le=100, description="Количество записей")
    offset: int = Field(0, ge=0, description="Смещение")

    @validator('from_currency', 'to_currency')
    def validate_currency(cls, v):
        return v.upper() if v else v


class ExchangeRateResponse(BaseModel):
    from_currency: str
    to_currency: str
    rate: str
    buy_rate: str
    sell_rate: str
    spread_percentage: str
    source: str
    min_amount: Optional[str] = None
    max_amount: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class ExchangeCalculationResponse(BaseModel):
    from_currency: str
    to_currency: str
    from_amount: str
    to_amount: str
    exchange_rate: str
    fee_amount: str
    fee_percentage: str
    fee_currency: str
    total_from_amount: str
    net_to_amount: str
    rate_source: str
    expires_in_minutes: int


class ExchangeResponse(BaseModel):
    exchange_id: str
    user_id: int
    exchange_type: ExchangeTypeEnum
    status: ExchangeStatusEnum
    from_currency: str
    to_currency: str
    from_amount: str
    to_amount: str
    exchange_rate: str
    fee_amount: str
    fee_currency: str
    fee_percentage: str
    total_from_amount: Optional[str] = None
    net_to_amount: Optional[str] = None
    expires_at: Optional[datetime] = None
    debit_transaction_id: Optional[str] = None
    credit_transaction_id: Optional[str] = None
    external_exchange_id: Optional[str] = None
    external_provider: Optional[str] = None
    notes: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    is_expired: Optional[bool] = None
    is_pending: Optional[bool] = None
    is_completed: Optional[bool] = None
    is_failed: Optional[bool] = None

    class Config:
        from_attributes = True


class ExchangeListResponse(BaseModel):
    exchanges: List[ExchangeResponse]
    total: int
    has_more: bool


class ExchangeProviderResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    supported_currencies: Optional[List[str]] = None
    default_fee_percentage: str
    min_fee_amount: Optional[str] = None
    max_fee_amount: Optional[str] = None
    min_exchange_amount: Optional[str] = None
    max_exchange_amount: Optional[str] = None
    daily_limit: Optional[str] = None
    is_active: bool
    priority: int
    success_rate: Optional[float] = None
    total_exchanges: int
    successful_exchanges: int
    failed_exchanges: int
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExchangeLimitResponse(BaseModel):
    user_id: int
    currency: str
    daily_limit: str
    monthly_limit: str
    yearly_limit: str
    daily_used: str
    monthly_used: str
    yearly_used: str
    daily_remaining: Optional[str] = None
    monthly_remaining: Optional[str] = None
    yearly_remaining: Optional[str] = None
    daily_reset_at: datetime
    monthly_reset_at: datetime
    yearly_reset_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExchangeHistoryResponse(BaseModel):
    from_currency: str
    to_currency: str
    rate: str
    volume_24h: Optional[str] = None
    change_24h: Optional[str] = None
    source: str
    timestamp: datetime

    class Config:
        from_attributes = True


class ExchangeStatsResponse(BaseModel):
    total_exchanges: int
    completed_exchanges: int
    failed_exchanges: int
    cancelled_exchanges: int
    total_volume_usd: str
    average_exchange_amount: str
    popular_pairs: List[Dict[str, Any]]
    success_rate: float
    average_processing_time_seconds: Optional[float] = None


class SupportedPairsResponse(BaseModel):
    pairs: List[Dict[str, Any]]


class CurrencyListResponse(BaseModel):
    crypto_currencies: List[Dict[str, str]]
    fiat_currencies: List[Dict[str, str]]


class ExchangeErrorResponse(BaseModel):
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None


class ExchangeRateCreateRequest(BaseModel):
    from_currency: str = Field(..., min_length=3, max_length=10)
    to_currency: str = Field(..., min_length=3, max_length=10)
    rate: Decimal = Field(..., gt=0)
    spread_percentage: Decimal = Field(0.001, ge=0, le=0.1)
    source: str = Field(..., min_length=1, max_length=50)
    min_amount: Optional[Decimal] = Field(None, gt=0)
    max_amount: Optional[Decimal] = Field(None, gt=0)
    is_active: bool = Field(True)

    @validator('from_currency', 'to_currency')
    def validate_currency(cls, v):
        return v.upper()

    @validator('max_amount')
    def validate_max_amount(cls, v, values):
        if v is not None and 'min_amount' in values and values['min_amount'] is not None:
            if v <= values['min_amount']:
                raise ValueError('max_amount must be greater than min_amount')
        return v


class ExchangeRateUpdateRequest(BaseModel):
    rate: Optional[Decimal] = Field(None, gt=0)
    spread_percentage: Optional[Decimal] = Field(None, ge=0, le=0.1)
    min_amount: Optional[Decimal] = Field(None, gt=0)
    max_amount: Optional[Decimal] = Field(None, gt=0)
    is_active: Optional[bool] = None

    @validator('max_amount')
    def validate_max_amount(cls, v, values):
        if v is not None and 'min_amount' in values and values['min_amount'] is not None:
            if v <= values['min_amount']:
                raise ValueError('max_amount must be greater than min_amount')
        return v


class ExchangeProviderCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    api_url: Optional[str] = Field(None, max_length=255)
    api_key: Optional[str] = Field(None, max_length=255)
    api_secret: Optional[str] = Field(None, max_length=255)
    supported_currencies: Optional[List[str]] = None
    default_fee_percentage: Decimal = Field(0.005, ge=0, le=0.1)
    min_fee_amount: Optional[Decimal] = Field(None, gt=0)
    max_fee_amount: Optional[Decimal] = Field(None, gt=0)
    min_exchange_amount: Optional[Decimal] = Field(None, gt=0)
    max_exchange_amount: Optional[Decimal] = Field(None, gt=0)
    daily_limit: Optional[Decimal] = Field(None, gt=0)
    is_active: bool = Field(True)
    priority: int = Field(0, ge=0, le=100)


class ExchangeProviderUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    api_url: Optional[str] = Field(None, max_length=255)
    api_key: Optional[str] = Field(None, max_length=255)
    api_secret: Optional[str] = Field(None, max_length=255)
    supported_currencies: Optional[List[str]] = None
    default_fee_percentage: Optional[Decimal] = Field(None, ge=0, le=0.1)
    min_fee_amount: Optional[Decimal] = Field(None, gt=0)
    max_fee_amount: Optional[Decimal] = Field(None, gt=0)
    min_exchange_amount: Optional[Decimal] = Field(None, gt=0)
    max_exchange_amount: Optional[Decimal] = Field(None, gt=0)
    daily_limit: Optional[Decimal] = Field(None, gt=0)
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=100)


class ExchangeLimitUpdateRequest(BaseModel):
    daily_limit: Optional[Decimal] = Field(None, gt=0)
    monthly_limit: Optional[Decimal] = Field(None, gt=0)
    yearly_limit: Optional[Decimal] = Field(None, gt=0)
