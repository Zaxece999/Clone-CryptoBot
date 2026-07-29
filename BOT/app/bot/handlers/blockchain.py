from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from decimal import Decimal

from app.database import get_db
from app.services.user import user_service
from app.services.blockchain import blockchain_service
from app.models.blockchain import BlockchainNetwork, TransactionStatus
from app.bot.keyboards.inline import create_inline_keyboard
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = Router()


class BlockchainStates(StatesGroup):
    waiting_withdrawal_currency = State()
    waiting_withdrawal_network = State()
    waiting_withdrawal_address = State()
    waiting_withdrawal_amount = State()
    waiting_withdrawal_memo = State()
    confirming_withdrawal = State()


@router.message(Command("deposit"))
async def cmd_deposit(message: Message, state: FSMContext):
    await state.clear()
    await show_deposit_menu(message)


@router.message(Command("withdraw"))
async def cmd_withdraw(message: Message, state: FSMContext):
    await state.clear()
    await show_withdrawal_menu(message)


async def show_deposit_menu(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="₿ Bitcoin (BTC)", callback_data="deposit_bitcoin")],
        [InlineKeyboardButton(text="Ξ Ethereum (ETH)", callback_data="deposit_ethereum")],
        [InlineKeyboardButton(text="💰 USDT (TRC20)", callback_data="deposit_usdt_tron")],
        [InlineKeyboardButton(text="💰 USDT (ERC20)", callback_data="deposit_usdt_ethereum")],
        [InlineKeyboardButton(text="💰 USDT (BEP20)", callback_data="deposit_usdt_bsc")],
        [InlineKeyboardButton(text="🔗 Другие валюты", callback_data="deposit_other")],
        [InlineKeyboardButton(text="📊 История депозитов", callback_data="deposit_history")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])

    text = (
        "💰 <b>Пополнение кошелька</b>\n\n"
        "Выберите валюту для пополнения:\n\n"
        "⚠️ <b>Важно:</b>\n"
        "• Отправляйте только указанную валюту на соответствующий адрес\n"
        "• Минимальная сумма пополнения различается для каждой валюты\n"
        "• Средства зачисляются после подтверждения в блокчейне\n"
        "• Сохраните адрес - он постоянный для вашего аккаунта"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("deposit_"))
async def handle_deposit_currency(callback: CallbackQuery):
    currency_data = callback.data.split("_", 1)[1]

    currency_mapping = {
        "bitcoin": ("BTC", BlockchainNetwork.BITCOIN),
        "ethereum": ("ETH", BlockchainNetwork.ETHEREUM),
        "usdt_tron": ("USDT", BlockchainNetwork.TRON),
        "usdt_ethereum": ("USDT", BlockchainNetwork.ETHEREUM),
        "usdt_bsc": ("USDT", BlockchainNetwork.BINANCE_SMART_CHAIN),
    }

    if currency_data == "other":
        await show_other_currencies(callback)
        return
    elif currency_data == "history":
        await show_deposit_history(callback)
        return

    if currency_data not in currency_mapping:
        await callback.answer("❌ Неподдерживаемая валюта")
        return

    currency, network = currency_mapping[currency_data]
    await show_deposit_address(callback, currency, network)


