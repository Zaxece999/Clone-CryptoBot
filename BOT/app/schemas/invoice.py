from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator, HttpUrl
from enum import Enum

from app.models.invoice import InvoiceStatus, InvoiceType


class InvoiceBase(BaseModel):
    currency: str = Field(..., description="Валюта инвойса")
    amount: str = Field(..., description="Сумма инвойса", regex=r'^\d+(\.\d+)?$')
    description: Optional[str] = Field(None, max_length=1000, description="Описание инвойса")

    @validator('currency')
    def validate_currency(cls, v):
        supported_currencies = [
            'BTC', 'ETH', 'USDT', 'LTC', 'BNB', 'TRX', 'TON'
        ]
        if v not in supported_currencies:
            raise ValueError(f'Unsupported currency: {v}')
        return v

    @validator('amount')
    def validate_amount(cls, v):
        try:
            amount = Decimal(v)
            if amount <= 0:
                raise ValueError('Amount must be positive')
            if amount > Decimal('10000000'):
                raise ValueError('Amount too large')
            return str(amount)
        except (ValueError, TypeError):
            raise ValueError('Invalid amount format')


class InvoiceCreateRequest(InvoiceBase):
    payload: Optional[str] = Field(None, max_length=4096, description="Дополнительные данные")
    expires_in_hours: Optional[int] = Field(None, ge=1, le=8760, description="Срок действия в часах (до 1 года)")
    return_url: Optional[HttpUrl] = Field(None, description="URL возврата")
    success_url: Optional[HttpUrl] = Field(None, description="URL успешной оплаты")
    cancel_url: Optional[HttpUrl] = Field(None, description="URL отмены")
    webhook_url: Optional[HttpUrl] = Field(None, description="URL webhook для уведомлений")
    notify_on_payment: bool = Field(True, description="Уведомлять об оплате")

    type: InvoiceType = Field(InvoiceType.STANDARD, description="Тип инвойса")
    recurring_interval_days: Optional[int] = Field(None, ge=1, le=365, description="Интервал повторения в днях")
    recurring_count: Optional[int] = Field(None, ge=1, le=1000, description="Количество повторений")

    @validator('recurring_interval_days')
    def validate_recurring_interval(cls, v, values):
        invoice_type = values.get('type')
        if invoice_type == InvoiceType.RECURRING and not v:
            raise ValueError('Recurring invoices require interval_days')
        return v


class InvoicePayRequest(BaseModel):
    invoice_id: str = Field(..., min_length=10, max_length=10, description="ID инвойса")

    @validator('invoice_id')
    def validate_invoice_id(cls, v):
        if not v.startswith('INV') or not v[3:].isalnum():
            raise ValueError('Invalid invoice ID format')
        return v.upper()


class InvoiceResponse(InvoiceBase):
    id: str = Field(..., description="Внутренний ID инвойса")
    invoice_id: str = Field(..., description="Публичный ID инвойса")
    creator_id: int = Field(..., description="ID создателя")
    payer_id: Optional[int] = Field(None, description="ID плательщика")
    type: InvoiceType = Field(..., description="Тип инвойса")
    status: InvoiceStatus = Field(..., description="Статус инвойса")
    payload: Optional[str] = Field(None, description="Дополнительные данные")
    expires_at: Optional[datetime] = Field(None, description="Дата истечения")
    paid_at: Optional[datetime] = Field(None, description="Дата оплаты")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    return_url: Optional[str] = Field(None, description="URL возврата")
    success_url: Optional[str] = Field(None, description="URL успешной оплаты")
    cancel_url: Optional[str] = Field(None, description="URL отмены")
    webhook_url: Optional[str] = Field(None, description="URL webhook")

    recurring_interval_days: Optional[int] = Field(None, description="Интервал повторения в днях")
    recurring_count: Optional[int] = Field(None, description="Количество повторений")
    recurring_current: int = Field(0, description="Текущий номер повторения")
    parent_invoice_id: Optional[str] = Field(None, description="ID родительского инвойса")

    is_active: bool = Field(..., description="Активен ли инвойс")
    is_expired: bool = Field(..., description="Истек ли инвойс")
    can_be_paid: bool = Field(..., description="Можно ли оплатить")
    expiry_info: Dict[str, Any] = Field(..., description="Информация о сроке действия")
    payment_url: str = Field(..., description="URL для оплаты")

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    invoices: List[InvoiceResponse] = Field(..., description="Список инвойсов")
    total: int = Field(..., description="Общее количество инвойсов")
    has_more: bool = Field(..., description="Есть ли еще инвойсы")


