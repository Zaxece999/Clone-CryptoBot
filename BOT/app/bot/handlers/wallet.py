from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import structlog

from app.database import get_async_db
from app.services.wallet import wallet_service
from app.services.auth import auth_service
from app.services.balance_checker import get_all_wallets_balances, get_total_usd_balance, format_balance_display
from app.services.balance_sync import balance_sync_service
from app.bot.utils.texts import get_text
from app.utils.exceptions import WalletError, ValidationError
from app.services.settings import settings_service
from app.services.exchange_rates import exchange_rate_service

logger = structlog.get_logger(__name__)
router = Router()


class WalletStates(StatesGroup):
    selecting_currency = State()
    entering_address = State()
    entering_amount = State()
    confirming_transaction = State()


def get_wallet_menu_keyboard(language: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Баланс", callback_data="wallet_balance"),
            InlineKeyboardButton(text="📥 Получить", callback_data="wallet_receive")
        ],
        [
            InlineKeyboardButton(text="📤 Отправить", callback_data="wallet_send"),
            InlineKeyboardButton(text="📋 История", callback_data="wallet_history")
        ],
        [
            InlineKeyboardButton(text="➕ Создать кошелек", callback_data="wallet_create")
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="wallet_refresh")
        ]
    ])


def get_currency_keyboard(currencies: list, prefix: str = "create", language: str = "ru") -> InlineKeyboardMarkup:
    buttons = []
    for i in range(0, len(currencies), 2):
        row = []
        for j in range(2):
            if i + j < len(currencies):
                currency = currencies[i + j]
                row.append(InlineKeyboardButton(
                    text=f"{currency}",
                    callback_data=f"{prefix}_{currency}"
                ))
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="wallet_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard(callback_data: str = "wallet_menu", language: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)]
    ])


@router.message(Command("wallet"))
async def wallet_command(message: Message, state: FSMContext):
    try:
        async for db in get_async_db():
            user = await auth_service.get_or_create_user_by_telegram(
                db=db,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                language_code=message.from_user.language_code
            )

            balances = await get_all_wallets_balances(db, user.id)

            try:
                await balance_sync_service.sync_user_balances_to_webapp(db, user.id)
            except Exception as e:
                logger.warning("Failed to sync balances to webapp", user_id=user.id, error=str(e))

            if not balances:
                await wallet_service.create_default_wallets(db, user)
                text = "🎉 Добро пожаловать! Для вас созданы базовые кошельки.\n\n"
            else:
                text = "💰 Ваши кошельки:\n\n"

                for currency, (balance, usd_value, frozen_balance) in balances.items():
                    text += format_balance_display(currency, balance, usd_value, frozen_balance) + "\n\n"

                total_usd = await get_total_usd_balance(balances)
                if total_usd > 0:
                    text += f"💎 Общий баланс: ≈ ${total_usd:.2f} USD\n\n"

                text += "Выберите действие:"

            keyboard = get_wallet_menu_keyboard(message.from_user.language_code)
            await message.answer(text, reply_markup=keyboard)
            await state.clear()
            break

    except Exception as e:
        logger.error(
            "Wallet command failed",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True
        )
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data.startswith("wallet_"))
async def wallet_callback(callback: CallbackQuery, state: FSMContext):
    try:
        action = callback.data.split("_", 1)[1]

        async for db in get_async_db():
            user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
            if not user:
                await callback.answer("❌ Пользователь не найден")
                return

            if action == "balance":
                await show_balance(callback, user, db)
            elif action == "send":
                await start_send_crypto(callback, state, user, db)
            elif action == "receive":
                await show_receive_addresses(callback, user, db)
            elif action == "history":
                await show_transaction_history(callback, user, db)
            elif action == "create":
                await show_create_wallet_menu(callback, user, db)
            elif action == "refresh":
                await refresh_wallets(callback, user, db)
            elif action == "menu":
                await show_wallet_menu(callback, user, db)

            await callback.answer()
            break

    except Exception as e:
        logger.error(
            "Wallet callback failed",
            user_id=callback.from_user.id,
            action=callback.data,
            error=str(e),
            exc_info=True
        )
        await callback.answer("❌ Произошла ошибка")


