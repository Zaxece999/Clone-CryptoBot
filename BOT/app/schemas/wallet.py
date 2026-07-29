from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.models.wallet import WalletStatus
from app.models.transaction import TransactionType, TransactionStatus, TransactionDirection


class WalletBase(BaseModel):
    currency: str = Field(..., description="Валюта кошелька")

    @validator('currency')
    def validate_currency(cls, v):
        supported_currencies = [
            'BTC', 'ETH', 'USDT', 'LTC', 'BNB', 'TRX', 'TON'
        ]
        if v not in supported_currencies:
            raise ValueError(f'Unsupported currency: {v}')
        return v


class WalletCreate(WalletBase):
    network: Optional[str] = Field(None, description="Сеть для мультисетевых валют")


class WalletResponse(WalletBase):
    id: str = Field(..., description="ID кошелька")
    address: str = Field(..., description="Основной адрес кошелька")
    address_erc20: Optional[str] = Field(None, description="ERC20 адрес (для USDT)")
    address_trc20: Optional[str] = Field(None, description="TRC20 адрес (для USDT)")
    address_bep20: Optional[str] = Field(None, description="BEP20 адрес (для USDT)")
    balance: str = Field(..., description="Общий баланс")
    available_balance: str = Field(..., description="Доступный баланс")
    frozen_balance: str = Field(..., description="Замороженный баланс")
    status: WalletStatus = Field(..., description="Статус кошелька")
    is_default: str = Field(..., description="Является ли кошелек основным")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    class Config:
        from_attributes = True


class WalletListResponse(BaseModel):
    wallets: List[WalletResponse] = Field(..., description="Список кошельков")
    total: int = Field(..., description="Общее количество кошельков")


class BalanceResponse(BaseModel):
    currency: str = Field(..., description="Валюта")
    available: str = Field(..., description="Доступный баланс")
    frozen: str = Field(..., description="Замороженный баланс")
    total: str = Field(..., description="Общий баланс")


class UserBalanceResponse(BaseModel):
    balances: Dict[str, BalanceResponse] = Field(..., description="Балансы по валютам")
    total_usd: Optional[str] = Field(None, description="Общий баланс в USD")


class TransactionBase(BaseModel):
    currency: str = Field(..., description="Валюта")
    amount: str = Field(..., description="Сумма", regex=r'^\d+(\.\d+)?$')
    description: Optional[str] = Field(None, max_length=500, description="Описание")

    @validator('amount')
    def validate_amount(cls, v):
        try:
            amount = Decimal(v)
            if amount <= 0:
                raise ValueError('Amount must be positive')
            if amount > Decimal('1000000000'):
                raise ValueError('Amount too large')
            return str(amount)
        except (ValueError, TypeError):
            raise ValueError('Invalid amount format')


