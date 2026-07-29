from functools import wraps
from typing import Callable, Any
from aiogram.types import Message, CallbackQuery, InlineQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import inspect

from app.database import get_async_db
from app.services.user import user_service

logger = structlog.get_logger(__name__)


def require_auth(handler: Callable) -> Callable:
    @wraps(handler)
    async def wrapper(event, state: FSMContext = None, *args, **kwargs):
        try:
            telegram_user = None

            if isinstance(event, (Message, CallbackQuery)):
                telegram_user = event.from_user
            elif isinstance(event, InlineQuery):
                telegram_user = event.from_user

            if not telegram_user:
                if isinstance(event, (Message, CallbackQuery)):
                    await event.answer("❌ Ошибка авторизации")
                return None

            async for db in get_async_db():
                try:
                    user = await user_service.get_user_by_telegram_id(db, telegram_user.id)

                    if not user:
                        user = await user_service.create_user_from_telegram(db, telegram_user)
                        logger.info(
                            "New user created",
                            user_id=user.id,
                            telegram_id=telegram_user.id,
                            username=telegram_user.username
                        )

                    await user_service.update_user_from_telegram(db, user, telegram_user)

                    handler_kwargs = {
                        'event': event,
                        'state': state,
                        'db': db,
                        'current_user': user,
                        'user': user,
                        **kwargs
                    }

                    if isinstance(event, Message):
                        handler_kwargs['message'] = event
                    elif isinstance(event, CallbackQuery):
                        handler_kwargs['callback'] = event
                    elif isinstance(event, InlineQuery):
                        handler_kwargs['inline_query'] = event

                    sig = inspect.signature(handler)
                    filtered_kwargs = {k: v for k, v in handler_kwargs.items() if k in sig.parameters}

                    return await handler(**filtered_kwargs)

                except Exception as e:
                    logger.error(
                        "Auth decorator error",
                        telegram_id=telegram_user.id,
                        error=str(e),
                        exc_info=True
                    )

                    if isinstance(event, (Message, CallbackQuery)):
                        await event.answer("❌ Ошибка авторизации. Попробуйте позже.")
                    return None

        except Exception as e:
            logger.error(
                "Auth decorator wrapper error",
                error=str(e),
                exc_info=True
            )
            return None

    return wrapper


def admin_required(handler: Callable) -> Callable:
    @wraps(handler)
    async def wrapper(event, state: FSMContext = None, *args, **kwargs):
        try:
            telegram_user = None

            if isinstance(event, (Message, CallbackQuery)):
                telegram_user = event.from_user
            elif isinstance(event, InlineQuery):
                telegram_user = event.from_user

            if not telegram_user:
                return None

            async for db in get_async_db():
                user = await user_service.get_user_by_telegram_id(db, telegram_user.id)
                if not user:
                    user = await user_service.create_user_from_telegram(db, telegram_user)

                await user_service.update_user_from_telegram(db, user, telegram_user)

                if not user.is_admin:
                    if isinstance(event, (Message, CallbackQuery)):
                        await event.answer("❌ Недостаточно прав доступа")
                    return None

                handler_kwargs = {
                    'event': event,
                    'state': state,
                    'db': db,
                    'current_user': user,
                    **kwargs
                }

                if isinstance(event, CallbackQuery):
                    handler_kwargs['callback'] = event

                sig = inspect.signature(handler)
                filtered_kwargs = {k: v for k, v in handler_kwargs.items() if k in sig.parameters}

                return await handler(**filtered_kwargs)

        except Exception as e:
            logger.error("Admin decorator error", error=str(e))
            return None

    return wrapper


def premium_required(handler: Callable) -> Callable:
    @wraps(handler)
    async def wrapper(event, state: FSMContext = None, *args, **kwargs):
        try:
            telegram_user = None

            if isinstance(event, (Message, CallbackQuery)):
                telegram_user = event.from_user
            elif isinstance(event, InlineQuery):
                telegram_user = event.from_user

            if not telegram_user:
                return None

            async for db in get_async_db():
                user = await user_service.get_user_by_telegram_id(db, telegram_user.id)
                if not user:
                    user = await user_service.create_user_from_telegram(db, telegram_user)

                await user_service.update_user_from_telegram(db, user, telegram_user)

                if not user.is_premium:
                    if isinstance(event, (Message, CallbackQuery)):
                        await event.answer("❌ Требуется Premium статус")
                    return None

                handler_kwargs = {
                    'event': event,
                    'state': state,
                    'db': db,
                    'current_user': user,
                    **kwargs
                }

                if isinstance(event, CallbackQuery):
                    handler_kwargs['callback'] = event

                sig = inspect.signature(handler)
                filtered_kwargs = {k: v for k, v in handler_kwargs.items() if k in sig.parameters}

                return await handler(**filtered_kwargs)

        except Exception as e:
            logger.error("Premium decorator error", error=str(e))
            return None

    return wrapper