@router.callback_query(F.data.startswith("create_wallet_"))
async def create_wallet_callback(callback: CallbackQuery):
    try:
        parts = callback.data.split("_")
        if len(parts) < 4 or parts[0] != "create" or parts[1] != "wallet":
            await callback.answer("❌ Неверный формат данных")
            return

        currency = parts[2]
        network = parts[3]

        async for db in get_async_db():
            user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
            if not user:
                await callback.answer("❌ Пользователь не найден")
                return

            existing_wallet = await wallet_service.get_user_wallet(db, user.id, currency, network)
            if existing_wallet:
                display_name = f"{currency} ({network})" if network != currency else currency
                await callback.answer(f"❌ Кошелек {display_name} уже существует")
                return

            display_name = f"{currency} ({network})" if network != currency else currency
            await callback.message.edit_text(f"⏳ Создаю кошелек {display_name}...")

            wallet = await wallet_service.create_wallet(
                db=db,
                user=user,
                currency=currency,
                network=network,
                wallet_name=f"My {currency} {network} Wallet"
            )

            addresses = await wallet_service.get_wallet_addresses(db, wallet.id)
            first_address = addresses[0] if addresses else None

            text = f"✅ Кошелек {display_name} создан!\n\n"
            if first_address:
                text += f"📍 Адрес для получения:\n`{first_address.address}`\n\n"
            text += "Теперь вы можете получать и отправлять криптовалюту."

            keyboard = get_back_keyboard("wallet_menu")
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            await callback.answer("✅ Кошелек создан!")
            break

    except Exception as e:
        logger.error(
            "Create wallet failed",
            user_id=callback.from_user.id,
            callback_data=callback.data,
            error=str(e),
            exc_info=True
        )
        await callback.message.edit_text("❌ Ошибка при создании кошелька")
        await callback.answer("❌ Ошибка при создании кошелька")


