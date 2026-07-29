from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.models.check import CheckStatus, CheckType

class CheckRestrictions(BaseModel):

    is_gift: bool = Field(default=False, description="Является ли чек подарком")
    password: Optional[str] = Field(None, description="Пароль для активации")

    bound_user_id: Optional[int] = Field(None, description="ID пользователя, за которым закреплен чек")
    bound_username: Optional[str] = Field(None, description="@username пользователя в Telegram")

    premium_only: bool = Field(default=False, description="Только для Telegram Premium")
    new_users_only: bool = Field(default=False, description="Только для новых пользователей (2 дня)")

    subscription_required: bool = Field(default=False, description="Включена ли проверка подписки")
    subscription_chat_ids: List[int] = Field(default_factory=list, description="ID каналов/групп для проверки, до 3-х")

    image_file_id: Optional[str] = Field(None, description="FileID прикрепленного изображения")
    description: Optional[str] = Field(None, description="Описание чека")

    @validator('subscription_chat_ids')
    def validate_subscription_chats(cls, v):
        if len(v) > 3:
            raise ValueError('Можно добавить не более 3 каналов/групп')
        return v

class CheckBase(BaseModel):
    currency: str = Field(..., description="Валюта чека")
    amount: str = Field(..., description="Сумма чека", regex=r'^\d+(\.\d+)?$')
    description: Optional[str] = Field(None, max_length=500, description="Описание чека")
    comment: Optional[str] = Field(None, max_length=1000, description="Комментарий к чеку")
    restrictions: CheckRestrictions = Field(default_factory=CheckRestrictions, description="Ограничения чека")

    @validator('currency')
    def validate_currency(cls, v):
        supported_currencies = [
            'BTC', 'ETH', 'USDT', 'LTC', 'BNB', 'TRX', 'TON'
        ]
        if v not in supported_currencies:
            raise ValueError(f'Unsupported currency: {v}')
        return v)
    def validate_amount(cls, v):
        try:
            amount = Decimal(v)
            if amount <= 0:
                raise ValueError('Amount must be positive')
            if amount > Decimal('1000000'):
                raise ValueError('Amount too large')
            return str(amount)
        except (ValueError, TypeError):
            raise ValueError('Invalid amount format')

class CheckCreateRequest(CheckBase):
    type: CheckType = Field(CheckType.ONE_TIME, description="Тип чека")
    password: Optional[str] = Field(None, min_length=4, max_length=50, description="Пароль для активации")
    target_username: Optional[str] = Field(None, description="Username целевого пользователя (для персональных чеков)")
    max_activations: Optional[int] = Field(None, ge=1, le=1000, description="Максимальное количество активаций")
    expires_in_hours: Optional[int] = Field(None, ge=1, le=720, description="Срок действия в часах (до 30 дней)")

    @validator('max_activations')
    def validate_max_activations(cls, v, values):
        if v is not None and v > 1:
            check_type = values.get('type')
            if check_type != CheckType.MULTI_USE:
                raise ValueError('Only multi-use checks can have max_activations > 1')
        return v

    @validator('target_username')
    def validate_target_username(cls, v, values):
        check_type = values.get('type')
        if check_type == CheckType.PERSONAL and not v:
            raise ValueError('Personal check requires target_username')
        return v

class CheckActivateRequest(BaseModel):
    check_id: str = Field(..., min_length=8, max_length=8, description="ID чека")
    password: Optional[str] = Field(None, description="Пароль (если требуется)")

    @validator('check_id')
    def validate_check_id(cls, v):
        if not v.isalnum():
            raise ValueError('Check ID must contain only letters and numbers')
        return v.upper()

class CheckResponse(CheckBase):
    id: str = Field(..., description="Внутренний ID чека")
    check_id: str = Field(..., description="Публичный ID чека")
    creator_id: int = Field(..., description="ID создателя")
    activator_id: Optional[int] = Field(None, description="ID активатора")
    type: CheckType = Field(..., description="Тип чека")
    status: CheckStatus = Field(..., description="Статус чека")
    max_activations: Optional[int] = Field(None, description="Максимальное количество активаций")
    current_activations: int = Field(..., description="Текущее количество активаций")
    target_user_id: Optional[int] = Field(None, description="ID целевого пользователя")
    expires_at: Optional[datetime] = Field(None, description="Дата истечения")
    activated_at: Optional[datetime] = Field(None, description="Дата активации")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    is_active: bool = Field(..., description="Активен ли чек")
    is_expired: bool = Field(..., description="Истек ли чек")
    remaining_activations: Optional[int] = Field(None, description="Оставшиеся активации")
    expiry_info: Dict[str, Any] = Field(..., description="Информация о сроке действия")

    class Config:
        from_attributes = True

    @validator('remaining_activations', pre=True, always=True)
    def set_remaining_activations(cls, v, values):
        max_activations = values.get('max_activations')
        current_activations = values.get('current_activations', 0)

        if max_activations is None:
            return None

        return max(0, max_activations - current_activations)

