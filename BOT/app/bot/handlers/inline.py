from aiogram import Router, F
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineQueryResultPhoto
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from decimal import Decimal
import re

from app.database import AsyncSessionLocal
from app.services.auth import auth_service
from app.services.wallet import wallet_service
from app.services.check import check_service
from app.services.invoice import InvoiceService
from app.models.check import CheckType
from app.models.invoice import InvoiceType
from app.utils.exceptions import ValidationError
from .inline_gift import create_gift_results

logger = structlog.get_logger(__name__)
router = Router()


@router.inline_query()
async def inline_query_handler(query: InlineQuery):
    try:
        text = query.query.strip()

        if not text:
            results = [
                InlineQueryResultArticle(
                    id="help_1",
                    title="💡 Как использовать",
                    description="Введите сумму и параметры, например: 100 USDT",
                    input_message_content=InputTextMessageContent(
                        message_text="💡 Для создания чека введите:\n\n"
                                   "• <b>100</b> - простой чек на 100 USDT\n"
                                   "• <b>100 USDT</b> - простой чек на 100 USDT\n"
                                   "• <b>100 @username</b> - чек для пользователя\n"
                                   "• <b>100 password</b> - чек с паролем\n\n"
                                   "Если у вас есть баланс - создастся чек 🎫\n"
                                   "Если баланса нет - создастся счет 🧾",
                        parse_mode="HTML"
                    )
                ),
                InlineQueryResultArticle(
                    id="help_2",
                    title="🎫 Чеки",
                    description="Создаются при наличии баланса",
                    input_message_content=InputTextMessageContent(
                        message_text="🎫 <b>Чеки</b>\n\n"
                                   "Создаются автоматически, если у вас есть достаточный баланс.\n"
                                   "Получатель может активировать чек и получить средства.",
                        parse_mode="HTML"
                    )
                ),
                InlineQueryResultArticle(
                    id="help_3",
                    title="🧾 Счета",
                    description="Создаются при отсутствии баланса",
                    input_message_content=InputTextMessageContent(
                        message_text="🧾 <b>Счета</b>\n\n"
                                   "Создаются автоматически, если у вас недостаточно баланса.\n"
                                   "Плательщик может оплатить счет со своего кошелька.",
                        parse_mode="HTML"
                    )
                )
            ]

            await query.answer(
                results=results,
                cache_time=300,
                switch_pm_text="🤖 Запустить бота",
                switch_pm_parameter="start"
            )
            return

        if text.startswith("gift_"):
            activation_code = text[5:]
            logger.info("Processing gift inline query",
                       activation_code=activation_code,
                       activation_code_type=type(activation_code),
                       user_id=query.from_user.id,
                       full_text=text)
            results = await create_gift_results(activation_code)
            await query.answer(results, cache_time=0)
            return

        amount, currency, check_type, extra_param = parse_check_command(text)

        if not amount:
            results = [
                InlineQueryResultArticle(
                    id="error_1",
                    title="❌ Неверный формат",
                    description="Введите сумму и параметры, например: 100 USDT",
                    input_message_content=InputTextMessageContent(
                        message_text="❌ Неверный формат запроса\n\n"
                                   "Примеры правильного ввода:\n"
                                   "• <b>100</b> - простой чек\n"
                                   "• <b>100 USDT</b> - чек в валюте\n"
                                   "• <b>100 @username</b> - чек для пользователя\n"
                                   "• <b>100 password</b> - чек с паролем",
                        parse_mode="HTML"
                    )
                )
            ]
            await query.answer(results, cache_time=60)
            return

        async with AsyncSessionLocal() as db:
            user = await auth_service.get_user_by_telegram_id(db, query.from_user.id)
            if not user:
                results = [
                    InlineQueryResultArticle(
                        id="not_registered",
                        title="❌ Пользователь не зарегистрирован",
                        description="Сначала запустите бота командой /start",
                        input_message_content=InputTextMessageContent(
                            message_text="❌ Вы не зарегистрированы в боте\n\n"
                                       "Для использования inline-режима сначала запустите бота командой /start"
                        )
                    )
                ]
                await query.answer(results, cache_time=60)
                return

            has_balance = await check_user_balance(db, user, currency, amount)

            if has_balance:
                results = await create_check_results(amount, currency, user, check_type, extra_param)
            else:
                results = await create_invoice_results(amount, currency, user)

            await query.answer(results, cache_time=60)

    except Exception as e:
        logger.error(
            "Inline query failed",
            user_id=query.from_user.id,
            query_text=query.query,
            error=str(e),
            exc_info=True
        )

        results = [
            InlineQueryResultArticle(
                id="error",
                title="❌ Произошла ошибка",
                description="Попробуйте еще раз",
                input_message_content=InputTextMessageContent(
                    message_text="❌ Произошла ошибка при обработке запроса\n\n"
                               "Попробуйте еще раз или обратитесь в поддержку."
                )
            )
        ]
        await query.answer(results, cache_time=30)


