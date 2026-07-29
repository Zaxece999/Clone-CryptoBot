from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiogram.types import User as TelegramUser
import structlog

from app.models.user import User, UserStatus, UserRole

logger = structlog.get_logger(__name__)


class UserService:
    async def get_user_by_telegram_id(
        self,
        db: AsyncSession,
        telegram_id: int
    ) -> Optional[User]:

        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create_user_from_telegram(
        self,
        db: AsyncSession,
        telegram_user: TelegramUser
    ) -> User:

        user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            language_code=telegram_user.language_code or "ru",
            is_premium=getattr(telegram_user, 'is_premium', False) or False,
            status=UserStatus.ACTIVE,
            role=UserRole.USER,
        )

        user.generate_referral_code()

        db.add(user)
        await db.flush()
        await db.commit()

        logger.info(
            "User created from Telegram",
            user_id=user.id,
            telegram_id=telegram_user.id,
            username=telegram_user.username,
        )

        return user

    async def update_user_from_telegram(
        self,
        db: AsyncSession,
        user: User,
        telegram_user: TelegramUser
    ) -> User:

        user.username = telegram_user.username
        user.first_name = telegram_user.first_name
        user.last_name = telegram_user.last_name
        user.language_code = telegram_user.language_code or user.language_code
        user.is_premium = getattr(telegram_user, 'is_premium', False) or False
        user.update_activity()

        await db.commit()

        logger.info(
            "User updated from Telegram",
            user_id=user.id,
            telegram_id=telegram_user.id,
            username=telegram_user.username,
        )

        return user

    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()


user_service = UserService()
