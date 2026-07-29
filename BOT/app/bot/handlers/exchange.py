from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from typing import Optional
import structlog

from app.database import get_db
from app.services.exchange import exchange_service
from app.services.user import user_service
from app.models.exchange import ExchangeStatus
from app.bot.keyboards.exchange import (
    get_exchange_main_keyboard,
    get_currency_selection_keyboard,
    get_exchange_confirmation_keyboard,
    get_exchange_actions_keyboard,
    get_back_keyboard
)
from app.bot.utils.decorators import require_auth
from app.bot.utils.formatters import format_currency, format_datetime, format_percentage
from app.utils.exceptions import ExchangeError, InsufficientFundsError, ValidationError

logger = structlog.get_logger(__name__)
router = Router()


class ExchangeStates(StatesGroup):
    SELECT_FROM_CURRENCY = State()
    SELECT_TO_CURRENCY = State()
    ENTER_AMOUNT = State()
    CONFIRM_EXCHANGE = State()


@router.message(Command("exchange"))
@require_auth
async def exchange_main_menu(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()

    keyboard = get_exchange_main_keyboard()

    text = (
        "🔄 <b>Обмен валют</b>\n\n"
        "Быстрый и безопасный обмен криптовалют по выгодным курсам.\n\n"
        "• Мгновенный обмен\n"
        "• Низкие комиссии\n"
        "• Поддержка множества валют\n"
        "• Прозрачные курсы\n\n"
        "Выберите действие:"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "exchange_create")
@require_auth
async def exchange_create_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ExchangeStates.SELECT_FROM_CURRENCY)

    keyboard = get_currency_selection_keyboard("crypto")

    text = (
        "💱 <b>Создать обмен</b>\n\n"
        "Выберите валюту, которую хотите обменять:"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("exchange_from_"))
async def exchange_from_currency_selected(callback: CallbackQuery, state: FSMContext):
    from_currency = callback.data.split("_", 2)[2]
    await state.update_data(from_currency=from_currency)
    await state.set_state(ExchangeStates.SELECT_TO_CURRENCY)

    keyboard = get_currency_selection_keyboard("all", exclude=from_currency)

    text = (
        f"💱 <b>Обмен {from_currency}</b>\n\n"
        "Выберите валюту, на которую хотите обменять:"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("exchange_to_"))
async def exchange_to_currency_selected(callback: CallbackQuery, state: FSMContext):
    to_currency = callback.data.split("_", 2)[2]
    await state.update_data(to_currency=to_currency)
    await state.set_state(ExchangeStates.ENTER_AMOUNT)

    data = await state.get_data()
    from_currency = data.get("from_currency")

    text = (
        f"💰 <b>Сумма для обмена</b>\n\n"
        f"Обмен: {from_currency} → {to_currency}\n\n"
        f"Введите количество {from_currency} для обмена:\n\n"
        "Пример: 0.1"
    )

    keyboard = get_back_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(StateFilter(ExchangeStates.ENTER_AMOUNT))