def parse_check_command(text: str) -> tuple[str, str, str, str]:
    try:
        text = text.strip()

        parts = text.split()

        if len(parts) < 1:
            return None, None, None, None

        amount = parts[0].replace(',', '.')

        try:
            float(amount)
        except ValueError:
            return None, None, None, None

        currency = 'USDT'
        check_type = 'simple'
        extra_param = None

        for part in parts[1:]:
            part_upper = part.upper()

            if part_upper in ['USDT', 'TON', 'SOL', 'TRX', 'GRAM', 'BTC', 'ETH', 'DOGE', 'LTC',
                            'NOT', 'TRUMP', 'MELANIA', 'PEPE', 'WIF', 'BONK', 'MAJOR', 'MY',
                            'DOGS', 'MEMHASH', 'BNB', 'HMSTR', 'CATI', 'USDC']:
                currency = part_upper

            elif part.startswith('@'):
                check_type = 'user'
                extra_param = part[1:]

            elif part_upper not in ['USDT', 'TON', 'SOL', 'TRX', 'GRAM', 'BTC', 'ETH', 'DOGE', 'LTC',
                                  'NOT', 'TRUMP', 'MELANIA', 'PEPE', 'WIF', 'BONK', 'MAJOR', 'MY',
                                  'DOGS', 'MEMHASH', 'BNB', 'HMSTR', 'CATI', 'USDC']:
                check_type = 'password'
                extra_param = part

        return amount, currency, check_type, extra_param

    except Exception as e:
        logger.error("Failed to parse check command", text=text, error=str(e))
        return None, None, None, None


def parse_amount_and_currency(text: str) -> tuple[str, str]:
    try:
        text = text.strip().upper()

        pattern = r'^(\d+(?:[.,]\d+)?)\s*([A-Z]{2,10})?$'
        match = re.match(pattern, text)

        if not match:
            return None, None

        amount_str = match.group(1).replace(',', '.')
        currency = match.group(2) or 'USDT'

        try:
            amount_decimal = Decimal(amount_str)
            if amount_decimal <= 0:
                return None, None
        except:
            return None, None

        supported_currencies = ["BTC", "ETH", "USDT", "LTC", "BNB", "TRX", "TON", "USD", "EUR", "RUB"]

        if currency not in supported_currencies:
            return None, None

        return amount_str, currency

    except Exception as e:
        logger.error("Failed to parse amount and currency", text=text, error=str(e))
        return None, None


async def check_user_balance(db: AsyncSession, user, currency: str, amount: str) -> bool:
    try:
        if currency in ["USD", "EUR", "RUB"]:
            return False

        wallet = await wallet_service.get_user_wallet(db, user.id, currency)
        if not wallet:
            return False

        available_balance = Decimal(wallet.available_balance)
        required_amount = Decimal(amount)

        return available_balance >= required_amount

    except Exception as e:
        logger.error(
            "Failed to check user balance",
            user_id=user.id,
            currency=currency,
            amount=amount,
            error=str(e)
        )
        return False


async def create_check_results(amount: str, currency: str, user, check_type: str = None, extra_param: str = None) -> list:
    try:
        from app.database import AsyncSessionLocal
        from app.models.check import CheckType

        async with AsyncSessionLocal() as db:
            if check_type == 'user':
                target_user = await auth_service.get_user_by_username(db, extra_param)

                if target_user:
                    check = await check_service.create_check(
                        db=db,
                        creator=user,
                        currency=currency,
                        amount=amount,
                        check_type=CheckType.PERSONAL,
                        target_user_id=target_user.id,
                        description=f"Персональный чек для @{extra_param}"
                    )
                else:
                    check = await check_service.create_check(
                        db=db,
                        creator=user,
                        currency=currency,
                        amount=amount,
                        check_type=CheckType.PERSONAL,
                        target_username=extra_param,
                        description=f"Персональный чек для @{extra_param}"
                    )

                title = f"🎫 Чек на {amount} {currency}"
                description = f"Персональный чек для @{extra_param}"

            elif check_type == 'password':
                check = await check_service.create_check(
                    db=db,
                    creator=user,
                    currency=currency,
                    amount=amount,
                    check_type=CheckType.ONE_TIME,
                    password=extra_param,
                    description=f"Чек с паролем"
                )
                title = f"🎫 Чек на {amount} {currency}"
                description = f"Чек защищенный паролем"

            else:
                check = await check_service.create_check(
                    db=db,
                    creator=user,
                    currency=currency,
                    amount=amount,
                    check_type=CheckType.ONE_TIME,
                    description=f"Чек создан через inline"
                )
                title = f"🎫 Чек на {amount} {currency}"
                description = f"Простой чек"

            from app.config import settings
            bot_username = settings.bot_username
            check_url = f"https://t.me/{bot_username}?start=activate_check_{check.activation_code}"

            message_text = (
                f"🎫 Чек на {amount} {currency}\n"
                f"Нажмите кнопку ниже для получения:"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Получить",
                        url=check_url
                    )
                ]
            ])

            results = [
                InlineQueryResultArticle(
                    id=f"check_{check.check_id}",
                    title=title,
                    description=description,
                    input_message_content=InputTextMessageContent(
                        message_text=message_text,
                        parse_mode="HTML"
                    ),
                    reply_markup=keyboard
                )
            ]

            return results

    except Exception as e:
        logger.error("Failed to create check results", error=str(e))
        return [
            InlineQueryResultArticle(
                id=f"error_create_check",
                title="❌ Ошибка создания чека",
                description="Попробуйте еще раз",
                input_message_content=InputTextMessageContent(
                    message_text="❌ Произошла ошибка при создании чека"
                )
            )
        ]


