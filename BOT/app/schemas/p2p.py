from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.models.p2p import P2POrderType, P2POrderStatus, P2PPaymentMethod


class P2POrderBase(BaseModel):
    crypto_currency: str = Field(..., description="Криптовалюта")
    crypto_amount: str = Field(..., description="Количество криптовалюты", regex=r'^\d+(\.\d+)?$')
    fiat_currency: str = Field(..., description="Фиатная валюта")
    price_per_unit: str = Field(..., description="Цена за единицу", regex=r'^\d+(\.\d+)?$')
    payment_methods: List[str] = Field(..., min_items=1, description="Способы оплаты")

    @validator('crypto_currency')
    def validate_crypto_currency(cls, v):
        supported_currencies = ['BTC', 'ETH', 'USDT', 'LTC', 'BNB', 'TRX', 'TON']
        if v not in supported_currencies:
            raise ValueError(f'Unsupported crypto currency: {v}')
        return v

    @validator('fiat_currency')
    def validate_fiat_currency(cls, v):
        supported_currencies = ['USD', 'EUR', 'RUB', 'CNY', 'KRW', 'JPY']
        if v not in supported_currencies:
            raise ValueError(f'Unsupported fiat currency: {v}')
        return v

    @validator('crypto_amount', 'price_per_unit')
    def validate_amounts(cls, v):
        try:
            amount = Decimal(v)
            if amount <= 0:
                raise ValueError('Amount must be positive')
            return str(amount)
        except (ValueError, TypeError):
            raise ValueError('Invalid amount format')

    @validator('payment_methods')
    def validate_payment_methods(cls, v):
        valid_methods = [method.value for method in P2PPaymentMethod]
        for method in v:
            if method not in valid_methods:
                raise ValueError(f'Invalid payment method: {method}')
        return v


class P2POrderCreateRequest(P2POrderBase):
    type: P2POrderType = Field(..., description="Тип ордера (buy/sell)")
    min_amount: Optional[str] = Field(None, description="Минимальная сумма сделки", regex=r'^\d+(\.\d+)?$')
    max_amount: Optional[str] = Field(None, description="Максимальная сумма сделки", regex=r'^\d+(\.\d+)?$')
    payment_details: Optional[str] = Field(None, max_length=1000, description="Детали оплаты")
    terms: Optional[str] = Field(None, max_length=2000, description="Условия сделки")
    auto_reply: Optional[str] = Field(None, max_length=500, description="Автоответ")
    payment_timeout_minutes: int = Field(30, ge=5, le=1440, description="Таймаут оплаты в минутах")
    expires_in_hours: Optional[int] = Field(None, ge=1, le=720, description="Срок действия в часах")
    min_trades: int = Field(0, ge=0, le=10000, description="Минимальное количество сделок")
    min_completion_rate: float = Field(0, ge=0, le=100, description="Минимальный процент завершения")
    country: Optional[str] = Field(None, min_length=2, max_length=2, description="Код страны")
    city: Optional[str] = Field(None, max_length=100, description="Город")

    @validator('min_amount', 'max_amount')
    def validate_optional_amounts(cls, v):
        if v is None:
            return v
        try:
            amount = Decimal(v)
            if amount <= 0:
                raise ValueError('Amount must be positive')
            return str(amount)
        except (ValueError, TypeError):
            raise ValueError('Invalid amount format')

    @validator('max_amount')
    def validate_amount_range(cls, v, values):
        if v is None or 'min_amount' not in values or values['min_amount'] is None:
            return v

        min_amount = Decimal(values['min_amount'])
        max_amount = Decimal(v)

        if max_amount < min_amount:
            raise ValueError('Max amount cannot be less than min amount')

        return v