async def show_deposit_address(callback: CallbackQuery, currency: str, network: BlockchainNetwork):
    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        try:
            deposit_address = await blockchain_service.get_user_deposit_address(
                db, user.id, currency, network
            )

            if not deposit_address:
                deposit_address = await blockchain_service.create_deposit_address(
                    db, user, currency, network
                )

            network_names = {
                BlockchainNetwork.BITCOIN: "Bitcoin",
                BlockchainNetwork.ETHEREUM: "Ethereum (ERC20)",
                BlockchainNetwork.TRON: "TRON (TRC20)",
                BlockchainNetwork.BINANCE_SMART_CHAIN: "Binance Smart Chain (BEP20)",
                BlockchainNetwork.POLYGON: "Polygon"
            }

            network_name = network_names.get(network, network.value.title())

            text = (
                f"💰 <b>Пополнение {currency}</b>\n"
                f"🌐 <b>Сеть:</b> {network_name}\n\n"
                f"📍 <b>Ваш адрес:</b>\n"
                f"<code>{deposit_address.address}</code>\n\n"
            )

            if deposit_address.memo:
                text += f"📝 <b>Memo:</b> <code>{deposit_address.memo}</code>\n\n"

            min_amounts = {
                ("BTC", BlockchainNetwork.BITCOIN): "0.001 BTC",
                ("ETH", BlockchainNetwork.ETHEREUM): "0.01 ETH",
                ("USDT", BlockchainNetwork.TRON): "10 USDT",
                ("USDT", BlockchainNetwork.ETHEREUM): "20 USDT",
                ("USDT", BlockchainNetwork.BINANCE_SMART_CHAIN): "10 USDT",
            }

            min_amount = min_amounts.get((currency, network), "Уточняйте")

            text += (
                f"💡 <b>Информация:</b>\n"
                f"• Минимальная сумма: {min_amount}\n"
                f"• Подтверждений требуется: {_get_confirmations_required(network)}\n"
                f"• Время зачисления: {_get_estimated_time(network)}\n\n"
                f"⚠️ <b>Внимание:</b>\n"
                f"• Отправляйте только {currency} в сети {network_name}\n"
                f"• Отправка других валют приведет к потере средств\n"
                f"• Адрес привязан к вашему аккаунту навсегда"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Копировать адрес", callback_data=f"copy_address_{deposit_address.address}")],
                [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"refresh_deposit_{currency}_{network.value}")],
                [InlineKeyboardButton(text="📊 История", callback_data="deposit_history")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="deposit_menu")]
            ])

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()

        except Exception as e:
            logger.error("❌ Не удалось показать адрес депозита", error=str(e), exc_info=True)
            await callback.answer("❌ Ошибка при получении адреса")


async def show_other_currencies(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Litecoin (LTC)", callback_data="deposit_ltc")],
        [InlineKeyboardButton(text="🐕 Dogecoin (DOGE)", callback_data="deposit_doge")],
        [InlineKeyboardButton(text="💎 Polygon (MATIC)", callback_data="deposit_matic")],
        [InlineKeyboardButton(text="🔷 Bitcoin Cash (BCH)", callback_data="deposit_bch")],
        [InlineKeyboardButton(text="⚡ Dash (DASH)", callback_data="deposit_dash")],
        [InlineKeyboardButton(text="🛡️ Zcash (ZEC)", callback_data="deposit_zec")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="deposit_menu")]
    ])

    text = (
        "🔗 <b>Другие валюты</b>\n\n"
        "Выберите валюту для пополнения:"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


async def show_deposit_history(callback: CallbackQuery):
    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return


        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="deposit_history")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="deposit_menu")]
        ])

        text = (
            "📊 <b>История депозитов</b>\n\n"
            "У вас пока нет депозитов.\n\n"
            "Депозиты будут отображаться здесь после поступления средств на ваши адреса."
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


async def show_withdrawal_menu(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Создать вывод", callback_data="create_withdrawal")],
        [InlineKeyboardButton(text="📊 История выводов", callback_data="withdrawal_history")],
        [InlineKeyboardButton(text="💰 Комиссии сетей", callback_data="network_fees")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="withdrawal_help")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])

    text = (
        "💸 <b>Вывод средств</b>\n\n"
        "Выберите действие:\n\n"
        "⚠️ <b>Важно:</b>\n"
        "• Проверяйте адрес получателя перед отправкой\n"
        "• Выводы необратимы после отправки в блокчейн\n"
        "• Крупные суммы могут требовать дополнительного подтверждения\n"
        "• Учитывайте комиссии сети при выводе"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "create_withdrawal")
async def start_withdrawal_process(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BlockchainStates.waiting_withdrawal_currency)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="₿ Bitcoin (BTC)", callback_data="withdraw_currency_BTC")],
        [InlineKeyboardButton(text="Ξ Ethereum (ETH)", callback_data="withdraw_currency_ETH")],
        [InlineKeyboardButton(text="💰 USDT", callback_data="withdraw_currency_USDT")],
        [InlineKeyboardButton(text="🔗 Другие", callback_data="withdraw_currency_other")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="withdrawal_menu")]
    ])

    text = (
        "💸 <b>Создание вывода</b>\n\n"
        "Шаг 1/5: Выберите валюту для вывода:"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("withdraw_currency_"))