async def create_invoice_results(amount: str, currency: str, user) -> list:
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧾 Создать счет",
                    callback_data=f"create_invoice_{amount}_{currency}"
                )
            ]
        ])

        results = [
            InlineQueryResultArticle(
                id=f"invoice_{amount}_{currency}",
                title=f"🧾 Создать счет на {amount} {currency}",
                description="Недостаточно баланса для чека, создаем счет",
                input_message_content=InputTextMessageContent(
                    message_text=f"🧾 <b>Счет на {amount} {currency}</b>\n\n"
                               f"💳 Плательщик сможет оплатить счет со своего кошелька\n"
                               f"💰 После оплаты средства поступят на ваш баланс\n\n"
                               f"Нажмите кнопку ниже для создания:",
                    parse_mode="HTML"
                ),
                reply_markup=keyboard
            ),
            InlineQueryResultArticle(
                id=f"invoice_recurring_{amount}_{currency}",
                title=f"🔄 Повторяющийся счет на {amount} {currency}",
                description="Счет с автоматическим повторением",
                input_message_content=InputTextMessageContent(
                    message_text=f"🔄 <b>Повторяющийся счет на {amount} {currency}</b>\n\n"
                               f"📅 Счет будет автоматически создаваться через заданный интервал\n"
                               f"💰 Удобно для регулярных платежей\n\n"
                               f"Нажмите кнопку ниже для создания:",
                    parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔄 Создать повторяющийся счет",
                            callback_data=f"create_recurring_invoice_{amount}_{currency}"
                        )
                    ]
                ])
            )
        ]

        return results

    except Exception as e:
        logger.error("Failed to create invoice results", error=str(e))
        return []


@router.callback_query(F.data.startswith("create_check_"))
async def create_check_callback(callback_query, state=None):
    try:
        parts = callback_query.data.split("_")
        amount = parts[2]
        currency = parts[3]

        async with AsyncSessionLocal() as db:
            user = await auth_service.get_user_by_telegram_id(db, callback_query.from_user.id)
            if not user:
                await callback_query.answer("❌ Пользователь не найден", show_alert=True)
                return

            check = await check_service.create_check(
                db=db,
                creator=user,
                currency=currency,
                amount=amount,
                check_type=CheckType.ONE_TIME,
                description=f"Чек создан через inline-режим"
            )

            bot_info = await callback_query.bot.get_me()
            check_url = f"https://t.me/{bot_info.username}?start=activate_check_{check.activation_code}"

            text = (
                f"🎫 Чек на {amount} {currency}\n"
                f"Нажмите кнопку ниже для получения:"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Получить",
                        url=check_url
                    )
                ]
            ])

            await callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            await callback_query.answer("✅ Чек создан!")

    except Exception as e:
        logger.error(
            "Failed to create check",
            user_id=callback_query.from_user.id,
            callback_data=callback_query.data,
            error=str(e),
            exc_info=True
        )
        await callback_query.answer("❌ Ошибка при создании чека", show_alert=True)