async def exchange_amount_entered(message: Message, state: FSMContext, db: AsyncSession):
    try:
        amount = Decimal(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError("Amount must be positive")

        data = await state.get_data()
        from_currency = data.get("from_currency")
        to_currency = data.get("to_currency")

        user = await user_service.get_user_by_telegram_id(db, message.from_user.id)

        calculation = await exchange_service.calculate_exchange(
            db=db,
            from_currency=from_currency,
            to_currency=to_currency,
            from_amount=amount,
            user=user
        )

        await state.update_data(
            from_amount=str(amount),
            calculation=calculation
        )
        await state.set_state(ExchangeStates.CONFIRM_EXCHANGE)

        from_amount = format_currency(Decimal(calculation["from_amount"]), from_currency)
        to_amount = format_currency(Decimal(calculation["to_amount"]), to_currency)
        fee_amount = format_currency(Decimal(calculation["fee_amount"]), calculation["fee_currency"])
        total_amount = format_currency(Decimal(calculation["total_from_amount"]), from_currency)
        rate = format_currency(Decimal(calculation["exchange_rate"]), to_currency)

        text = (
            f"✅ <b>Подтверждение обмена</b>\n\n"
            f"📊 <b>Детали обмена:</b>\n"
            f"• Отдаете: {from_amount}\n"
            f"• Получаете: {to_amount}\n"
            f"• Курс: 1 {from_currency} = {rate}\n"
            f"• Комиссия: {fee_amount} ({calculation['fee_percentage']}%)\n"
            f"• Итого к списанию: {total_amount}\n\n"
            f"⏰ Предложение действительно {calculation['expires_in_minutes']} минут\n\n"
            "Подтвердите обмен:"
        )

        keyboard = get_exchange_confirmation_keyboard()
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    except (ValueError, TypeError):
        text = (
            "❌ <b>Неверный формат</b>\n\n"
            "Введите корректную сумму для обмена.\n\n"
            "Пример: 0.1"
        )
        await message.answer(text, parse_mode="HTML")

    except ValidationError as e:
        text = f"❌ <b>Ошибка валидации</b>\n\n{str(e)}"
        await message.answer(text, parse_mode="HTML")

    except ExchangeError as e:
        text = f"❌ <b>Ошибка обмена</b>\n\n{str(e)}"
        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        logger.error("Failed to calculate exchange", error=str(e), exc_info=True)
        text = "❌ Ошибка при расчете обмена. Попробуйте позже."
        await message.answer(text)


@router.callback_query(F.data == "exchange_confirm")
async def exchange_confirm(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    try:
        data = await state.get_data()
        from_currency = data.get("from_currency")
        to_currency = data.get("to_currency")
        from_amount = Decimal(data.get("from_amount"))

        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)

        exchange = await exchange_service.create_exchange(
            db=db,
            user=user,
            from_currency=from_currency,
            to_currency=to_currency,
            from_amount=from_amount
        )

        exchange = await exchange_service.process_exchange(
            db=db,
            exchange_id=exchange.exchange_id,
            user=user
        )

        await state.clear()

        if exchange.status == ExchangeStatus.COMPLETED.value:
            from_amount_str = format_currency(exchange.from_amount, exchange.from_currency)
            to_amount_str = format_currency(exchange.net_to_amount, exchange.to_currency)

            text = (
                f"✅ <b>Обмен завершен успешно!</b>\n\n"
                f"🔄 Обмен #{exchange.exchange_id[:8]}\n\n"
                f"📊 <b>Результат:</b>\n"
                f"• Списано: {from_amount_str}\n"
                f"• Зачислено: {to_amount_str}\n"
                f"• Время: {format_datetime(exchange.completed_at)}\n\n"
                "Средства зачислены на ваш кошелек."
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💰 Кошелек", callback_data="wallet_main")],
                [InlineKeyboardButton(text="🔄 Новый обмен", callback_data="exchange_create")],
                [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
            ])

        else:
            text = (
                f"❌ <b>Обмен не удался</b>\n\n"
                f"🔄 Обмен #{exchange.exchange_id[:8]}\n\n"
                f"Причина: {exchange.failure_reason or 'Неизвестная ошибка'}\n\n"
                "Попробуйте позже или обратитесь в поддержку."
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="exchange_create")],
                [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
            ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    except InsufficientFundsError as e:
        text = f"❌ <b>Недостаточно средств</b>\n\n{str(e)}"
        keyboard = get_back_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    except ValidationError as e:
        text = f"❌ <b>Ошибка валидации</b>\n\n{str(e)}"
        keyboard = get_back_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    except ExchangeError as e:
        text = f"❌ <b>Ошибка обмена</b>\n\n{str(e)}"
        keyboard = get_back_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        logger.error("Failed to confirm exchange", error=str(e), exc_info=True)
        text = "❌ Ошибка при создании обмена. Попробуйте позже."
        keyboard = get_back_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "exchange_cancel")
async def exchange_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await exchange_main_menu(callback.message, state, next(get_db()))


@router.callback_query(F.data == "exchange_history")
@require_auth
async def exchange_history(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    try:
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)

        exchanges = await exchange_service.get_user_exchanges(
            db=db,
            user_id=user.id,
            limit=10
        )

        if not exchanges:
            text = (
                "📭 <b>История обменов пуста</b>\n\n"
                "У вас пока нет обменов.\n\n"
                "Создайте свой первый обмен!"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Создать обмен", callback_data="exchange_create")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="exchange_main")]
            ])

        else:
            text_parts = ["📊 <b>История обменов</b>\n"]

            for i, exchange in enumerate(exchanges[:5], 1):
                status_emoji = {
                    "completed": "✅",
                    "pending": "🟡",
                    "processing": "🔵",
                    "failed": "❌",
                    "cancelled": "❌",
                    "expired": "⏰"
                }.get(exchange.status, "❓")

                from_amount = format_currency(exchange.from_amount, exchange.from_currency)
                to_amount = format_currency(exchange.to_amount, exchange.to_currency)
                date_str = format_datetime(exchange.created_at, show_time=False)

                text_parts.append(
                    f"{i}. {status_emoji} {from_amount} → {to_amount}\n"
                    f"   📅 {date_str}"
                )

            text = "\n\n".join(text_parts)

            keyboard_buttons = []
            for i, exchange in enumerate(exchanges[:3], 1):
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"#{i} - {exchange.from_currency}/{exchange.to_currency}",
                        callback_data=f"exchange_view_{exchange.exchange_id}"
                    )
                ])

            keyboard_buttons.extend([
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="exchange_history")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="exchange_main")]
            ])

            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        logger.error("Failed to show exchange history", error=str(e), exc_info=True)
        text = "❌ Ошибка при загрузке истории обменов."
        keyboard = get_back_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("exchange_view_"))
