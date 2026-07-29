from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InlineQuery, InlineQueryResultArticle, InputTextMessageContent, BufferedInputFile, InputMediaPhoto
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import secrets
from typing import List
from app.config import settings

from app.models.invoice import Invoice, InvoiceStatus
from app.models.user import User
from app.bot.utils.texts import get_text
from app.bot.keyboards.inline import get_main_menu_keyboard
from app.bot.utils.formatters import format_currency, format_invoice
from app.services.invoice import InvoiceService
from app.bot.handlers.invoice_states import InvoiceStates
from app.bot.utils.decorators import require_auth

logger = structlog.get_logger(__name__)
router = Router()

BACK_SYMBOL = "‹"

async def safe_edit_message(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup = None, parse_mode: str = "HTML", remove_photo: bool = False):
    try:
        if callback.message.photo and not remove_photo:
            media = InputMediaPhoto(
                media=callback.message.photo[-1].file_id,
                caption=text,
                parse_mode=parse_mode
            )
            await callback.message.edit_media(media=media, reply_markup=reply_markup)
        else:
            await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        logger.error("Failed to edit message", error=str(e))
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)

@router.message(Command("accounts"))
@router.callback_query(F.data == "accounts_menu")
async def show_accounts_menu(callback_or_message: CallbackQuery | Message,
                           language_code: str = "ru"):

    accounts_text = f"""
<b>Счета</b>

Здесь вы можете создать счёт для получения оплаты или сбора средств в криптовалюте. <a href="https://youtu.be/SwLMA4noWGc">Смотрите видеоинструкцию ›</a>

Попробовать счета можно в <a href="https://t.me/CryptoBotDonates/9">@CryptoBotDonates</a>.
    """

    keyboard_buttons = [
        [InlineKeyboardButton(text="Создать счёт", callback_data="create_invoice")],
        [InlineKeyboardButton(text="Создать из чата", callback_data="create_from_chat")],
        [InlineKeyboardButton(text="Мои счета", callback_data="my_invoices")]
    ]


    keyboard_buttons.append([
        InlineKeyboardButton(text=f"{BACK_SYMBOL} Назад", callback_data="main_menu")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    if isinstance(callback_or_message, CallbackQuery):
        await safe_edit_message(callback_or_message, accounts_text, keyboard)
        await callback_or_message.answer()
    else:
        await callback_or_message.answer(accounts_text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "invoice_menu")
async def show_invoice_menu(callback: CallbackQuery, db: AsyncSession):
    try:
        from app.services.auth import auth_service

        user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        active_invoices = await InvoiceService.get_user_invoices(db, user.id, status="active")
        unpaid_invoices = await InvoiceService.get_unpaid_invoices(db, user.id)

        active_count = len(active_invoices)
        unpaid_count = len(unpaid_invoices)

        accounts_text = (
            "Здесь вы можете создать счёт для получения оплаты или сбора средств в криптовалюте. "
            '<a href="https://youtu.be/SwLMA4noWGc">Смотрите видеоинструкцию ›</a>\n\n'
            'Попробовать счета можно в <a href="https://t.me/CryptoBotDonates/9">@CryptoBotDonates</a>.'
        )

        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text="Создать счет",
                callback_data="create_invoice"
            )
        )

        builder.row(
            InlineKeyboardButton(
                text="Создать из чата",
                switch_inline_query=""
            )
        )

        builder.row(
            InlineKeyboardButton(
                text="Мои счета",
                callback_data="my_invoices"
            )
        )

        if active_count > 0:
            builder.row(
                InlineKeyboardButton(
                    text=f"Активные счета • {active_count}",
                    callback_data="active_invoices"
                )
            )

        if unpaid_count > 0:
            builder.row(
                InlineKeyboardButton(
                    text=f"Неоплаченные счета • {unpaid_count}",
                    callback_data="unpaid_invoices"
                )
            )

        builder.row(
            InlineKeyboardButton(
                text=f"{BACK_SYMBOL} Назад",
                callback_data="main_menu"
            )
        )

        await callback.message.edit_text(
            accounts_text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        await callback.answer()

    except Exception as e:
        logger.error("Invoice menu failed", error=str(e))
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "create_invoice")
@require_auth
async def show_create_invoice_type(callback: CallbackQuery,
                               state: FSMContext,
                               language_code: str = "ru"):

    await state.clear()

    type_text = f"""
Выберите тип счёта.
    """

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Одноразовый", callback_data="invoice_type_single"),
            InlineKeyboardButton(text="Многоразовый", callback_data="invoice_type_multiple")
        ],
        [InlineKeyboardButton(text=f"{BACK_SYMBOL} Назад к счетам", callback_data="accounts_menu")]
    ])

    await callback.message.edit_text(type_text, reply_markup=keyboard, parse_mode="HTML")
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
Выберите одну или больше криптовалют, которыми может быть оплачен счёт.
    """

    keyboard = get_currency_selection_keyboard([])

    await callback.message.edit_text(currency_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.inline_query(F.query.startswith("share_invoice_"))
async def handle_share_invoice(inline_query: InlineQuery, db: AsyncSession):
    try:
        invoice_code = inline_query.query.replace("share_invoice_", "")

        if not invoice_code:
            return

        invoice = await InvoiceService.get_invoice_by_code(db, invoice_code)
        if not invoice:
            return

        invoice_link = f"https://t.me/{settings.bot_username}?start={invoice_code}"

        result = InlineQueryResultArticle(
            id=invoice_code,
            title=f"Счет #{invoice_code}",
            description=f"Сумма: ${invoice.amount} • {invoice.invoice_type}",
            input_message_content=InputTextMessageContent(
                message_text=f"💳 Счет #{invoice_code}\n💰 Сумма: ${invoice.amount}\n🔗 {invoice_link}",
                parse_mode="HTML"
            )
        )

        await inline_query.answer(results=[result], cache_time=1)

    except Exception as e:
        logger.error("Share invoice inline query failed", error=str(e))


def get_currency_selection_keyboard(selected_currencies: List[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    code_to_name = {
        "BTC": "Bitcoin",
        "ETH": "Ethereum",
        "USDT": "USDT",
        "LTC": "Litecoin",
        "BNB": "BNB",
        "TRX": "TRON",
        "TON": "Toncoin",
        "DOGE": "Dogecoin",
        "SOL": "Solana",
        "USDC": "USD Coin",
    }
    currencies = [(code, code_to_name.get(code, code)) for code in settings.supported_crypto_currencies]

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
Пришлите сумму счёта в USD с оплатой в {', '.join(selected_currencies)}!!
    """

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{BACK_SYMBOL} Назад к выбору валют", callback_data="back_to_currencies")]
    ])

    await callback.message.edit_text(amount_text, reply_markup=keyboard, parse_mode="HTML")
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


