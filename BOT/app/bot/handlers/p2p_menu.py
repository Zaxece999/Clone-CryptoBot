from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import structlog

from app.database import get_async_db
from app.bot.keyboards.p2p import get_p2p_menu_keyboard

logger = structlog.get_logger(__name__)
router = Router()


@router.message(Command("p2p_menu"))
async def cmd_p2p_menu(message: Message, language_code: str = "ru"):
    await show_p2p_menu(message, language_code)


@router.callback_query(F.data == "p2p_menu")
async def callback_p2p_menu(callback: CallbackQuery, language_code: str = "ru"):
    await show_p2p_menu(callback.message, language_code)
    await callback.answer()


async def show_p2p_menu(message: Message, language_code: str = "ru"):
    text = (
        "💠 Здесь вы можете <a href=\"https://help.send.tg/ru/articles/9819562-%D0%BA%D0%B0%D0%BA-%D0%BA%D1%83%D0%BF%D0%B8%D1%82%D1%8C-%D0%BC%D0%BE%D0%BD%D0%B5%D1%82%D1%8B\">купить</a> "
        "или <a href=\"https://help.send.tg/ru/articles/9819582-%D0%BA%D0%B0%D0%BA-%D0%BF%D1%80%D0%BE%D0%B4%D0%B0%D1%82%D1%8C-%D0%BC%D0%BE%D0%BD%D0%B5%D1%82%D1%8B\">продать</a> "
        "криптовалюту переводом на карту или электронный кошелёк. "
        "Смотреть <a href=\"https://youtu.be/PuD59ai_VNg\">видеоинструкцию</a> ›"
    )

    keyboard = get_p2p_menu_keyboard()

    if hasattr(message, 'edit_text'):
        await message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)
    else:
        await message.answer(text, reply_markup=keyboard, disable_web_page_preview=True)