@router.callback_query(F.data.startswith("create_invoice_"))
async def create_invoice_callback(callback_query, state=None):
    try:
        parts = callback_query.data.split("_")
        amount = parts[2]
        currency = parts[3]

        async with AsyncSessionLocal() as db:
            user = await auth_service.get_user_by_telegram_id(db, callback_query.from_user.id)
            if not user:
                await callback_query.answer("❌ Пользователь не найден", show_alert=True)
                return

            invoice = await invoice_service.create_invoice(
                db=db,
                creator=user,
                currency=currency,
                amount=amount,
                description=f"Счет создан через inline-режим",
                invoice_type=InvoiceType.STANDARD
            )

            bot_info = await callback_query.bot.get_me()
            invoice_url = f"https://t.me/{bot_info.username}?start=invoice_{invoice.invoice_id}"

            text = (
                f"✅ <b>Счет создан успешно!</b>\n\n"
                f"🧾 ID счета: <code>{invoice.invoice_id}</code>\n"
                f"💰 Сумма: {amount} {currency}\n"
                f"📅 Действителен до: {invoice.expires_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                f"🔗 <b>Ссылка для оплаты:</b>\n"
                f"{invoice_url}\n\n"
                f"📋 Отправьте эту ссылку плательщику для оплаты счета"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 Скопировать ссылку",
                        url=invoice_url
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🧾 Мои счета",
                        callback_data="invoice_list"
                    )
                ]
            ])

            await callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            await callback_query.answer("✅ Счет создан!")

    except Exception as e:
        logger.error(
            "Failed to create invoice",
            user_id=callback_query.from_user.id,
            callback_data=callback_query.data,
            error=str(e),
            exc_info=True
        )
        await callback_query.answer("❌ Ошибка при создании счета", show_alert=True)


@router.callback_query(F.data.startswith("create_personal_check_"))
async def create_personal_check_callback(callback_query, state=None):
    try:
        parts = callback_query.data.split("_")
        amount = parts[3]
        currency = parts[4]

        text = (
            f"👤 <b>Создание персонального чека</b>\n\n"
            f"💰 Сумма: {amount} {currency}\n\n"
            f"📝 Отправьте username получателя (например: @username или username):"
        )

        await callback_query.message.edit_text(text, parse_mode="HTML")
        await callback_query.answer()


    except Exception as e:
        logger.error(
            "Failed to create personal check",
            user_id=callback_query.from_user.id,
            callback_data=callback_query.data,
            error=str(e),
            exc_info=True
        )
        await callback_query.answer("❌ Ошибка при создании персонального чека", show_alert=True)


@router.callback_query(F.data.startswith("create_user_check_"))
async def create_user_check_callback(callback_query, state=None):
    try:
        parts = callback_query.data.split("_")
        amount = parts[3]
        currency = parts[4]
        username = parts[5]

        async with AsyncSessionLocal() as db:
            user = await auth_service.get_user_by_telegram_id(db, callback_query.from_user.id)
            if not user:
                await callback_query.answer("❌ Пользователь не найден", show_alert=True)
                return

            target_user = await auth_service.get_user_by_username(db, username)
            if not target_user:
                await callback_query.answer(f"❌ Пользователь @{username} не найден", show_alert=True)
                return

            check = await check_service.create_check(
                db=db,
                creator=user,
                currency=currency,
                amount=amount,
                check_type=CheckType.PERSONAL,
                target_user_id=target_user.id,
                description=f"Персональный чек для @{username}"
            )

            bot_info = await callback_query.bot.get_me()
            check_url = f"https://t.me/{bot_info.username}?start=activate_check_{check.activation_code}"

            text = (
                f"🎫 Чек на {amount} {currency}\n"
                f"Нажмите кнопку ниже для получения:"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Получить",
                        url=check_url
                    )
                ]
            ])

            await callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            await callback_query.answer("✅ Чек создан!")

    except Exception as e:
        logger.error(
            "Failed to create user check",
            user_id=callback_query.from_user.id,
            callback_data=callback_query.data,
            error=str(e),
            exc_info=True
        )
        await callback_query.answer("❌ Ошибка при создании чека", show_alert=True)


@router.callback_query(F.data.startswith("create_password_check_"))
async def create_password_check_callback(callback_query, state=None):
    try:
        parts = callback_query.data.split("_")
        amount = parts[3]
        currency = parts[4]
        password = parts[5]

        async with AsyncSessionLocal() as db:
            user = await auth_service.get_user_by_telegram_id(db, callback_query.from_user.id)
            if not user:
                await callback_query.answer("❌ Пользователь не найден", show_alert=True)
                return

            check = await check_service.create_check(
                db=db,
                creator=user,
                currency=currency,
                amount=amount,
                check_type=CheckType.ONE_TIME,
                password=password,
                description=f"Чек с паролем"
            )

            bot_info = await callback_query.bot.get_me()
            check_url = f"https://t.me/{bot_info.username}?start=activate_check_{check.activation_code}"

            text = (
                f"🎫 Чек на {amount} {currency}\n"
                f"Нажмите кнопку ниже для получения:"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Получить",
                        url=check_url
                    )
                ]
            ])

            await callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            await callback_query.answer("✅ Чек создан!")

    except Exception as e:
        logger.error(
            "Failed to create password check",
            user_id=callback_query.from_user.id,
            callback_data=callback_query.data,
            error=str(e),
            exc_info=True
        )
        await callback_query.answer("❌ Ошибка при создании чека", show_alert=True)
