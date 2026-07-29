from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import secrets
from typing import List

from app.models.invoice import Invoice, InvoiceStatus
from app.models.user import User
from app.bot.utils.texts import get_text
from app.bot.utils.decorators import require_auth
from app.services.invoice import InvoiceService
from app.bot.handlers.invoice_states import InvoiceStates

logger = structlog.get_logger(__name__)
router = Router()

BACK_SYMBOL = "‹"


@router.message(Command("accounts"))
@router.callback_query(F.data == "accounts_menu")
async def show_accounts_menu(callback_or_message: CallbackQuery | Message,
                           language_code: str = "ru",
                           user: User = None):

    accounts_text = f"""
🧾 <b>Счета</b>

Здесь вы можете создать счёт для получения оплаты или сбора средств в криптовалюте. <a href="https://youtu.be/SwLMA4noWGc">Смотрите видеоинструкцию ›</a>

Попробовать счета можно в <a href="https://t.me/CryptoBotDonates/9">@CryptoBotDonates</a>.
    """

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать счёт", callback_data="create_invoice")],
        [InlineKeyboardButton(text="Создать из чата", callback_data="create_from_chat")],
        [InlineKeyboardButton(text="Неоплаченные счета", callback_data="unpaid_invoices")],
        [InlineKeyboardButton(text=f"{BACK_SYMBOL} Назад", callback_data="main_menu")]
    ])

    if isinstance(callback_or_message, CallbackQuery):
        await callback_or_message.message.edit_text(accounts_text, reply_markup=keyboard)
        await callback_or_message.answer()
    else:
        await callback_or_message.answer(accounts_text, reply_markup=keyboard)


@router.callback_query(F.data == "create_invoice")
@require_auth
async def show_create_invoice_type(callback: CallbackQuery,
                               state: FSMContext,
                               language_code: str = "ru"):

    await state.clear()

    type_text = f"""
🧾 <b>Создать счёт</b>

Выберите тип счёта.
    """

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Одноразовый", callback_data="invoice_type_single"),
            InlineKeyboardButton(text="Многоразовый", callback_data="invoice_type_multiple")
        ],
        [InlineKeyboardButton(text=f"{BACK_SYMBOL} Назад к счетам", callback_data="accounts_menu")]
    ])

    await callback.message.edit_text(type_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("invoice_type_"))
@require_auth
async def show_currency_selection(callback: CallbackQuery,
                                state: FSMContext,
                                language_code: str = "ru"):

    invoice_type = callback.data.split("_")[2]

    await state.update_data(invoice_type=invoice_type)
    await state.set_state(InvoiceStates.selecting_currencies)

    currency_text = f"""
🧾 <b>Выбор криптовалют</b>

Выберите одну или больше криптовалют, которыми может быть оплачен счёт.
    """

    keyboard = get_currency_selection_keyboard([])

    await callback.message.edit_text(currency_text, reply_markup=keyboard)
    await callback.answer()


def get_currency_selection_keyboard(selected_currencies: List[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    currencies = [
        ("BTC", "Bitcoin"),
        ("ETH", "Ethereum"),
        ("USDT", "USDT"),
        ("BNB", "BNB"),
        ("SOL", "Solana"),
        ("TON", "Toncoin")
    ]

    for code, name in currencies:
        if code in selected_currencies:
            text = f"· {name} ·"
        else:
            text = name
        builder.button(text=text, callback_data=f"select_currency_{code}")

    builder.adjust(2)

    if selected_currencies:
        builder.button(text="Далее ›", callback_data="next_amount")

    builder.button(text=f"{BACK_SYMBOL} Назад к типу счета", callback_data="back_to_type")

    return builder.as_markup()


@router.callback_query(F.data.startswith("select_currency_"))
@require_auth
async def handle_currency_selection(callback: CallbackQuery,
                                  state: FSMContext,
                                  language_code: str = "ru"):

    currency_code = callback.data.split("_")[2]

    data = await state.get_data()
    selected_currencies = data.get("selected_currencies", [])

    if currency_code in selected_currencies:
        selected_currencies.remove(currency_code)
    else:
        selected_currencies.append(currency_code)

    await state.update_data(selected_currencies=selected_currencies)

    keyboard = get_currency_selection_keyboard(selected_currencies)

    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "next_amount")
@require_auth
async def show_amount_input(callback: CallbackQuery,
                          state: FSMContext,
                          language_code: str = "ru"):

    await state.set_state(InvoiceStates.entering_amount)

    data = await state.get_data()
    selected_currencies = data.get("selected_currencies", [])

    amount_text = f"""
🧾 <b>Ввод суммы</b>

Пришлите сумму счёта в USD с оплатой в {', '.join(selected_currencies)}!!
    """

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{BACK_SYMBOL} Назад к выбору валют", callback_data="back_to_currencies")]
    ])

    await callback.message.edit_text(amount_text, reply_markup=keyboard)
    await callback.answer()


@router.message(InvoiceStates.entering_amount)
@require_auth
async def process_amount_input(message: Message,
                           state: FSMContext,
                           user: User,
                           db: AsyncSession,
                           language_code: str = "ru"):

    try:
        amount = float(message.text.strip())
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return

        data = await state.get_data()
        selected_currencies = data.get("selected_currencies", [])
        invoice_type = data.get("invoice_type", "single")

        invoice = await InvoiceService.create_invoice(
            session=db,
            user_id=user.id,
            amount=amount,
            currencies=selected_currencies,
            invoice_type=invoice_type
        )

        await state.clear()

        await show_created_invoice(message, invoice, language_code)

    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму")


@router.message(InvoiceStates.entering_amount)
@require_auth
async def process_amount_input(message: Message,
                           state: FSMContext,
                           user: User,
                           db: AsyncSession,
                           language_code: str = "ru"):

    try:
        amount = float(message.text.strip())
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return

        data = await state.get_data()
        selected_currencies = data.get("selected_currencies", [])
        invoice_type = data.get("invoice_type", "single")

        invoice = await InvoiceService.create_invoice(
            session=db,
            user_id=user.id,
            amount=amount,
            currencies=selected_currencies,
            invoice_type=invoice_type
        )

        await state.clear()

        await show_created_invoice(message, invoice, language_code)

    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму")


@router.callback_query(F.data == "back_to_type")
@require_auth
async def back_to_type_selection(callback: CallbackQuery,
                               state: FSMContext,
                               language_code: str = "ru"):

    await state.clear()
    await show_create_invoice_type(callback, state, language_code)


@router.callback_query(F.data == "back_to_currencies")
@require_auth
async def back_to_currency_selection(callback: CallbackQuery,
                                   state: FSMContext,
                                   language_code: str = "ru"):

    await state.set_state(InvoiceStates.selecting_currencies)

    currency_text = f"""
🧾 <b>Выбор криптовалют</b>

Выберите одну или больше криптовалют, которыми может быть оплачен счёт.
    """

    data = await state.get_data()
    selected_currencies = data.get("selected_currencies", [])

    keyboard = get_currency_selection_keyboard(selected_currencies)

    await callback.message.edit_text(currency_text, reply_markup=keyboard)
    await callback.answer()