class InvoicePaymentResponse(BaseModel):
    id: str = Field(..., description="ID платежа")
    invoice_id: str = Field(..., description="ID инвойса")
    payer_id: int = Field(..., description="ID плательщика")
    amount_paid: str = Field(..., description="Оплаченная сумма")
    currency: str = Field(..., description="Валюта")
    payment_method: Optional[str] = Field(None, description="Способ оплаты")
    payment_source: Optional[str] = Field(None, description="Источник платежа")
    paid_at: datetime = Field(..., description="Дата оплаты")

    invoice: InvoiceResponse = Field(..., description="Данные инвойса")

    class Config:
        from_attributes = True


class InvoicePaymentListResponse(BaseModel):
    payments: List[InvoicePaymentResponse] = Field(..., description="Список платежей")
    total: int = Field(..., description="Общее количество платежей")
    has_more: bool = Field(..., description="Есть ли еще платежи")


class InvoiceStatsResponse(BaseModel):
    created: Dict[str, Any] = Field(..., description="Статистика созданных инвойсов")
    paid: Dict[str, Any] = Field(..., description="Статистика оплаченных инвойсов")


class InvoiceHistoryRequest(BaseModel):
    status: Optional[InvoiceStatus] = Field(None, description="Фильтр по статусу")
    type: Optional[InvoiceType] = Field(None, description="Фильтр по типу")
    currency: Optional[str] = Field(None, description="Фильтр по валюте")
    limit: int = Field(50, ge=1, le=100, description="Количество записей")
    offset: int = Field(0, ge=0, description="Смещение")


class InvoiceInfoResponse(BaseModel):
    invoice_id: str = Field(..., description="ID инвойса")
    currency: str = Field(..., description="Валюта")
    amount: str = Field(..., description="Сумма")
    type: InvoiceType = Field(..., description="Тип инвойса")
    status: InvoiceStatus = Field(..., description="Статус инвойса")
    description: Optional[str] = Field(None, description="Описание")
    expires_at: Optional[datetime] = Field(None, description="Дата истечения")
    is_active: bool = Field(..., description="Можно ли оплатить")
    is_expired: bool = Field(..., description="Истек ли инвойс")
    expiry_info: Dict[str, Any] = Field(..., description="Информация о сроке действия")
    created_at: datetime = Field(..., description="Дата создания")
    payment_url: str = Field(..., description="URL для оплаты")


class InvoiceUrlResponse(BaseModel):
    invoice_id: str = Field(..., description="ID инвойса")
    payment_url: str = Field(..., description="URL для оплаты инвойса")
    qr_code_url: Optional[str] = Field(None, description="URL QR-кода")


class InvoiceValidationResponse(BaseModel):
    is_valid: bool = Field(..., description="Валиден ли инвойс")
    invoice_id: str = Field(..., description="ID инвойса")
    can_pay: bool = Field(..., description="Можно ли оплатить")
    reason: Optional[str] = Field(None, description="Причина, если нельзя оплатить")
    invoice_info: Optional[InvoiceInfoResponse] = Field(None, description="Информация об инвойсе")


class LegacyInvoiceCreateRequest(BaseModel):
    asset: str = Field(..., description="Валюта (legacy)")
    amount: str = Field(..., description="Сумма")
    description: Optional[str] = Field(None, description="Описание")
    payload: Optional[str] = Field(None, description="Дополнительные данные")

    @validator('asset')
    def validate_asset(cls, v):
        asset_mapping = {
            'USDT': 'USDT',
            'BTC': 'BTC',
            'ETH': 'ETH',
            'LTC': 'LTC',
            'BNB': 'BNB',
            'TRX': 'TRX',
            'TON': 'TON'
        }

        if v not in asset_mapping:
            raise ValueError(f'Unsupported asset: {v}')

        return asset_mapping[v]


class LegacyInvoiceResponse(BaseModel):
    ok: bool = Field(True, description="Успешность операции")
    result: Dict[str, Any] = Field(..., description="Результат")
    error: Optional[Dict[str, str]] = Field(None, description="Ошибка")