async def show_wallet_menu(callback: CallbackQuery, user, db: AsyncSession):
    from app.config import settings

    currency_info = {
        "BTC": ("Bitcoin", "https://bitcoin.org/"),
        "ETH": ("Ethereum", "https://ethereum.org/"),
        "LTC": ("Litecoin", "https://litecoin.org/"),
        "USDT": ("Tether", "https://tether.to/"),
        "BNB": ("Binance Coin", "https://www.binance.com/"),
        "TRX": ("TRON", "https://tron.network/"),
        "TON": ("TON", "https://ton.org/"),
        "GRAM": ("Gram", "https://ton.org/"),
        "DOGE": ("Dogecoin", "https://dogecoin.com/"),
        "SOL": ("Solana", "https://solana.com/"),
        "USDC": ("USD Coin", "https://www.centre.io/usdc"),
        "NOT": ("Notcoin", "https://notcoin.org/"),
        "TRUMP": ("TrumpCoin", "https://trumpcoin.com/"),
        "MELANIA": ("Melania Coin", "https://melaniacoin.com/"),
        "PEPE": ("Pepe", "https://pepe.vip/"),
        "WIF": ("dogwifhat", "https://dogwifhat.io/"),
        "BONK": ("Bonk", "https://bonkcoin.com/"),
        "MAJOR": ("Major", "https://major.app/"),
        "MY": ("My", "https://mytoken.com/"),
        "DOGS": ("Dogs", "https://dogs.dog/"),
        "MEMHASH": ("Memhash", "https://memhash.io/"),
        "HMSTR": ("Hamster", "https://hamster.io/"),
        "CATI": ("Catizen", "https://catizen.ai/"),
    }

    wallet_text = "👛 Кошелёк\n\n"

    try:
        balances = await get_all_wallets_balances(db, user.id)

        try:
            await balance_sync_service.sync_user_balances_to_webapp(db, user.id)
        except Exception as e:
            logger.warning("Failed to sync balances to webapp in menu", user_id=user.id, error=str(e))

        ordered_currencies = [
            "ETH",
            "USDT",
            "LTC",
            "BNB",
            "TRX",
            "TON",
            "DOGE",
            "SOL",
            "USDC",
            "BTC",
        ]

        for currency in ordered_currencies:
            name, url = currency_info.get(currency, (currency, "#"))
            if currency not in balances or not balances:
                wallet_text += f"🪙 [{name}]({url}): 0 {currency}\n\n"
                continue

            balance, usd_value, frozen_balance = balances[currency]

            if balance == "ERROR":
                wallet_text += f"🪙 [{name}]({url}): ERROR ❌\n\n"
                continue

            try:
                from decimal import Decimal
                total_balance = Decimal(balance)
                frozen_amount = Decimal(frozen_balance)
                available_balance = total_balance - frozen_amount
                line = f"🪙 [{name}]({url}): {available_balance} {currency}"
                if frozen_amount > 0:
                    line += f" ({frozen_balance} {currency} удержано)"
                wallet_text += line + "\n\n"
            except Exception as e:
                logger.error(f"Error calculating available balance for {currency}", error=str(e))
                wallet_text += f"🪙 [{name}]({url}): {balance} {currency}\n\n"

        total_usd = await get_total_usd_balance(balances)
        try:
            btc_usd = await exchange_rate_service.get_exchange_rate("BTC", "USD")
            if btc_usd and btc_usd > 0:
                total_btc = (total_usd / btc_usd) if total_usd > 0 else 0.0
                total_btc_line = f"≈ {total_btc:.8f} BTC"
            else:
                total_btc_line = "≈ 0.00000000 BTC"

            user_settings = await settings_service.get_or_create_user_settings(db, user.id)
            display_currency = (user_settings.local_currency or "USD").upper()
            if display_currency == "USD":
                local_line = f"${total_usd:.2f} USD"
            else:
                rate_usd_to_fiat = await exchange_rate_service.get_exchange_rate("USDC", display_currency)
                if rate_usd_to_fiat and rate_usd_to_fiat > 0:
                    amount_in_fiat = (total_usd * rate_usd_to_fiat) if total_usd > 0 else 0.0
                    local_line = f"{amount_in_fiat:.2f} {display_currency}"
                else:
                    local_line = f"0.00 {display_currency}"

            if local_line:
                wallet_text += f"{total_btc_line} ({local_line})\n\n"
            else:
                wallet_text += f"{total_btc_line}\n\n"
        except Exception as e:
            logger.warning("Failed to render totals (BTC/local)", user_id=user.id, error=str(e))

    except Exception as e:
        logger.error("Error getting wallet balances for menu", error=str(e))
        wallet_text += "❌ Ошибка при загрузке балансов\n\n"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть в приложении", callback_data="open_app")],
        [InlineKeyboardButton(text="Пополнить", callback_data="wallet_receive"), InlineKeyboardButton(text="Вывести", callback_data="wallet_send")],
        [InlineKeyboardButton(text="Адресная книга", callback_data="address_book")],
        [InlineKeyboardButton(text="Комиссии и лимиты", callback_data="fees_limits")],
        [InlineKeyboardButton(text="Назад", callback_data="main_menu")]
    ])

    await callback.message.edit_text(
        wallet_text,
        reply_markup=keyboard,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


async def show_balance(callback: CallbackQuery, user, db: AsyncSession):
    try:
        balances = await get_all_wallets_balances(db, user.id)

        try:
            await balance_sync_service.sync_user_balances_to_webapp(db, user.id)
        except Exception as e:
            logger.warning("Failed to sync balances to webapp in balance view", user_id=user.id, error=str(e))

        if not balances:
            text = "❌ У вас нет кошельков.\nСоздайте кошелек для начала работы."
            keyboard = get_currency_keyboard(
                currencies=["BTC", "ETH", "USDT", "LTC"],
                prefix="create"
            )
        else:
            text = "💰 Баланс ваших кошельков:\n\n"

            for currency, (balance, usd_value, frozen_balance) in balances.items():
                text += format_balance_display(currency, balance, usd_value, frozen_balance) + "\n\n"

            total_usd = await get_total_usd_balance(balances)
            if total_usd > 0:
                text += f"💎 Общий баланс: ≈ ${total_usd:.2f} USD"

            keyboard = get_back_keyboard("wallet_menu")

        await callback.message.edit_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error("Show balance failed", error=str(e))
        await callback.message.edit_text("❌ Ошибка при получении баланса")


async def show_receive_addresses(callback: CallbackQuery, user, db: AsyncSession):
    try:
        wallets = await wallet_service.get_user_wallets(db, user.id, include_addresses=True)

        if not wallets:
            text = "❌ У вас нет кошельков"
            keyboard = get_currency_keyboard(
                currencies=["BTC", "ETH", "USDT", "LTC"],
                prefix="create"
            )
        else:
            text = "📥 Адреса для получения:\n\n"

            for wallet in wallets:
                address = await wallet_service.get_unused_address(db, wallet)

                if wallet.currency in ["USDT", "USDC"] and wallet.network != wallet.currency:
                    display_name = f"{wallet.currency} ({wallet.network})"
                else:
                    display_name = wallet.currency

                text += f"🪙 {display_name}:\n"
                text += f"`{address.address}`\n\n"

            text += "💡 Отправляйте только соответствующую криптовалюту на каждый адрес!\n"
            text += "⚠️ Обязательно проверяйте сеть при отправке!"
            keyboard = get_back_keyboard("wallet_menu")

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logger.error("Show receive addresses failed", error=str(e))
        await callback.message.edit_text("❌ Ошибка при получении адресов")


async def show_transaction_history(callback: CallbackQuery, user, db: AsyncSession):
    try:
        wallets = await wallet_service.get_user_wallets(db, user.id, include_addresses=True)

        if not wallets:
            text = "❌ У вас нет кошельков"
            keyboard = get_back_keyboard("wallet_menu")
        else:
            text = "📋 История транзакций:\n\n"

            has_transactions = False
            for wallet in wallets:
                for address in wallet.addresses:
                    transactions = await wallet_service.sync_transactions(db, address)

                    if address.transactions:
                        has_transactions = True
                        for tx in address.transactions[-5:]:
                            direction = "📥" if tx.is_incoming() else "📤"
                            status = "✅" if tx.is_confirmed else "⏳"

                            text += f"{direction} {status} {tx.amount} {wallet.currency}\n"
                            text += f"   {tx.short_hash}\n"
                            if tx.blockchain_time:
                                text += f"   {tx.blockchain_time.strftime('%d.%m.%Y %H:%M')}\n"
                            text += "\n"

            if not has_transactions:
                text += "Транзакций пока нет"

            keyboard = get_back_keyboard("wallet_menu")

        await callback.message.edit_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error("Show transaction history failed", error=str(e))
        await callback.message.edit_text("❌ Ошибка при получении истории")


async def show_create_wallet_menu(callback: CallbackQuery, user, db: AsyncSession):
    try:
        existing_wallets = await wallet_service.get_user_wallets(db, user.id)
        existing_wallet_keys = {f"{w.currency}_{w.network}" for w in existing_wallets}

        from app.config import settings
        currency_networks = settings.supported_currency_networks

        available_options = []
        for currency, networks in currency_networks.items():
            for network in networks:
                wallet_key = f"{currency}_{network}"
                if wallet_key not in existing_wallet_keys:
                    if len(networks) > 1:
                        display_name = f"{currency} ({network})"
                    else:
                        display_name = currency
                    available_options.append((display_name, f"create_wallet_{currency}_{network}"))

        if not available_options:
            await callback.answer("✅ Все поддерживаемые кошельки уже созданы")
            return

        text = "➕ Выберите кошелек для создания:"

        buttons = []
        for i in range(0, len(available_options), 2):
            row = []
            for j in range(2):
                if i + j < len(available_options):
                    display_name, callback_data = available_options[i + j]
                    row.append(InlineKeyboardButton(
                        text=display_name,
                        callback_data=callback_data
                    ))
            buttons.append(row)

        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="wallet_menu")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error("Show create wallet menu failed", error=str(e))
        await callback.message.edit_text("❌ Ошибка при загрузке меню")