async def show_created_invoice(message: Message,
                           invoice: Invoice,
                           language_code: str = "ru"):

    currencies = invoice.currency.split(", ")

    invoice_text = f"""
<b>Счёт #{invoice.invoice_code}!</b>

Сумма: {invoice.amount}$

Любой может оплатить этот счёт в [{', '.join(currencies)}]

Скопируйте ссылку, чтобы поделиться счётом:
t.me/{settings.bot_username}?start={invoice.invoice_code}
    """

    keyboard = get_invoice_actions_keyboard(invoice.invoice_code, language_code)

    await message.answer(invoice_text, reply_markup=keyboard, parse_mode="HTML")


def get_invoice_actions_keyboard(invoice_code: str, language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Поделиться счётом", switch_inline_query=f"share_invoice_{invoice_code}")],
        [InlineKeyboardButton(text="Показать QR-код", callback_data=f"qr_{invoice_code}")],
        [InlineKeyboardButton(text="Разрешения", callback_data=f"permissions_{invoice_code}")],
        [InlineKeyboardButton(text="Скрытое сообщение: Выкл.", callback_data=f"toggle_hidden_{invoice_code}")],
        [InlineKeyboardButton(text="Удалить счёт", callback_data=f"delete_invoice_{invoice_code}")],
        [InlineKeyboardButton(text=f"{BACK_SYMBOL} Назад к списку счетов", callback_data="my_invoices")]
    ])