class P2PTradeCreateRequest(BaseModel):
    order_id: str = Field(..., min_length=8, max_length=8, description="ID ордера")
    trade_amount: str = Field(..., description="Сумма сделки в фиате", regex=r'^\d+(\.\d+)?$')
    payment_method: str = Field(..., description="Способ оплаты")
    message: Optional[str] = Field(None, max_length=500, description="Сообщение")

    @validator('order_id')
    def validate_order_id(cls, v):
        if not v.startswith('P2P') or not v[3:].isalnum():
            raise ValueError('Invalid order ID format')
        return v.upper()

    @validator('trade_amount')
    def validate_trade_amount(cls, v):
        try:
            amount = Decimal(v)
            if amount <= 0:
                raise ValueError('Trade amount must be positive')
            return str(amount)
        except (ValueError, TypeError):
            raise ValueError('Invalid amount format')


class P2POrderResponse(P2POrderBase):
    id: str = Field(..., description="Внутренний ID ордера")
    order_id: str = Field(..., description="Публичный ID ордера")
    creator_id: int = Field(..., description="ID создателя")
    type: P2POrderType = Field(..., description="Тип ордера")
    status: P2POrderStatus = Field(..., description="Статус ордера")
    fiat_amount: str = Field(..., description="Общая сумма в фиате")
    min_amount: Optional[str] = Field(None, description="Минимальная сумма сделки")
    max_amount: Optional[str] = Field(None, description="Максимальная сумма сделки")
    payment_details: Optional[str] = Field(None, description="Детали оплаты")
    terms: Optional[str] = Field(None, description="Условия сделки")
    auto_reply: Optional[str] = Field(None, description="Автоответ")
    payment_timeout_minutes: int = Field(..., description="Таймаут оплаты в минутах")
    expires_at: Optional[datetime] = Field(None, description="Дата истечения")
    min_trades: int = Field(..., description="Минимальное количество сделок")
    min_completion_rate: float = Field(..., description="Минимальный процент завершения")
    country: Optional[str] = Field(None, description="Код страны")
    city: Optional[str] = Field(None, description="Город")
    views_count: int = Field(..., description="Количество просмотров")
    matches_count: int = Field(..., description="Количество совпадений")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    is_active: bool = Field(..., description="Активен ли ордер")
    is_expired: bool = Field(..., description="Истек ли ордер")

    class Config:
        from_attributes = True


class P2PTradeResponse(BaseModel):
    id: str = Field(..., description="Внутренний ID сделки")
    trade_id: str = Field(..., description="Публичный ID сделки")
    order_id: str = Field(..., description="ID ордера")
    buyer_id: int = Field(..., description="ID покупателя")
    seller_id: int = Field(..., description="ID продавца")
    crypto_currency: str = Field(..., description="Криптовалюта")
    crypto_amount: str = Field(..., description="Количество криптовалюты")
    fiat_currency: str = Field(..., description="Фиатная валюта")
    fiat_amount: str = Field(..., description="Сумма в фиате")
    price_per_unit: str = Field(..., description="Цена за единицу")
    status: P2POrderStatus = Field(..., description="Статус сделки")
    payment_method: str = Field(..., description="Способ оплаты")
    payment_details: Optional[str] = Field(None, description="Детали оплаты")
    payment_timeout_at: Optional[datetime] = Field(None, description="Таймаут оплаты")
    payment_confirmed_by_buyer: bool = Field(..., description="Подтверждение оплаты покупателем")
    payment_confirmed_by_seller: bool = Field(..., description="Подтверждение оплаты продавцом")
    crypto_released: bool = Field(..., description="Освобождена ли криптовалюта")
    dispute_reason: Optional[str] = Field(None, description="Причина спора")
    buyer_rating: Optional[int] = Field(None, description="Оценка покупателя")
    seller_rating: Optional[int] = Field(None, description="Оценка продавца")
    buyer_feedback: Optional[str] = Field(None, description="Отзыв покупателя")
    seller_feedback: Optional[str] = Field(None, description="Отзыв продавца")
    matched_at: datetime = Field(..., description="Дата создания сделки")
    started_at: Optional[datetime] = Field(None, description="Дата начала сделки")
    completed_at: Optional[datetime] = Field(None, description="Дата завершения")
    cancelled_at: Optional[datetime] = Field(None, description="Дата отмены")

    is_payment_expired: bool = Field(..., description="Истекло ли время для оплаты")

    class Config:
        from_attributes = True