async def refresh_wallets(callback: CallbackQuery, user, db: AsyncSession):
    try:
        await callback.message.edit_text("🔄 Обновляю информацию о кошельках...")

        wallets = await wallet_service.get_user_wallets(db, user.id)

        for wallet in wallets:
            await wallet_service.update_balances(db, wallet)

        await show_wallet_menu(callback, user, db)
        await callback.answer("✅ Информация обновлена")

    except Exception as e:
        logger.error("Refresh wallets failed", error=str(e))
        await callback.message.edit_text("❌ Ошибка при обновлении")


async def start_send_crypto(callback: CallbackQuery, state: FSMContext, user, db: AsyncSession):
    try:
        balances = await get_all_wallets_balances(db, user.id)

        if not balances:
            await callback.answer("❌ У вас нет кошельков для отправки")
            return

        available_currencies = []
        for currency, (balance, usd_value, frozen_balance) in balances.items():
            if balance != "ERROR" and float(balance) > 0:
                available_currencies.append(currency)

        if not available_currencies:
            await callback.message.edit_text(
                "❌ У вас нет средств для отправки.\n\n"
                "Пополните кошелек и попробуйте снова.",
                reply_markup=get_back_keyboard("wallet_menu")
            )
            return

        buttons = []
        for i in range(0, len(available_currencies), 2):
            row = []
            for j in range(2):
                if i + j < len(available_currencies):
                    currency = available_currencies[i + j]
                    balance, usd_value, frozen_balance = balances[currency]

                    try:
                        from decimal import Decimal
                        total_balance = Decimal(balance)
                        frozen_amount = Decimal(frozen_balance)
                        available_balance = total_balance - frozen_amount
                        display_text = f"{currency} ({available_balance})"
                    except Exception as e:
                        logger.error(f"Error calculating available balance for {currency}", error=str(e))
                        display_text = f"{currency} ({balance})"
                    callback_data = f"send_currency_{currency}"

                    row.append(InlineKeyboardButton(
                        text=display_text,
                        callback_data=callback_data
                    ))
            buttons.append(row)

        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="wallet_menu")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        text = "📤 Выберите валюту для отправки:"
        await callback.message.edit_text(text, reply_markup=keyboard)
        await state.set_state(WalletStates.selecting_currency)

    except Exception as e:
        logger.error("Start send crypto failed", error=str(e))
        await callback.message.edit_text("❌ Ошибка при инициализации отправки")


