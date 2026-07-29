from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import structlog

from app.database import get_async_db
from app.services.auth import auth_service
from app.schemas.user import (
    TelegramAuthData,
    TokenResponse,
    TokenRefresh,
    UserResponse,
    PinCodeSet,
    PinCodeVerify,
    UserSettings,
    UserSettingsUpdate,
)
from app.models.user import User
from app.utils.exceptions import (
    AuthenticationError,
    InvalidTokenError,
    UserNotFoundError,
)

logger = structlog.get_logger(__name__)
router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> User:

    try:
        token = credentials.credentials
        user = await auth_service.get_current_user(db, token)
        return user
    except (InvalidTokenError, UserNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/getMe")
async def get_me():
    return {
        "ok": True,
        "result": {
            "app_id": 12345,
            "name": "CryptoBot Clone",
            "payment_processing_bot_username": "CryptoBotClone",
            "supported_currencies": ["BTC", "ETH", "USDT", "LTC", "BNB", "TRX", "TON", "GRAM"]
        },
        "error": None
    }


@router.post("/telegram-auth", response_model=TokenResponse)
async def telegram_auth(
    auth_data: TelegramAuthData,
    db: AsyncSession = Depends(get_async_db)
):

    try:
        user = await auth_service.get_or_create_user_by_telegram(
            db=db,
            telegram_id=auth_data.telegram_id,
            username=auth_data.username,
            first_name=auth_data.first_name,
            last_name=auth_data.last_name,
            language_code=auth_data.language_code,
            is_premium=auth_data.is_premium,
        )

        token_data = {"sub": str(user.id), "telegram_id": user.telegram_id}
        access_token = auth_service.create_access_token(token_data)
        refresh_token = auth_service.create_refresh_token(token_data)

        logger.info(
            "User authenticated via Telegram",
            user_id=user.id,
            telegram_id=user.telegram_id,
        )

        return {
            "ok": True,
            "result": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": auth_service.access_token_expire_minutes * 60,
            },
            "error": None
        }

    except Exception as e:
        logger.error("❌ Ошибка Telegram авторизации", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {str(e)}"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_async_db)
):

    try:
        payload = auth_service.verify_token(token_data.refresh_token, "refresh")
        user_id = payload.get("sub")

        if not user_id:
            raise InvalidTokenError("Token does not contain user ID")

        user = await auth_service.get_user_by_id(db, int(user_id))
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        token_data = {"sub": str(user.id), "telegram_id": user.telegram_id}
        access_token = auth_service.create_access_token(token_data)
        new_refresh_token = auth_service.create_refresh_token(token_data)

        return {
            "ok": True,
            "result": {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": auth_service.access_token_expire_minutes * 60,
            },
            "error": None
        }

    except Exception as e:
        logger.error("❌ Обновление токена не удалось", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token refresh failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):

    return {
        "ok": True,
        "result": UserResponse.from_orm(current_user),
        "error": None
    }


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):

    try:
        update_data = user_update.dict(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(current_user, field):
                setattr(current_user, field, value)

        await db.commit()
        await db.refresh(current_user)

        logger.info("✅ Пользователь обновлен", user_id=current_user.id)

        return {
            "ok": True,
            "result": UserResponse.from_orm(current_user),
            "error": None
        }

    except Exception as e:
        logger.error("❌ Обновление пользователя не удалось", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Update failed: {str(e)}"
        )


@router.post("/pin/set")
async def set_pin_code(
    pin_data: PinCodeSet,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):

    try:
        await auth_service.set_user_pin(db, current_user, pin_data.pin_code)

        return {
            "ok": True,
            "result": {"message": "PIN code set successfully"},
            "error": None
        }

    except Exception as e:
        logger.error("❌ Установка PIN не удалась", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PIN set failed: {str(e)}"
        )


@router.post("/pin/verify")
async def verify_pin_code(
    pin_data: PinCodeVerify,
    current_user: User = Depends(get_current_user)
):

    try:
        is_valid = await auth_service.verify_user_pin(current_user, pin_data.pin_code)

        return {
            "ok": True,
            "result": {"valid": is_valid},
            "error": None
        }

    except Exception as e:
        logger.error("❌ Проверка PIN не удалась", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PIN verify failed: {str(e)}"
        )


@router.get("/settings", response_model=UserSettings)
async def get_user_settings(
    current_user: User = Depends(get_current_user)
):

    return {
        "ok": True,
        "result": {
            "language_code": current_user.language_code,
            "timezone": current_user.timezone,
            "notifications_enabled": current_user.notifications_enabled,
            "email_notifications": current_user.email_notifications,
            "sms_notifications": current_user.sms_notifications,
            "two_factor_enabled": current_user.two_factor_enabled,
        },
        "error": None
    }


@router.put("/settings", response_model=UserSettings)
async def update_user_settings(
    settings_update: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):

    try:
        update_data = settings_update.dict(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(current_user, field):
                setattr(current_user, field, value)

        await db.commit()

        logger.info("✅ Настройки пользователя обновлены", user_id=current_user.id)

        return {
            "ok": True,
            "result": {
                "language_code": current_user.language_code,
                "timezone": current_user.timezone,
                "notifications_enabled": current_user.notifications_enabled,
                "email_notifications": current_user.email_notifications,
                "sms_notifications": current_user.sms_notifications,
                "two_factor_enabled": current_user.two_factor_enabled,
            },
            "error": None
        }

    except Exception as e:
        logger.error("❌ Обновление настроек не удалось", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Settings update failed: {str(e)}"
        )


@router.delete("/me")
async def delete_current_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):

    try:
        current_user.status = "suspended"
        current_user.blocked_reason = "User requested account deletion"

        await db.commit()

        logger.info("✅ Пользователь деактивирован", user_id=current_user.id)

        return {
            "ok": True,
            "result": {"message": "Account deactivated successfully"},
            "error": None
        }

    except Exception as e:
        logger.error("❌ Удаление пользователя не удалось", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Account deletion failed: {str(e)}"
        )