async def exchange_view(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    exchange_id = callback.data.split("_", 2)[2]

    try:
        exchange = await exchange_service.get_exchange_by_id(db, exchange_id)

        if not exchange:
            text = "❌ Обмен не найден."
            keyboard = get_back_keyboard()
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            return

        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)

        if exchange.user_id != user.id:
            text = "❌ У вас нет доступа к этому обмену."
            keyboard = get_back_keyboard()
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            return

        status_text = {
            "pending": "🟡 Ожидает обработки",
            "processing": "🔵 Обрабатывается",
            "completed": "✅ Завершен",
            "failed": "❌ Неудачный",
            "cancelled": "❌ Отменен",
            "expired": "⏰ Истек"
        }.get(exchange.status, f"❓ {exchange.status}")

        from_amount = format_currency(exchange.from_amount, exchange.from_currency)
        to_amount = format_currency(exchange.to_amount, exchange.to_currency)
        fee_amount = format_currency(exchange.fee_amount, exchange.fee_currency)
        rate = format_currency(exchange.exchange_rate, exchange.to_currency)

        text_parts = [
            f"🔄 <b>Обмен #{exchange.exchange_id[:8]}</b>\n",
            f"📊 <b>Статус:</b> {status_text}",
            f"💱 <b>Обмен:</b> {exchange.from_currency} → {exchange.to_currency}",
            f"💰 <b>Сумма:</b> {from_amount}",
            f"💸 <b>Получено:</b> {to_amount}",
            f"📈 <b>Курс:</b> 1 {exchange.from_currency} = {rate}",
            f"💳 <b>Комиссия:</b> {fee_amount}",
            f"📅 <b>Создан:</b> {format_datetime(exchange.created_at)}"
        ]

        if exchange.completed_at:
            text_parts.append(f"✅ <b>Завершен:</b> {format_datetime(exchange.completed_at)}")

        if exchange.failure_reason:
            text_parts.append(f"❌ <b>Причина ошибки:</b> {exchange.failure_reason}")

        text = "\n".join(text_parts)

        keyboard = get_exchange_actions_keyboard(exchange)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        logger.error("Failed to view exchange", exchange_id=exchange_id, error=str(e), exc_info=True)
        text = "❌ Ошибка при загрузке информации об обмене."
        keyboard = get_back_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "exchange_rates")
async def exchange_rates(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    try:
        pairs = await exchange_service.get_supported_pairs(db)

        if not pairs:
            text = (
                "📊 <b>Курсы обмена</b>\n\n"
                "Курсы временно недоступны.\n"
                "Попробуйте позже."
            )
        else:
            text_parts = ["📊 <b>Актуальные курсы</b>\n"]

            main_pairs = [
                ("BTC", "USDT"),
                ("ETH", "USDT"),
                ("BTC", "ETH"),
                ("USDT", "USD")
            ]

            for from_curr, to_curr in main_pairs:
                pair_data = next(
                    (p for p in pairs if p["from_currency"] == from_curr and p["to_currency"] == to_curr),
                    None
                )

                if pair_data:
                    rate = format_currency(Decimal(pair_data["rate"]), to_curr, show_symbol=False)
                    text_parts.append(f"• {from_curr}/{to_curr}: {rate}")

            text = "\n".join(text_parts)
            text += f"\n\n🕐 Обновлено: {format_datetime(datetime.utcnow())}"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="exchange_rates")],
            [InlineKeyboardButton(text="💱 Создать обмен", callback_data="exchange_create")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="exchange_main")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        logger.error("Failed to show exchange rates", error=str(e), exc_info=True)
        text = "❌ Ошибка при загрузке курсов обмена."
        keyboard = get_back_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "exchange_main")
async def exchange_back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await exchange_main_menu(callback.message, state, next(get_db()))