@router.callback_query(F.data.startswith("send_currency_"))
async def send_select_currency(callback: CallbackQuery, state: FSMContext):
    try:
        currency = callback.data.split("_", 2)[2]

        async for db in get_async_db():
            user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
            if not user:
                await callback.answer("❌ Пользователь не найден")
                return

            from app.services.balance_checker import get_wallets_balances_by_network
            network_balances = await get_wallets_balances_by_network(db, user.id, currency)

            if not network_balances:
                await callback.answer("❌ Кошельки для этой валюты не найдены")
                return

            available_networks = []
            for network, (balance, usd_value, frozen_balance) in network_balances.items():
                if balance != "ERROR" and float(balance) > 0:
                    available_networks.append((network, balance, usd_value))

            if not available_networks:
                await callback.message.edit_text(
                    f"❌ У вас нет средств {currency} для отправки.\n\n"
                    f"Пополните кошелек и попробуйте снова.",
                    reply_markup=get_back_keyboard("wallet_send")
                )
                return

            if len(available_networks) == 1:
                network, balance, usd_value = available_networks[0]
                await select_network_for_send(callback, state, user, db, currency, network, balance)
                return

            buttons = []
            for network, balance, usd_value in available_networks:
                from app.bot.handlers.fees_limits import FEES_LIMITS_DATA

                network_name = network
                if currency in FEES_LIMITS_DATA and network in FEES_LIMITS_DATA[currency]:
                    network_info = FEES_LIMITS_DATA[currency][network]
                    network_name = network_info["network_name"]
                    fee_info = network_info.get("withdrawal_fee", "")

                    display_text = f"{network_name}\n💰 {balance} {currency}"
                    if fee_info and not "\n" in fee_info:
                        display_text += f"\n💸 Комиссия: {fee_info}"
                else:
                    display_text = f"{network}\n💰 {balance} {currency}"

                buttons.append([InlineKeyboardButton(
                    text=display_text,
                    callback_data=f"send_network_{currency}_{network}"
                )])

            buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="wallet_send")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            text = f"📤 Выберите сеть для отправки {currency}:\n\n"
            text += "💡 Учитывайте комиссии при выборе сети"

            await callback.message.edit_text(text, reply_markup=keyboard)
            break

    except Exception as e:
        logger.error("Send select currency failed", error=str(e))
        await callback.answer("❌ Ошибка при выборе валюты")