@router.callback_query(F.data.startswith("invoice_"))
@require_auth
async def show_invoice_details(callback: CallbackQuery,
                           state: FSMContext,
                           db: AsyncSession,
                           user: User,
                           language_code: str = "ru"):

    invoice_code = callback.data.split("_")[1]

    invoice = await InvoiceService.get_invoice_by_code(db, invoice_code)

    if not invoice or invoice.user_id != user.id:
        await callback.answer("❌ Счет не найден")
        return

    currencies = invoice.currency.split(", ")

    invoice_text = f"""
🧾 <b>Счёт #{invoice.invoice_code}!</b>

Сумма: {invoice.amount}$

Любой может оплатить этот счёт в [{', '.join(currencies)}]

Скопируйте ссылку, чтобы поделиться счётом:
t.me/{settings.bot_username}?start={invoice.invoice_code}
    """

    keyboard = get_invoice_actions_keyboard(invoice_code, language_code)

    await safe_edit_message(callback, invoice_text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("permissions_"))
@require_auth
async def show_permissions_menu(callback: CallbackQuery,
                              state: FSMContext,
                              db: AsyncSession,
                              user: User,
                              language_code: str = "ru"):

    invoice_code = callback.data.split("_")[1]

    invoice = await InvoiceService.get_invoice_by_code(db, invoice_code)

    if not invoice or invoice.user_id != user.id:
        await callback.answer("❌ Счет не найден")
        return

    permissions_text = f"""
🧾 <b>Разрешения счёта #{invoice_code}</b>

Разрешите или запретите оплачивать счёт анонимно и добавлять комментарий при оплате.
    """

    keyboard = get_permissions_keyboard(invoice_code, invoice)

    await callback.message.edit_text(permissions_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


def get_permissions_keyboard(invoice_code: str, invoice: Invoice) -> InlineKeyboardMarkup:
    comments_status = "Вкл." if invoice.allow_comments else "Выкл."
    anonymous_status = "Вкл." if invoice.allow_anonymous else "Выкл."
    hidden_status = "Вкл." if invoice.hidden_message else "Выкл."

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Комментарии: {comments_status}",
                            callback_data=f"toggle_comments_{invoice_code}")],
        [InlineKeyboardButton(text=f"Анонимные платежи: {anonymous_status}",
                            callback_data=f"toggle_anonymous_{invoice_code}")],
        [InlineKeyboardButton(text=f"Скрытое сообщение: {hidden_status}",
                            callback_data=f"toggle_hidden_{invoice_code}")],
        [InlineKeyboardButton(text=f"{BACK_SYMBOL} Назад к счёту",
                            callback_data=f"invoice_{invoice_code}")]
    ])


@router.callback_query(F.data.startswith("toggle_"))
@require_auth
async def toggle_permission(callback: CallbackQuery,
                          state: FSMContext,
                          db: AsyncSession,
                          user: User):

    parts = callback.data.split("_")
    permission_type = parts[1]
    invoice_code = parts[2]

    invoice = await InvoiceService.get_invoice_by_code(db, invoice_code)

    if not invoice or invoice.user_id != user.id:
        await callback.answer("❌ Счет не найден")
        return

    if permission_type == "comments":
        invoice.allow_comments = not invoice.allow_comments
    elif permission_type == "anonymous":
        invoice.allow_anonymous = not invoice.allow_anonymous
    elif permission_type == "hidden":
        invoice.hidden_message = not invoice.hidden_message

    await db.commit()

    keyboard = get_permissions_keyboard(invoice_code, invoice)

    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer("✅ Настройки обновлены")