async def select_withdrawal_currency(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.split("_")[-1]

    if currency == "other":
        await show_other_withdrawal_currencies(callback, state)
        return

    await state.update_data(currency=currency)
    await select_withdrawal_network(callback, state, currency)


async def show_other_withdrawal_currencies(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Litecoin (LTC)", callback_data="withdraw_currency_LTC")],
        [InlineKeyboardButton(text="🐕 Dogecoin (DOGE)", callback_data="withdraw_currency_DOGE")],
        [InlineKeyboardButton(text="💎 Polygon (MATIC)", callback_data="withdraw_currency_MATIC")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="create_withdrawal")]
    ])

    text = (
        "💸 <b>Создание вывода</b>\n\n"
        "Шаг 1/5: Выберите валюту для вывода:"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


async def select_withdrawal_network(callback: CallbackQuery, state: FSMContext, currency: str):
    await state.set_state(BlockchainStates.waiting_withdrawal_network)

    network_options = {
        "BTC": [("Bitcoin", "bitcoin")],
        "ETH": [("Ethereum", "ethereum")],
        "USDT": [
            ("TRON (TRC20)", "tron"),
            ("Ethereum (ERC20)", "ethereum"),
            ("BSC (BEP20)", "bsc")
        ],
        "LTC": [("Litecoin", "litecoin")],
        "DOGE": [("Dogecoin", "dogecoin")],
        "MATIC": [("Polygon", "polygon")]
    }

    networks = network_options.get(currency, [])

    if len(networks) == 1:
        await state.update_data(network=networks[0][1])
        await request_withdrawal_address(callback, state)
        return

    keyboard_buttons = []
    for network_name, network_value in networks:
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=network_name,
                callback_data=f"withdraw_network_{network_value}"
            )
        ])

    keyboard_buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="create_withdrawal")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    text = (
        f"💸 <b>Создание вывода</b>\n\n"
        f"Шаг 2/5: Выберите сеть для {currency}:"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("withdraw_network_"))
async def select_network(callback: CallbackQuery, state: FSMContext):
    network = callback.data.split("_")[-1]
    await state.update_data(network=network)
    await request_withdrawal_address(callback, state)


async def request_withdrawal_address(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BlockchainStates.waiting_withdrawal_address)

    data = await state.get_data()
    currency = data.get("currency")
    network = data.get("network")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="withdrawal_menu")]
    ])

    text = (
        f"💸 <b>Создание вывода</b>\n\n"
        f"Шаг 3/5: Введите адрес получателя\n\n"
        f"💰 <b>Валюта:</b> {currency}\n"
        f"🌐 <b>Сеть:</b> {network.title()}\n\n"
        f"Отправьте адрес получателя:"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.message(BlockchainStates.waiting_withdrawal_address)
async def receive_withdrawal_address(message: Message, state: FSMContext):
    address = message.text.strip()

    if len(address) < 10:
        await message.answer("❌ Неверный формат адреса. Попробуйте еще раз:")
        return

    await state.update_data(address=address)
    await request_withdrawal_amount(message, state)


async def request_withdrawal_amount(message: Message, state: FSMContext):
    await state.set_state(BlockchainStates.waiting_withdrawal_amount)

    data = await state.get_data()
    currency = data.get("currency")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Весь баланс", callback_data="withdraw_all_balance")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="withdrawal_menu")]
    ])

    balance = "0.00"

    text = (
        f"💸 <b>Создание вывода</b>\n\n"
        f"Шаг 4/5: Введите сумму для вывода\n\n"
        f"💰 <b>Доступно:</b> {balance} {currency}\n"
        f"💸 <b>Комиссия сети:</b> ~{_get_network_fee(currency)} {currency}\n\n"
        f"Введите сумму:"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(BlockchainStates.waiting_withdrawal_amount)
async def receive_withdrawal_amount(message: Message, state: FSMContext):
    try:
        amount = Decimal(message.text.strip())
        if amount <= 0:
            raise ValueError("Сумма должна быть больше нуля")

        await state.update_data(amount=amount)
        await confirm_withdrawal(message, state)

    except (ValueError, TypeError):
        await message.answer("❌ Неверный формат суммы. Введите число:")


async def confirm_withdrawal(message: Message, state: FSMContext):
    await state.set_state(BlockchainStates.confirming_withdrawal)

    data = await state.get_data()
    currency = data.get("currency")
    network = data.get("network")
    address = data.get("address")
    amount = data.get("amount")

    fee = Decimal(_get_network_fee(currency))
    total = amount + fee

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_withdrawal")],
        [InlineKeyboardButton(text="✏️ Изменить", callback_data="create_withdrawal")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="withdrawal_menu")]
    ])

    text = (
        f"💸 <b>Подтверждение вывода</b>\n\n"
        f"💰 <b>Валюта:</b> {currency}\n"
        f"🌐 <b>Сеть:</b> {network.title()}\n"
        f"📍 <b>Адрес:</b> <code>{address}</code>\n"
        f"💵 <b>Сумма:</b> {amount} {currency}\n"
        f"💸 <b>Комиссия:</b> {fee} {currency}\n"
        f"💳 <b>К списанию:</b> {total} {currency}\n\n"
        f"⚠️ <b>Внимание:</b>\n"
        f"• Проверьте правильность адреса\n"
        f"• Операция необратима\n"
        f"• Средства поступят после подтверждения в блокчейне"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "confirm_withdrawal")