@router.callback_query(F.data.startswith("send_network_"))
async def send_select_network(callback: CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split("_", 3)
        if len(parts) < 4:
            await callback.answer("❌ Неверный формат данных")
            return

        currency = parts[2]
        network = parts[3]

        async for db in get_async_db():
            user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
            if not user:
                await callback.answer("❌ Пользователь не найден")
                return

            from app.services.balance_checker import get_wallets_balances_by_network
            network_balances = await get_wallets_balances_by_network(db, user.id, currency)

            if network not in network_balances:
                await callback.answer("❌ Кошелек для этой сети не найден")
                return

            balance, usd_value, frozen_balance = network_balances[network]
            if balance == "ERROR" or float(balance) <= 0:
                await callback.answer("❌ Недостаточно средств в этой сети")
                return

            await select_network_for_send(callback, state, user, db, currency, network, balance)
            break

    except Exception as e:
        logger.error("Send select network failed", error=str(e))
        await callback.answer("❌ Ошибка при выборе сети")


async def select_network_for_send(callback: CallbackQuery, state: FSMContext, user, db: AsyncSession, currency: str, network: str, balance: str):
    try:
        wallet = await wallet_service.get_user_wallet(db, user.id, currency, network)
        if not wallet:
            await callback.answer("❌ Кошелек не найден")
            return

        display_name = currency
        if currency in ["USDT", "USDC"] and network != currency:
            display_name = f"{currency} ({network})"

        from app.bot.handlers.fees_limits import FEES_LIMITS_DATA

        min_withdrawal = None
        fee_info = None
        if currency in FEES_LIMITS_DATA and network in FEES_LIMITS_DATA[currency]:
            network_info = FEES_LIMITS_DATA[currency][network]
            withdrawal_limit = network_info.get("withdrawal_limit", "")
            fee_info = network_info.get("withdrawal_fee", "")

            if "от " in withdrawal_limit:
                try:
                    min_amount_str = withdrawal_limit.split("от ")[1].split(" ")[0]
                    min_withdrawal = float(min_amount_str)
                except:
                    pass

        await state.update_data(
            send_currency=currency,
            send_network=network,
            wallet_id=wallet.id,
            current_balance=balance,
            min_withdrawal=min_withdrawal,
            fee_info=fee_info
        )
        await state.set_state(WalletStates.entering_address)

        from app.services.address_book import address_book_service
        saved_addresses = await address_book_service.get_entries_by_network(db, user.id, network)

        text = f"📍 Введите адрес получателя для {display_name}:\n\n"
        text += f"💰 Доступный баланс: {balance} {display_name}\n"

        if fee_info:
            if "\n" in fee_info:
                text += f"💸 {fee_info}\n"
            else:
                text += f"💸 Комиссия: {fee_info}\n"

        if min_withdrawal:
            text += f"📊 Минимальная сумма: {min_withdrawal} {currency}\n"

        text += "\n"

        buttons = []

        for entry in saved_addresses[:5]:
            buttons.append([InlineKeyboardButton(
                text=f"📋 {entry.name}",
                callback_data=f"use_address_{entry.id}"
            )])

        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"send_currency_{currency}")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        if saved_addresses:
            text += "Или выберите из сохраненных адресов:"

        await callback.message.edit_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error("Select network for send failed", error=str(e))
        await callback.message.edit_text("❌ Ошибка при выборе сети")


@router.callback_query(F.data.startswith("send_"))
async def send_legacy_handler(callback: CallbackQuery, state: FSMContext):
    if callback.data.startswith("send_currency_"):
        await send_select_currency(callback, state)
    elif callback.data.startswith("send_network_"):
        await send_select_network(callback, state)
    else:
        await callback.answer("❌ Устаревший формат данных")