def verified_required(handler: Callable) -> Callable:
    @wraps(handler)
    async def wrapper(event, state: FSMContext = None, *args, **kwargs):
        try:
            telegram_user = None

            if isinstance(event, (Message, CallbackQuery)):
                telegram_user = event.from_user
            elif isinstance(event, InlineQuery):
                telegram_user = event.from_user

            if not telegram_user:
                return None

            async for db in get_async_db():
                user = await user_service.get_user_by_telegram_id(db, telegram_user.id)
                if not user:
                    user = await user_service.create_user_from_telegram(db, telegram_user)

                await user_service.update_user_from_telegram(db, user, telegram_user)

                if not user.is_verified:
                    if isinstance(event, (Message, CallbackQuery)):
                        await event.answer("❌ Требуется верификация")
                    return None

                handler_kwargs = {
                    'event': event,
                    'state': state,
                    'db': db,
                    'current_user': user,
                    **kwargs
                }

                if isinstance(event, CallbackQuery):
                    handler_kwargs['callback'] = event

                sig = inspect.signature(handler)
                filtered_kwargs = {k: v for k, v in handler_kwargs.items() if k in sig.parameters}

                return await handler(**filtered_kwargs)

        except Exception as e:
            logger.error("Verified decorator error", error=str(e))
            return None

    return wrapper


def rate_limit(calls: int = 5, period: int = 60):
    def decorator(handler: Callable) -> Callable:
        @wraps(handler)
        async def wrapper(event, state: FSMContext = None, *args, **kwargs):
            return await handler(event, state, *args, **kwargs)

        return wrapper

    return decorator


def log_handler_call(handler: Callable) -> Callable:
    @wraps(handler)
    async def wrapper(event, state: FSMContext = None, *args, **kwargs):
        try:
            if isinstance(event, Message):
                telegram_user = event.from_user
                event_type = "message"
                event_data = {
                    "text": event.text,
                    "chat_id": event.chat.id,
                    "message_id": event.message_id
                }
            elif isinstance(event, CallbackQuery):
                telegram_user = event.from_user
                event_type = "callback_query"
                event_data = {
                    "data": event.data,
                    "chat_id": event.message.chat.id if event.message else None,
                    "message_id": event.message.message_id if event.message else None
                }
            elif isinstance(event, InlineQuery):
                telegram_user = event.from_user
                event_type = "inline_query"
                event_data = {
                    "query": event.query,
                    "user_id": event.from_user.id
                }
            else:
                telegram_user = None
                event_type = "unknown"
                event_data = {}

            logger.info(
                f"Handler called: {handler.__name__}",
                handler=handler.__name__,
                event_type=event_type,
                user_id=telegram_user.id if telegram_user else None,
                username=telegram_user.username if telegram_user else None,
                event_data=event_data
            )

            result = await handler(event, state, *args, **kwargs)

            logger.info(
                f"Handler completed: {handler.__name__}",
                handler=handler.__name__,
                user_id=telegram_user.id if telegram_user else None
            )

            return result

        except Exception as e:
            logger.error(
                f"Handler error: {handler.__name__}",
                handler=handler.__name__,
                error=str(e),
                exc_info=True
            )
            raise

    return wrapper


def handle_errors(handler: Callable) -> Callable:
    @wraps(handler)
    async def wrapper(event, state: FSMContext = None, *args, **kwargs):
        try:
            return await handler(event, state, *args, **kwargs)

        except Exception as e:
            logger.error(
                f"Unhandled error in {handler.__name__}",
                handler=handler.__name__,
                error=str(e),
                exc_info=True
            )

            error_text = "❌ Произошла ошибка. Попробуйте позже."

            if isinstance(event, Message):
                await event.answer(error_text)
            elif isinstance(event, CallbackQuery):
                await event.answer(error_text)

    return wrapper


def typing_action(handler: Callable) -> Callable:
    @wraps(handler)
    async def wrapper(event, state: FSMContext = None, *args, **kwargs):
        if isinstance(event, Message):
            bot = event.bot
            chat_id = event.chat.id
        elif isinstance(event, CallbackQuery):
            bot = event.bot
            chat_id = event.message.chat.id if event.message else None
        else:
            return await handler(event, state, *args, **kwargs)

        if chat_id:
            await bot.send_chat_action(chat_id, "typing")

        return await handler(event, state, *args, **kwargs)

    return wrapper


def get_db_session(handler: Callable) -> Callable:
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        async for db in get_async_db():
            try:
                kwargs['db'] = db
                return await handler(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Database session error in {handler.__name__}",
                    handler=handler.__name__,
                    error=str(e),
                    exc_info=True
                )
                raise

    return wrapper