@router.callback_query(F.data.startswith("delete_invoice_"))
@require_auth
async def confirm_delete_invoice(callback: CallbackQuery,
                             state: FSMContext,
                             language_code: str = "ru"):

    invoice_code = callback.data.split("_")[2]

    confirm_text = f"""
❌ <b>Удалить счёт #{invoice_code}?</b>

Вы уверены, что хотите удалить этот счёт?
    """

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data=f"confirm_delete_{invoice_code}"),
            InlineKeyboardButton(text="Нет", callback_data=f"invoice_{invoice_code}")
        ]
    ])

    await callback.message.edit_text(confirm_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"))
@require_auth
async def delete_invoice(callback: CallbackQuery,
                      state: FSMContext,
                      db: AsyncSession,
                      user: User,
                      language_code: str = "ru"):

    invoice_code = callback.data.split("_")[2]

    success = await InvoiceService.delete_invoice(db, invoice_code, user.id)

    if success:
        success_text = f"""
✅ <b>Счёт успешно удалён</b>

Счёт #{invoice_code} был удалён.
        """
    else:
        success_text = f"""
❌ <b>Ошибка удаления</b>

Не удалось удалить счёт #{invoice_code}.
        """

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{BACK_SYMBOL} Назад к списку счетов",
                            callback_data="accounts_menu")]
    ])

    await callback.message.edit_text(success_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "my_invoices")
@require_auth
async def show_my_invoices(callback: CallbackQuery, db: AsyncSession, user: User):
    try:
        invoices = await InvoiceService.get_user_invoices(db, user.id)

        header_text = "Здесь вы можете управлять своими созданными счетами."

        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()

        if not invoices:
            builder.row(
                InlineKeyboardButton(text="Создать счёт", callback_data="create_invoice")
            )
        else:
            seen_codes = set()
            unique_invoices = []
            for inv in invoices:
                if inv.invoice_code not in seen_codes:
                    seen_codes.add(inv.invoice_code)
                    unique_invoices.append(inv)

            for invoice in unique_invoices:
                currencies = invoice.currency.split(", ") if invoice.currency else []

                if invoice.invoice_type == "multiple":
                    button_text = f"Многоразовый · ${invoice.amount}"
                else:
                    if currencies:
                        button_text = f"${invoice.amount} ({', '.join(currencies)})"
                    else:
                        button_text = f"${invoice.amount}"

                builder.row(
                    InlineKeyboardButton(text=button_text, callback_data=f"open_invoice_{invoice.invoice_code}")
                )

        builder.row(
            InlineKeyboardButton(text=f"{BACK_SYMBOL} Назад к счетам", callback_data="accounts_menu")
        )

        await safe_edit_message(
            callback,
            header_text,
            builder.as_markup(),
            "HTML",
            remove_photo=True
        )
        await callback.answer()

    except Exception as e:
        logger.error("Show my invoices failed", error=str(e))
        await callback.answer("❌ Произошла ошибка", show_alert=True)