class CheckListResponse(BaseModel):
    checks: List[CheckResponse] = Field(..., description="Список чеков")
    total: int = Field(..., description="Общее количество чеков")
    has_more: bool = Field(..., description="Есть ли еще чеки")

class CheckActivationResponse(BaseModel):
    id: str = Field(..., description="ID активации")
    check_id: str = Field(..., description="ID чека")
    user_id: int = Field(..., description="ID активатора")
    amount_received: str = Field(..., description="Полученная сумма")
    activated_at: datetime = Field(..., description="Дата активации")

    check: CheckResponse = Field(..., description="Данные чека")

    class Config:
        from_attributes = True

class CheckActivationListResponse(BaseModel):
    activations: List[CheckActivationResponse] = Field(..., description="Список активаций")
    total: int = Field(..., description="Общее количество активаций")
    has_more: bool = Field(..., description="Есть ли еще активации")

class CheckStatsResponse(BaseModel):
    created: Dict[str, Any] = Field(..., description="Статистика созданных чеков")
    activated: Dict[str, Any] = Field(..., description="Статистика активированных чеков")

class CheckHistoryRequest(BaseModel):
    status: Optional[CheckStatus] = Field(None, description="Фильтр по статусу")
    type: Optional[CheckType] = Field(None, description="Фильтр по типу")
    currency: Optional[str] = Field(None, description="Фильтр по валюте")
    limit: int = Field(50, ge=1, le=100, description="Количество записей")
    offset: int = Field(0, ge=0, description="Смещение")

class CheckInfoResponse(BaseModel):
    check_id: str = Field(..., description="ID чека")
    currency: str = Field(..., description="Валюта")
    amount: str = Field(..., description="Сумма")
    type: CheckType = Field(..., description="Тип чека")
    status: CheckStatus = Field(..., description="Статус чека")
    description: Optional[str] = Field(None, description="Описание")
    requires_password: bool = Field(..., description="Требует ли пароль")
    max_activations: Optional[int] = Field(None, description="Максимальное количество активаций")
    current_activations: int = Field(..., description="Текущее количество активаций")
    remaining_activations: Optional[int] = Field(None, description="Оставшиеся активации")
    expires_at: Optional[datetime] = Field(None, description="Дата истечения")
    is_active: bool = Field(..., description="Можно ли активировать")
    is_expired: bool = Field(..., description="Истек ли чек")
    expiry_info: Dict[str, Any] = Field(..., description="Информация о сроке действия")
    created_at: datetime = Field(..., description="Дата создания")

class CheckUrlResponse(BaseModel):
    check_id: str = Field(..., description="ID чека")
    url: str = Field(..., description="URL для активации чека")
    qr_code_url: Optional[str] = Field(None, description="URL QR-кода")

class CheckValidationResponse(BaseModel):
    is_valid: bool = Field(..., description="Валиден ли чек")
    check_id: str = Field(..., description="ID чека")
    can_activate: bool = Field(..., description="Можно ли активировать")
    reason: Optional[str] = Field(None, description="Причина, если нельзя активировать")
    check_info: Optional[CheckInfoResponse] = Field(None, description="Информация о чеке")

class CheckErrorResponse(BaseModel):
    error: str = Field(..., description="Код ошибки")
    message: str = Field(..., description="Сообщение об ошибке")
    check_id: Optional[str] = Field(None, description="ID чека")
    details: Optional[Dict[str, Any]] = Field(None, description="Дополнительные детали")

class LegacyCheckCreateRequest(BaseModel):
    asset: str = Field(..., description="Валюта (legacy)")
    amount: str = Field(..., description="Сумма")
    pin_to_user_id: Optional[int] = Field(None, description="ID пользователя для персонального чека")
    pin_to_username: Optional[str] = Field(None, description="Username для персонального чека")

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

class LegacyCheckResponse(BaseModel):
    ok: bool = Field(True, description="Успешность операции")
    result: Dict[str, Any] = Field(..., description="Результат")
    error: Optional[Dict[str, str]] = Field(None, description="Ошибка")

class CheckTemplateResponse(BaseModel):
    templates: List[Dict[str, Any]] = Field(..., description="Шаблоны чеков")

class CheckBulkCreateRequest(BaseModel):
    currency: str = Field(..., description="Валюта")
    amount: str = Field(..., description="Сумма каждого чека")
    count: int = Field(..., ge=1, le=100, description="Количество чеков")
    type: CheckType = Field(CheckType.ONE_TIME, description="Тип чеков")
    expires_in_hours: Optional[int] = Field(None, ge=1, le=720, description="Срок действия в часах")
    description: Optional[str] = Field(None, max_length=500, description="Описание")

class CheckBulkCreateResponse(BaseModel):
    created_count: int = Field(..., description="Количество созданных чеков")
    total_amount: str = Field(..., description="Общая сумма")
    currency: str = Field(..., description="Валюта")
    checks: List[CheckResponse] = Field(..., description="Созданные чеки")
    download_url: Optional[str] = Field(None, description="URL для скачивания списка чеков")