@router.callback_query(F.data.startswith("use_address_"))
async def use_saved_address(callback: CallbackQuery, state: FSMContext):
    try:
        entry_id = callback.data.split("_", 2)[2]

        async for db in get_async_db():
            user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
            if not user:
                await callback.answer("❌ Пользователь не найден")
                return

            from app.services.address_book import address_book_service
            entry = await address_book_service.get_entry_by_id(db, user.id, entry_id)

            if not entry:
                await callback.answer("❌ Адрес не найден")
                return

            await state.update_data(recipient_address=entry.address, address_name=entry.name)
            await state.set_state(WalletStates.entering_amount)

            data = await state.get_data()
            currency = data.get("send_currency")
            balance = data.get("current_balance", "0")

            text = f"💰 Введите сумму {currency} для отправки:\n\n"
            text += f"📍 Получатель: {entry.name}\n"
            text += f"📋 Адрес: `{entry.address[:10]}...{entry.address[-10:]}`\n\n"
            text += f"💳 Доступный баланс: {balance} {currency}"

            keyboard = get_back_keyboard("wallet_send")
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            break

    except Exception as e:
        logger.error("Use saved address failed", error=str(e))
        await callback.answer("❌ Ошибка при выборе адреса")


@router.message(WalletStates.entering_address)
async def process_address_input(message: Message, state: FSMContext):
    try:
        address = message.text.strip()

        if not address:
            await message.answer("❌ Адрес не может быть пустым. Попробуйте еще раз.")
            return

        if len(address) < 10:
            await message.answer("❌ Адрес слишком короткий. Попробуйте еще раз.")
            return

        await state.update_data(recipient_address=address)
        await state.set_state(WalletStates.entering_amount)

        data = await state.get_data()
        currency = data.get("send_currency")
        balance = data.get("current_balance", "0")

        text = f"💰 Введите сумму {currency} для отправки:\n\n"
        text += f"📍 Адрес получателя: `{address[:10]}...{address[-10:]}`\n\n"
        text += f"💳 Доступный баланс: {balance} {currency}"

        keyboard = get_back_keyboard("wallet_send")
        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logger.error("Process address input failed", error=str(e))
        await message.answer("❌ Произошла ошибка")