async def process_withdrawal_confirmation(callback: CallbackQuery, state: FSMContext):
    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        data = await state.get_data()
        currency = data.get("currency")
        network_str = data.get("network")
        address = data.get("address")
        amount = data.get("amount")

        try:
            network = BlockchainNetwork(network_str)

            withdrawal = await blockchain_service.create_withdrawal_request(
                db=db,
                user=user,
                currency=currency,
                network=network,
                to_address=address,
                amount=amount
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 История выводов", callback_data="withdrawal_history")],
                [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
            ])

            status_text = "⏳ Ожидает обработки"
            if withdrawal.requires_approval:
                status_text = "⏳ Ожидает одобрения"

            text = (
                f"✅ <b>Запрос на вывод создан</b>\n\n"
                f"🆔 <b>ID:</b> {withdrawal.id}\n"
                f"💰 <b>Валюта:</b> {currency}\n"
                f"💵 <b>Сумма:</b> {amount} {currency}\n"
                f"📊 <b>Статус:</b> {status_text}\n\n"
                f"Вы получите уведомление, когда средства будут отправлены."
            )

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()
            await state.clear()

        except Exception as e:
            logger.error("❌ Не удалось создать вывод", error=str(e), exc_info=True)
            await callback.answer("❌ Ошибка при создании вывода")


def _get_confirmations_required(network: BlockchainNetwork) -> int:
    confirmations = {
        BlockchainNetwork.BITCOIN: 1,
        BlockchainNetwork.ETHEREUM: 12,
        BlockchainNetwork.TRON: 19,
        BlockchainNetwork.BINANCE_SMART_CHAIN: 15,
        BlockchainNetwork.POLYGON: 128,
    }
    return confirmations.get(network, 12)


def _get_estimated_time(network: BlockchainNetwork) -> str:
    times = {
        BlockchainNetwork.BITCOIN: "10-60 минут",
        BlockchainNetwork.ETHEREUM: "3-15 минут",
        BlockchainNetwork.TRON: "1-3 минуты",
        BlockchainNetwork.BINANCE_SMART_CHAIN: "1-3 минуты",
        BlockchainNetwork.POLYGON: "2-5 минут",
    }
    return times.get(network, "5-30 минут")


def _get_network_fee(currency: str) -> str:
    fees = {
        "BTC": "0.0005",
        "ETH": "0.005",
        "USDT": "1.0",
        "LTC": "0.001",
        "DOGE": "1.0",
    }
    return fees.get(currency, "0.001")


@router.callback_query(F.data == "deposit_menu")
async def back_to_deposit_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_deposit_menu(callback.message)
    await callback.answer()


@router.callback_query(F.data == "withdrawal_menu")
async def back_to_withdrawal_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_withdrawal_menu(callback.message)
    await callback.answer()