class P2PChatMessageResponse(BaseModel):
    id: str = Field(..., description="ID сообщения")
    sender_id: Optional[int] = Field(None, description="ID отправителя")
    message_type: str = Field(..., description="Тип сообщения")
    content: str = Field(..., description="Содержимое сообщения")
    is_read: bool = Field(..., description="Прочитано ли сообщение")
    is_system: bool = Field(..., description="Системное ли сообщение")
    created_at: datetime = Field(..., description="Дата создания")

    class Config:
        from_attributes = True


class P2PUserStatsResponse(BaseModel):
    user_id: int = Field(..., description="ID пользователя")
    total_trades: int = Field(..., description="Общее количество сделок")
    completed_trades: int = Field(..., description="Завершенные сделки")
    cancelled_trades: int = Field(..., description="Отмененные сделки")
    disputed_trades: int = Field(..., description="Спорные сделки")
    buy_trades: int = Field(..., description="Сделки как покупатель")
    buy_volume_usd: str = Field(..., description="Объем покупок в USD")
    sell_trades: int = Field(..., description="Сделки как продавец")
    sell_volume_usd: str = Field(..., description="Объем продаж в USD")
    average_rating: float = Field(..., description="Средний рейтинг")
    total_ratings: int = Field(..., description="Общее количество оценок")
    completion_rate: float = Field(..., description="Процент завершенных сделок")
    dispute_rate: float = Field(..., description="Процент спорных сделок")
    first_trade_at: Optional[datetime] = Field(None, description="Дата первой сделки")
    last_trade_at: Optional[datetime] = Field(None, description="Дата последней сделки")

    class Config:
        from_attributes = True


class P2POrderListResponse(BaseModel):
    orders: List[P2POrderResponse] = Field(..., description="Список ордеров")
    total: int = Field(..., description="Общее количество ордеров")
    has_more: bool = Field(..., description="Есть ли еще ордеры")


class P2PTradeListResponse(BaseModel):
    trades: List[P2PTradeResponse] = Field(..., description="Список сделок")
    total: int = Field(..., description="Общее количество сделок")
    has_more: bool = Field(..., description="Есть ли еще сделки")


class P2PChatResponse(BaseModel):
    trade_id: str = Field(..., description="ID сделки")
    messages: List[P2PChatMessageResponse] = Field(..., description="Сообщения чата")
    total_messages: int = Field(..., description="Общее количество сообщений")


class P2POrderFiltersRequest(BaseModel):
    type: Optional[P2POrderType] = Field(None, description="Тип ордера")
    crypto_currency: Optional[str] = Field(None, description="Криптовалюта")
    fiat_currency: Optional[str] = Field(None, description="Фиатная валюта")
    payment_method: Optional[str] = Field(None, description="Способ оплаты")
    country: Optional[str] = Field(None, description="Страна")
    min_amount: Optional[str] = Field(None, description="Минимальная сумма")
    max_amount: Optional[str] = Field(None, description="Максимальная сумма")
    sort_by: str = Field("created_at", description="Поле для сортировки")
    sort_order: str = Field("desc", description="Порядок сортировки")
    limit: int = Field(50, ge=1, le=100, description="Количество записей")
    offset: int = Field(0, ge=0, description="Смещение")

    @validator('sort_by')
    def validate_sort_by(cls, v):
        allowed_fields = ['created_at', 'price', 'amount', 'views_count']
        if v not in allowed_fields:
            raise ValueError(f'Invalid sort field: {v}')
        return v

    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('Sort order must be asc or desc')
        return v


class P2PTradeActionRequest(BaseModel):
    trade_id: str = Field(..., min_length=8, max_length=8, description="ID сделки")
    message: Optional[str] = Field(None, max_length=500, description="Сообщение")

    @validator('trade_id')
    def validate_trade_id(cls, v):
        if not v.startswith('TRD') or not v[3:].isalnum():
            raise ValueError('Invalid trade ID format')
        return v.upper()


