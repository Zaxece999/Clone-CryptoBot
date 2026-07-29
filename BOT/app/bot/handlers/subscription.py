from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import structlog

from app.bot.keyboards.inline import get_subscription_menu_keyboard
from app.bot.utils.texts import get_text

logger = structlog.get_logger(__name__)
router = Router()


@router.message(Command("subscriptions"))
async def cmd_subscriptions(message: Message, language_code: str = "ru"):
    await show_subscription_menu(message, language_code)


@router.callback_query(F.data == "subscription_menu")
async def callback_subscription_menu(callback: CallbackQuery, language_code: str = "ru"):
    subscription_text = f"""
📺 <b>{get_text('subscriptions', language_code)}</b>

{get_text('not_implemented', language_code)}
    """

    keyboard = get_subscription_menu_keyboard(language_code)

    await callback.message.edit_text(
        subscription_text,
        reply_markup=keyboard
    )
    await callback.answer()


async def show_subscription_menu(message: Message, language_code: str = "ru"):
    subscription_text = f"""
📺 <b>{get_text('subscriptions', language_code)}</b>

{get_text('not_implemented', language_code)}
    """

    keyboard = get_subscription_menu_keyboard(language_code)

    await message.answer(
        subscription_text,
        reply_markup=keyboard
    )


async def handle_subscription(message: Message, subscription_id: str, language_code: str = "ru"):
    subscription_text = f"""
📺 <b>Подписка</b>

Подписка ID: <code>{subscription_id}</code>

{get_text('not_implemented', language_code)}
    """

    from app.bot.keyboards.inline import get_main_menu_keyboard
    keyboard = get_main_menu_keyboard(language_code)

    await message.answer(
        subscription_text,
        reply_markup=keyboard
    )
