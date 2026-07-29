from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, User
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.database import get_async_db
from app.services.auth import auth_service

logger = structlog.get_logger(__name__)


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:

        user: User = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        logger.info(
            "User interaction",
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code,
            is_bot=user.is_bot,
            is_premium=getattr(user, 'is_premium', False),
        )

        if user.is_bot:
            logger.warning("🤖 Обнаружен бот-пользователь", user_id=user.id)
            return

        data["user"] = user
        data["user_id"] = user.id
        data["language_code"] = user.language_code or "ru"

        try:
            async for db_session in get_async_db():
                try:
                    db_user = await auth_service.get_or_create_user_by_telegram(
                        db=db_session,
                        telegram_id=user.id,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        language_code=user.language_code,
                        is_premium=getattr(user, 'is_premium', False),
                    )

                    data["db_user"] = db_user
                    data["db"] = db_session
                    data["language_code"] = db_user.language_code

                    logger.info(
                        "User authenticated",
                        user_id=user.id,
                        db_user_id=db_user.id,
                        username=db_user.username
                    )

                    return await handler(event, data)

                except Exception as db_error:
                    logger.error(
                        "Database error in auth middleware",
                        user_id=user.id,
                        error=str(db_error),
                        exc_info=True
                    )

                    data["db_user"] = None
                    data["db"] = None

                    return await handler(event, data)

                break

        except Exception as e:
            logger.error(
                "Critical error in auth middleware",
                user_id=user.id,
                error=str(e),
                exc_info=True
            )

            data["db_user"] = None
            data["db"] = None

            return await handler(event, data)