class P2PDisputeRequest(BaseModel):
    trade_id: str = Field(..., min_length=8, max_length=8, description="ID сделки")
    reason: str = Field(..., min_length=10, max_length=1000, description="Причина спора")

    @validator('trade_id')
    def validate_trade_id(cls, v):
        if not v.startswith('TRD') or not v[3:].isalnum():
            raise ValueError('Invalid trade ID format')
        return v.upper()


class P2PRatingRequest(BaseModel):
    trade_id: str = Field(..., min_length=8, max_length=8, description="ID сделки")
    rating: int = Field(..., ge=1, le=5, description="Оценка от 1 до 5")
    feedback: Optional[str] = Field(None, max_length=500, description="Отзыв")

    @validator('trade_id')
    def validate_trade_id(cls, v):
        if not v.startswith('TRD') or not v[3:].isalnum():
            raise ValueError('Invalid trade ID format')
        return v.upper()


class P2PChatMessageRequest(BaseModel):
    trade_id: str = Field(..., min_length=8, max_length=8, description="ID сделки")
    content: str = Field(..., min_length=1, max_length=1000, description="Содержимое сообщения")
    message_type: str = Field("text", description="Тип сообщения")

    @validator('trade_id')
    def validate_trade_id(cls, v):
        if not v.startswith('TRD') or not v[3:].isalnum():
            raise ValueError('Invalid trade ID format')
        return v.upper()

    @validator('message_type')
    def validate_message_type(cls, v):
        allowed_types = ['text', 'image', 'file']
        if v not in allowed_types:
            raise ValueError(f'Invalid message type: {v}')
        return v


class P2PErrorResponse(BaseModel):
    error: str = Field(..., description="Код ошибки")
    message: str = Field(..., description="Сообщение об ошибке")
    order_id: Optional[str] = Field(None, description="ID ордера")
    trade_id: Optional[str] = Field(None, description="ID сделки")
    details: Optional[Dict[str, Any]] = Field(None, description="Дополнительные детали")


class P2PMarketStatsResponse(BaseModel):
    total_orders: int = Field(..., description="Общее количество ордеров")
    active_orders: int = Field(..., description="Активные ордеры")
    total_trades: int = Field(..., description="Общее количество сделок")
    completed_trades: int = Field(..., description="Завершенные сделки")
    total_volume_usd: str = Field(..., description="Общий объем торгов в USD")
    average_completion_time_minutes: int = Field(..., description="Среднее время завершения сделки")
    popular_currencies: List[Dict[str, Any]] = Field(..., description="Популярные валютные пары")
    popular_payment_methods: List[Dict[str, Any]] = Field(..., description="Популярные способы оплаты")


class P2PPriceStatsResponse(BaseModel):
    crypto_currency: str = Field(..., description="Криптовалюта")
    fiat_currency: str = Field(..., description="Фиатная валюта")
    buy_orders_count: int = Field(..., description="Количество ордеров на покупку")
    sell_orders_count: int = Field(..., description="Количество ордеров на продажу")
    min_buy_price: Optional[str] = Field(None, description="Минимальная цена покупки")
    max_buy_price: Optional[str] = Field(None, description="Максимальная цена покупки")
    avg_buy_price: Optional[str] = Field(None, description="Средняя цена покупки")
    min_sell_price: Optional[str] = Field(None, description="Минимальная цена продажи")
    max_sell_price: Optional[str] = Field(None, description="Максимальная цена продажи")
    avg_sell_price: Optional[str] = Field(None, description="Средняя цена продажи")
    last_trade_price: Optional[str] = Field(None, description="Цена последней сделки")
    price_change_24h: Optional[str] = Field(None, description="Изменение цены за 24 часа")


class P2PNotificationResponse(BaseModel):
    id: str = Field(..., description="ID уведомления")
    user_id: int = Field(..., description="ID пользователя")
    type: str = Field(..., description="Тип уведомления")
    title: str = Field(..., description="Заголовок")
    message: str = Field(..., description="Сообщение")
    data: Optional[Dict[str, Any]] = Field(None, description="Дополнительные данные")
    is_read: bool = Field(..., description="Прочитано ли уведомление")
    created_at: datetime = Field(..., description="Дата создания")