async def _show_invoice_details_by_code(callback: CallbackQuery, db: AsyncSession, user: User, invoice_code: str):
    invoice = await InvoiceService.get_invoice_by_code(db, invoice_code)
    if not invoice or invoice.user_id != user.id:
        await callback.answer("❌ Счет не найден")
        return

    currencies = invoice.currency.split(", ")
    invoice_text = f"""
🧾 <b>Счёт #{invoice.invoice_code}!</b>

Сумма: {invoice.amount}$

Любой может оплатить этот счёт в [{', '.join(currencies)}]

Скопируйте ссылку, чтобы поделиться счётом:
 t.me/{settings.bot_username}?start={invoice.invoice_code}
    """
    keyboard = get_invoice_actions_keyboard(invoice_code, "ru")
    await safe_edit_message(callback, invoice_text, keyboard, "HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("open_invoice_"))
@require_auth
async def open_invoice_from_list(callback: CallbackQuery, db: AsyncSession, user: User):
    code = callback.data.split("_", 2)[2]
    await _show_invoice_details_by_code(callback, db, user, code)


@router.callback_query(F.data == "active_invoices")
async def show_active_invoices(callback: CallbackQuery, db: AsyncSession):
    try:
        from app.services.auth import auth_service

        user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        invoices = await InvoiceService.get_user_invoices(db, user.id, status="active")

        if not invoices:
            text = """
🧾 <b>Активные счета</b>

У вас нет активных счетов.
            """
        else:
            text = f"""
🧾 <b>Активные счета</b>

Всего активных счетов: {len(invoices)}
            """

            for invoice in invoices[:10]:
                text += f"\n\n📄 <b>#{invoice.invoice_code}</b>"
                text += f"\n💰 Сумма: {invoice.amount}$"
                text += f"\n🔗 <a href='t.me/{settings.bot_username}?start={invoice.invoice_code}'>Поделиться</a>"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="invoice_menu")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logger.error("Show active invoices failed", error=str(e))
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "unpaid_invoices")
@require_auth
async def show_unpaid_invoices(callback: CallbackQuery,
                             state: FSMContext,
                             db: AsyncSession,
                             user: User,
                             language_code: str = "ru"):

    invoices = await InvoiceService.get_unpaid_invoices(db, user.id)

    if not invoices:
        text = f"""
🧾 <b>Неоплаченные счета</b>

У вас нет неоплаченных счетов.
        """
    else:
        text = f"""
🧾 <b>Неоплаченные счета</b>

Всего неоплаченных счетов: {len(invoices)}
        """

        for invoice in invoices[:5]:
            text += f"\n\n📄 <b>#{invoice.invoice_code}</b>"
            text += f"\n💰 Сумма: {invoice.amount}$"
            text += f"\n🔗 <a href='t.me/{settings.bot_username}?start={invoice.invoice_code}'>Оплатить</a>"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="invoice_menu")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


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

    await callback.message.edit_text(currency_text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("qr_"))
@require_auth
async def show_qr_code(callback: CallbackQuery,
                      state: FSMContext,
                      db: AsyncSession,
                      user: User,
                      language_code: str = "ru"):

    invoice_code = callback.data.split("_")[1]

    invoice = await InvoiceService.get_invoice_by_code(db, invoice_code)

    if not invoice or invoice.user_id != user.id:
        await callback.answer("❌ Счет не найден")
        return

    from app.utils.qr_generator import generate_invoice_qr_code

    qr_image = generate_invoice_qr_code(invoice_code, settings.bot_username)

    if not qr_image:
        await callback.answer("❌ Ошибка генерации QR кода", show_alert=True)
        return

    original_text = callback.message.text or callback.message.caption or ""
    original_keyboard = callback.message.reply_markup

    media = InputMediaPhoto(
        media=BufferedInputFile(qr_image, filename=f"qr_{invoice_code}.png"),
        caption=original_text,
        parse_mode="HTML"
    )

    await callback.message.edit_media(media=media, reply_markup=original_keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_hidden_"))
@require_auth
async def toggle_hidden_message(callback: CallbackQuery,
                             state: FSMContext,
                             db: AsyncSession,
                             user: User):

    invoice_code = callback.data.split("_")[2]

    invoice = await InvoiceService.get_invoice_by_code(db, invoice_code)

    if not invoice or invoice.user_id != user.id:
        await callback.answer("❌ Счет не найден")
        return

    invoice.hidden_message = not invoice.hidden_message

    await db.commit()

    keyboard = get_invoice_actions_keyboard(invoice_code, "ru")

    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer("✅ Скрытое сообщение обновлено")


@router.callback_query(F.data == "create_from_chat")
@require_auth
async def show_create_from_chat(callback: CallbackQuery,
                              state: FSMContext,
                              language_code: str = "ru"):

    await callback.answer("Функция в разработке")