class InvoiceErrorResponse(BaseModel):
    error: str = Field(..., description="Код ошибки")
    message: str = Field(..., description="Сообщение об ошибке")
    invoice_id: Optional[str] = Field(None, description="ID инвойса")
    details: Optional[Dict[str, Any]] = Field(None, description="Дополнительные детали")


class InvoiceWebhookPayload(BaseModel):
    update_id: int = Field(..., description="ID обновления")
    update_type: str = Field(..., description="Тип обновления")
    request_date: datetime = Field(..., description="Дата запроса")
    payload: Dict[str, Any] = Field(..., description="Данные события")


class InvoicePaymentWebhookPayload(BaseModel):
    invoice_id: str = Field(..., description="ID инвойса")
    status: InvoiceStatus = Field(..., description="Статус инвойса")
    amount: str = Field(..., description="Сумма")
    currency: str = Field(..., description="Валюта")
    paid_at: datetime = Field(..., description="Дата оплаты")
    payer_id: int = Field(..., description="ID плательщика")
    payload: Optional[str] = Field(None, description="Дополнительные данные")


class InvoiceBulkCreateRequest(BaseModel):
    currency: str = Field(..., description="Валюта")
    amount: str = Field(..., description="Сумма каждого инвойса")
    count: int = Field(..., ge=1, le=100, description="Количество инвойсов")
    description: Optional[str] = Field(None, max_length=1000, description="Описание")
    expires_in_hours: Optional[int] = Field(None, ge=1, le=8760, description="Срок действия в часах")


class InvoiceBulkCreateResponse(BaseModel):
    created_count: int = Field(..., description="Количество созданных инвойсов")
    total_amount: str = Field(..., description="Общая сумма")
    currency: str = Field(..., description="Валюта")
    invoices: List[InvoiceResponse] = Field(..., description="Созданные инвойсы")
    download_url: Optional[str] = Field(None, description="URL для скачивания списка инвойсов")


class InvoiceTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Название шаблона")
    currency: str = Field(..., description="Валюта")
    amount: Optional[str] = Field(None, description="Сумма (может быть пустой)")
    description: Optional[str] = Field(None, max_length=1000, description="Описание")
    expires_in_hours: Optional[int] = Field(None, ge=1, le=8760, description="Срок действия в часах")


class InvoiceTemplateResponse(BaseModel):
    id: str = Field(..., description="ID шаблона")
    name: str = Field(..., description="Название шаблона")
    currency: str = Field(..., description="Валюта")
    amount: Optional[str] = Field(None, description="Сумма")
    description: Optional[str] = Field(None, description="Описание")
    expires_in_hours: Optional[int] = Field(None, description="Срок действия в часах")
    created_at: datetime = Field(..., description="Дата создания")
    usage_count: int = Field(0, description="Количество использований")


class InvoiceFromTemplateRequest(BaseModel):
    template_id: str = Field(..., description="ID шаблона")
    amount: Optional[str] = Field(None, description="Сумма (переопределить из шаблона)")
    description: Optional[str] = Field(None, description="Описание (переопределить из шаблона)")
    payload: Optional[str] = Field(None, description="Дополнительные данные")


class InvoiceAnalyticsRequest(BaseModel):
    period: str = Field(..., description="Период (day, week, month, year)")
    currency: Optional[str] = Field(None, description="Фильтр по валюте")
    start_date: Optional[datetime] = Field(None, description="Начальная дата")
    end_date: Optional[datetime] = Field(None, description="Конечная дата")

    @validator('period')
    def validate_period(cls, v):
        if v not in ['day', 'week', 'month', 'year']:
            raise ValueError('Period must be one of: day, week, month, year')
        return v


class InvoiceAnalyticsResponse(BaseModel):
    period: str = Field(..., description="Период")
    currency: Optional[str] = Field(None, description="Валюта")
    total_invoices: int = Field(..., description="Общее количество инвойсов")
    paid_invoices: int = Field(..., description="Оплаченные инвойсы")
    total_amount: str = Field(..., description="Общая сумма")
    paid_amount: str = Field(..., description="Оплаченная сумма")
    conversion_rate: float = Field(..., description="Коэффициент конверсии")
    average_amount: str = Field(..., description="Средняя сумма")
    data_points: List[Dict[str, Any]] = Field(..., description="Точки данных по периодам")
