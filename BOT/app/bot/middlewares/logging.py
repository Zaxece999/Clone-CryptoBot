from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
import time
import structlog

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:

        start_time = time.time()

        event_type = "message" if isinstance(event, Message) else "callback_query"

        log_data = {
            "event_type": event_type,
            "user_id": event.from_user.id if event.from_user else None,
            "chat_id": event.chat.id if hasattr(event, 'chat') and event.chat else None,
        }

        if isinstance(event, Message):
            log_data.update({
                "message_id": event.message_id,
                "text": event.text[:100] if event.text else None,
                "content_type": event.content_type,
                "chat_type": event.chat.type if event.chat else None,
            })

            if event.text and event.text.startswith('/'):
                log_data["command"] = event.text.split()[0]

        elif isinstance(event, CallbackQuery):
            log_data.update({
                "callback_data": event.data,
                "message_id": event.message.message_id if event.message else None,
            })

        logger.info("🎯 Событие началось", **log_data)

        try:
            result = await handler(event, data)

            processing_time = time.time() - start_time

            logger.info(
                "Event completed",
                processing_time=processing_time,
                **log_data
            )

            return result

        except Exception as e:
            processing_time = time.time() - start_time

            logger.error(
                "Event failed",
                error=str(e),
                processing_time=processing_time,
                exc_info=True,
                **log_data
            )

            raise