class SendCryptoRequest(TransactionBase):
    to_address: str = Field(..., min_length=10, max_length=100, description="Адрес получателя")
    network: Optional[str] = Field(None, description="Сеть (для мультисетевых валют)")

    @validator('to_address')
    def validate_address(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError('Invalid address format')
        return v.strip()


class TransactionResponse(BaseModel):
    id: str = Field(..., description="ID транзакции")
    type: TransactionType = Field(..., description="Тип транзакции")
    status: TransactionStatus = Field(..., description="Статус транзакции")
    direction: TransactionDirection = Field(..., description="Направление транзакции")
    currency: str = Field(..., description="Валюта")
    amount: str = Field(..., description="Сумма")
    fee: str = Field(..., description="Комиссия")
    from_address: Optional[str] = Field(None, description="Адрес отправителя")
    to_address: Optional[str] = Field(None, description="Адрес получателя")
    network: Optional[str] = Field(None, description="Сеть")
    blockchain_tx_id: Optional[str] = Field(None, description="ID транзакции в блокчейне")
    confirmations: int = Field(0, description="Количество подтверждений")
    required_confirmations: int = Field(1, description="Требуемое количество подтверждений")
    description: Optional[str] = Field(None, description="Описание")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    transactions: List[TransactionResponse] = Field(..., description="Список транзакций")
    total: int = Field(..., description="Общее количество транзакций")
    has_more: bool = Field(..., description="Есть ли еще транзакции")


class TransactionHistoryRequest(BaseModel):
    currency: Optional[str] = Field(None, description="Фильтр по валюте")
    transaction_type: Optional[TransactionType] = Field(None, description="Фильтр по типу")
    status: Optional[TransactionStatus] = Field(None, description="Фильтр по статусу")
    limit: int = Field(50, ge=1, le=100, description="Количество записей")
    offset: int = Field(0, ge=0, description="Смещение")


class AddressValidationRequest(BaseModel):
    address: str = Field(..., min_length=10, max_length=100, description="Адрес для валидации")
    currency: str = Field(..., description="Валюта")
    network: Optional[str] = Field(None, description="Сеть")


class AddressValidationResponse(BaseModel):
    is_valid: bool = Field(..., description="Валиден ли адрес")
    address: str = Field(..., description="Проверенный адрес")
    currency: str = Field(..., description="Валюта")
    network: Optional[str] = Field(None, description="Сеть")
    address_type: Optional[str] = Field(None, description="Тип адреса")


class FeeEstimateRequest(BaseModel):
    currency: str = Field(..., description="Валюта")
    amount: str = Field(..., description="Сумма", regex=r'^\d+(\.\d+)?$')
    to_address: str = Field(..., description="Адрес получателя")
    network: Optional[str] = Field(None, description="Сеть")
    priority: Optional[str] = Field("normal", description="Приоритет (low, normal, high)")

    @validator('priority')
    def validate_priority(cls, v):
        if v not in ['low', 'normal', 'high']:
            raise ValueError('Priority must be low, normal, or high')
        return v


class FeeEstimateResponse(BaseModel):
    currency: str = Field(..., description="Валюта")
    network: Optional[str] = Field(None, description="Сеть")
    fee: str = Field(..., description="Комиссия")
    fee_currency: str = Field(..., description="Валюта комиссии")
    priority: str = Field(..., description="Приоритет")
    estimated_time: Optional[str] = Field(None, description="Примерное время подтверждения")


class WalletStatsResponse(BaseModel):
    total_received: str = Field(..., description="Всего получено")
    total_sent: str = Field(..., description="Всего отправлено")
    transaction_count: int = Field(..., description="Количество транзакций")
    first_transaction_date: Optional[datetime] = Field(None, description="Дата первой транзакции")
    last_transaction_date: Optional[datetime] = Field(None, description="Дата последней транзакции")


class ExchangeRateResponse(BaseModel):
    base_currency: str = Field(..., description="Базовая валюта")
    target_currency: str = Field(..., description="Целевая валюта")
    rate: str = Field(..., description="Курс обмена")
    updated_at: datetime = Field(..., description="Время обновления курса")


class SupportedCurrenciesResponse(BaseModel):
    currencies: List[Dict[str, Any]] = Field(..., description="Список поддерживаемых валют")


class WalletSecurityRequest(BaseModel):
    enable_2fa: Optional[bool] = Field(None, description="Включить 2FA")
    withdrawal_limit: Optional[str] = Field(None, description="Лимит на вывод")
    require_confirmation: Optional[bool] = Field(None, description="Требовать подтверждение")


class WalletSecurityResponse(BaseModel):
    is_2fa_enabled: bool = Field(..., description="Включена ли 2FA")
    withdrawal_limit: Optional[str] = Field(None, description="Лимит на вывод")
    require_confirmation: bool = Field(..., description="Требуется ли подтверждение")
    last_security_update: Optional[datetime] = Field(None, description="Последнее обновление настроек")


class WalletErrorResponse(BaseModel):
    error: str = Field(..., description="Код ошибки")
    message: str = Field(..., description="Сообщение об ошибке")
    details: Optional[Dict[str, Any]] = Field(None, description="Дополнительные детали")


class ValidationErrorResponse(BaseModel):
    error: str = Field("validation_error", description="Код ошибки")
    message: str = Field(..., description="Сообщение об ошибке")
    field_errors: Optional[Dict[str, List[str]]] = Field(None, description="Ошибки полей")