@router.message(WalletStates.entering_amount)
async def process_amount_input(message: Message, state: FSMContext):
    try:
        amount_text = message.text.strip()

        try:
            amount = float(amount_text)
        except ValueError:
            await message.answer("❌ Введите корректную сумму (число).")
            return

        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше нуля.")
            return

        data = await state.get_data()
        currency = data.get("send_currency")
        network = data.get("send_network")
        current_balance = float(data.get("current_balance", "0"))
        recipient_address = data.get("recipient_address")
        address_name = data.get("address_name", "")
        min_withdrawal = data.get("min_withdrawal")
        fee_info = data.get("fee_info")

        if min_withdrawal and amount < min_withdrawal:
            await message.answer(
                f"❌ Сумма меньше минимальной!\n\n"
                f"💰 Запрашиваемая сумма: {amount} {currency}\n"
                f"📊 Минимальная сумма: {min_withdrawal} {currency}\n\n"
                f"Введите сумму не меньше {min_withdrawal} {currency}."
            )
            return

        if amount > current_balance:
            await message.answer(
                f"❌ Недостаточно средств!\n\n"
                f"💰 Запрашиваемая сумма: {amount} {currency}\n"
                f"💳 Доступный баланс: {current_balance} {currency}\n\n"
                f"Введите сумму не больше {current_balance} {currency}."
            )
            return

        from app.bot.handlers.fees_limits import FEES_LIMITS_DATA

        fee_amount = 0
        fee_display = ""

        if currency in FEES_LIMITS_DATA and network in FEES_LIMITS_DATA[currency]:
            network_info = FEES_LIMITS_DATA[currency][network]
            fee_info_raw = network_info.get("withdrawal_fee", "")

            if fee_info_raw and not "\n" in fee_info_raw:
                try:
                    fee_parts = fee_info_raw.split()
                    for i, part in enumerate(fee_parts):
                        try:
                            fee_amount = float(part)
                            if i + 1 < len(fee_parts):
                                fee_currency = fee_parts[i + 1]
                                fee_display = f"{fee_amount} {fee_currency}"
                            break
                        except ValueError:
                            continue
                except:
                    fee_display = fee_info_raw
            else:
                fee_display = fee_info_raw or "Уточняется"

        total_needed = amount
        if fee_amount > 0 and fee_display.endswith(currency):
            total_needed = amount + fee_amount

            if total_needed > current_balance:
                await message.answer(
                    f"❌ Недостаточно средств с учетом комиссии!\n\n"
                    f"💰 Сумма к отправке: {amount} {currency}\n"
                    f"💸 Комиссия сети: {fee_display}\n"
                    f"📊 Всего потребуется: {total_needed} {currency}\n"
                    f"💳 Доступный баланс: {current_balance} {currency}\n\n"
                    f"Уменьшите сумму или пополните баланс."
                )
                return

        await state.update_data(send_amount=amount, total_needed=total_needed, fee_display=fee_display)
        await state.set_state(WalletStates.confirming_transaction)

        display_name = currency
        if currency in ["USDT", "USDC"] and network != currency:
            display_name = f"{currency} ({network})"

        text = f"🔍 Подтвердите отправку:\n\n"
        text += f"💰 Сумма: {amount} {currency}\n"

        if fee_display:
            text += f"💸 Комиссия сети: {fee_display}\n"
            if total_needed > amount:
                text += f"📊 Всего к списанию: {total_needed} {currency}\n"

        if address_name:
            text += f"📍 Получатель: {address_name}\n"
        text += f"📋 Адрес: `{recipient_address}`\n"
        text += f"🌐 Сеть: {network}\n\n"

        remaining_balance = current_balance - total_needed
        text += f"💳 Остаток после отправки: {remaining_balance} {currency}\n\n"
        text += "⚠️ Проверьте все данные перед подтверждением!\n"
        text += "💡 Транзакция необратима после отправки."

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_send")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="wallet_send")]
        ])

        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logger.error("Process amount input failed", error=str(e))
        await message.answer("❌ Произошла ошибка")


@router.callback_query(F.data == "confirm_send")
async def confirm_send_transaction(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        currency = data.get("send_currency")
        network = data.get("send_network")
        amount = data.get("send_amount")
        recipient_address = data.get("recipient_address")
        wallet_id = data.get("wallet_id")
        total_needed = data.get("total_needed", amount)
        fee_display = data.get("fee_display", "")

        if not all([currency, network, amount, recipient_address, wallet_id]):
            await callback.answer("❌ Недостаточно данных для транзакции")
            return

        await callback.message.edit_text("⏳ Обрабатываю транзакцию...")

        async for db in get_async_db():
            user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
            if not user:
                await callback.answer("❌ Пользователь не найден")
                return

            try:
                display_name = currency
                if currency in ["USDT", "USDC"] and network != currency:
                    display_name = f"{currency} ({network})"

                text = f"✅ Транзакция отправлена!\n\n"
                text += f"💰 Сумма: {amount} {currency}\n"

                if fee_display:
                    text += f"💸 Комиссия: {fee_display}\n"
                    if total_needed > amount:
                        text += f"📊 Всего списано: {total_needed} {currency}\n"

                text += f"🌐 Сеть: {network}\n"
                text += f"📍 Адрес получателя: `{recipient_address}`\n\n"
                text += f"🔗 Транзакция будет обработана в ближайшее время.\n"
                text += f"📊 Проверить статус можно в разделе 'История'.\n\n"
                text += f"💡 Время обработки зависит от загруженности сети {network}."

                keyboard = get_back_keyboard("wallet_menu")
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
                await state.clear()

            except Exception as e:
                logger.error("Transaction failed", error=str(e))
                await callback.message.edit_text("❌ Ошибка при выполнении транзакции")

            break

    except Exception as e:
        logger.error("Confirm send transaction failed", error=str(e))
        await callback.answer("❌ Произошла ошибка")
