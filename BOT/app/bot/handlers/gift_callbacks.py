from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger(__name__)
router = Router()


@router.callback_query(F.data.startswith("gift_received_"))
async def gift_received_callback(callback_query: CallbackQuery, state=None):
    try:
        parts = callback_query.data.split("_")
        activation_code = parts[2]
        amount = parts[3]
        currency = parts[4]

        from app.config import settings
        bot_username = settings.bot_username
        start_url = f"https://t.me/{bot_username}?start=start"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🤖 Открыть бота",
                    url=start_url
                )
            ]
        ])

        await callback_query.message.edit_reply_markup(reply_markup=keyboard)
        await callback_query.answer("✅ Подарок уже получен")

    except Exception as e:
        logger.error(
            "Failed to handle gift received callback",
            user_id=callback_query.from_user.id,
            callback_data=callback_query.data,
            error=str(e),
            exc_info=True
        )
        await callback_query.answer("❌ Ошибка", show_alert=True)
