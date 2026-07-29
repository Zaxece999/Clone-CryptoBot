from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
import structlog

from app.config import settings
from app.models.user import User, UserStatus, UserRole
from app.utils.exceptions import (
    AuthenticationError,
    AuthorizationError,
    UserNotFoundError,
    UserBlockedError,
)

logger = structlog.get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self):
        pass

    async def get_or_create_user_by_telegram(
        self,
        db: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None,
        is_premium: Optional[bool] = None,
    ) -> User:

        try:
            result = await db.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if user:
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user.language_code = language_code or user.language_code
                if is_premium is not None:
                    user.is_premium = is_premium
                user.update_activity()

                logger.info(
                    "User updated",
                    user_id=user.id,
                    telegram_id=telegram_id,
                    username=username,
                )
            else:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language_code=language_code or "ru",
                    is_premium=is_premium if is_premium is not None else False,
                    status=UserStatus.ACTIVE,
                    role=UserRole.USER,
                )

                user.generate_referral_code()

                if hasattr(user, 'p2p_nickname'):
                    user.generate_p2p_nickname()

                db.add(user)
                await db.flush()

                logger.info(
                    "User created",
                    user_id=user.id,
                    telegram_id=telegram_id,
                    username=username,
                )

            await db.commit()
            return user

        except IntegrityError:
            await db.rollback()

            result = await db.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if user:
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user.language_code = language_code or user.language_code
                if is_premium is not None:
                    user.is_premium = is_premium
                user.update_activity()

                logger.info(
                    "User updated after integrity error",
                    user_id=user.id,
                    telegram_id=telegram_id,
                    username=username,
                )

                await db.commit()
                return user
            else:
                logger.error(
                    "User not found after integrity error",
                    telegram_id=telegram_id,
                )
                raise UserNotFoundError(f"User with telegram_id {telegram_id} not found after integrity error")

    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_telegram_id(
        self,
        db: AsyncSession,
        telegram_id: int
    ) -> Optional[User]:

        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_username(
        self,
        db: AsyncSession,
        username: str
    ) -> Optional[User]:

        result = await db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def authenticate_user(
        self,
        db: AsyncSession,
        telegram_id: int
    ) -> User:

        user = await self.get_user_by_telegram_id(db, telegram_id)

        if not user:
            raise UserNotFoundError(f"User with telegram_id {telegram_id} not found")

        if user.is_blocked():
            raise UserBlockedError(
                f"User {user.id} is blocked",
                details={
                    "blocked_at": user.blocked_at.isoformat() if user.blocked_at else None,
                    "blocked_reason": user.blocked_reason,
                    "blocked_until": user.blocked_until.isoformat() if user.blocked_until else None,
                }
            )

        user.update_activity()
        await db.commit()

        return user

    async def get_current_user_by_telegram_id(self, db: AsyncSession, telegram_id: int) -> User:
        user = await self.get_user_by_telegram_id(db, telegram_id)

        if not user:
            raise UserNotFoundError(f"User with telegram_id {telegram_id} not found")

        if user.is_blocked():
            raise UserBlockedError(f"User {user.id} is blocked")

        return user

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    async def set_user_pin(self, db: AsyncSession, user: User, pin: str) -> None:
        user.pin_code_hash = self.hash_password(pin)
        await db.commit()

        logger.info("PIN code set", user_id=user.id)

    async def verify_user_pin(self, user: User, pin: str) -> bool:
        if not user.pin_code_hash:
            return False

        return self.verify_password(pin, user.pin_code_hash)

    async def check_permissions(
        self,
        user: User,
        required_role: UserRole = UserRole.USER
    ) -> None:

        role_hierarchy = {
            UserRole.USER: 0,
            UserRole.MODERATOR: 1,
            UserRole.ADMIN: 2,
        }

        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        if user_level < required_level:
            raise AuthorizationError(
                f"Insufficient permissions: required {required_role.value}, got {user.role.value}"
            )


auth_service = AuthService()
