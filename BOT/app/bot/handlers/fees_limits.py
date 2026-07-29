from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import structlog

logger = structlog.get_logger(__name__)
router = Router()


class FeesLimitsStates(StatesGroup):
    selecting_currency = State()
    selecting_network = State()


FEES_LIMITS_DATA = {
    "USDT": {
        "TON": {
            "network_name": "The Open Network – TON",
            "withdrawal_fee": "3.5 USDT",
            "deposit_limit": "от 1 USDT",
            "withdrawal_limit": "от 1 USDT"
        },
        "TRC20": {
            "network_name": "Tron – TRC20",
            "withdrawal_fee": "Комиссия на вывод на адреса с USDT: 5.5 USDT\nКомиссия на вывод на адреса без USDT: 8.5 USDT",
            "deposit_limit": "от 1 USDT",
            "withdrawal_limit": "от 1 USDT"
        },
        "SPL": {
            "network_name": "Solana – SPL",
            "withdrawal_fee": "3 USDT",
            "deposit_limit": "от 1 USDT",
            "withdrawal_limit": "от 1 USDT"
        },
        "ERC20": {
            "network_name": "Ethereum – ERC20",
            "withdrawal_fee": "5 USDT",
            "deposit_limit": "от 1 USDT",
            "withdrawal_limit": "от 0.01 USDT"
        },
        "BEP20": {
            "network_name": "BNB Smart Chain – BEP20",
            "withdrawal_fee": "3 USDT",
            "deposit_limit": "от 1 USDT",
            "withdrawal_limit": "от 1 USDT"
        }
    },
    "USDC": {
        "ERC20": {
            "network_name": "Ethereum – ERC20",
            "withdrawal_fee": "5 USDC",
            "deposit_limit": "от 1 USDC",
            "withdrawal_limit": "от 0.01 USDC"
        },
        "SPL": {
            "network_name": "Solana – SPL",
            "withdrawal_fee": "3 USDC",
            "deposit_limit": "от 1 USDC",
            "withdrawal_limit": "от 1 USDC"
        },
        "BEP20": {
            "network_name": "BNB Smart Chain – BEP20",
            "withdrawal_fee": "3 USDC",
            "deposit_limit": "от 1 USDC",
            "withdrawal_limit": "от 1 USDC"
        }
    },
    "TON": {
        "TON": {
            "network_name": "The Open Network – TON",
            "withdrawal_fee": "0.1 TON",
            "deposit_limit": "безлимит",
            "withdrawal_limit": "от 0.0005 TON"
        }
    },
    "SOL": {
        "SPL": {
            "network_name": "Solana – SPL",
            "withdrawal_fee": "0.024 SOL",
            "deposit_limit": "безлимит",
            "withdrawal_limit": "от 0.005 SOL"
        }
    },
    "TRX": {
        "TRC20": {
            "network_name": "TRON – TRC20",
            "withdrawal_fee": "15 TRX",
            "deposit_limit": "от 10 TRX",
            "withdrawal_limit": "от 20 TRX"
        }
    },
    "BTC": {
        "BTC": {
            "network_name": "Bitcoin – BTC",
            "withdrawal_fee": "0.0003 BTC",
            "deposit_limit": "от 0.00002 BTC",
            "withdrawal_limit": "от 0.001 BTC до 25 BTC"
        }
    },
    "ETH": {
        "ERC20": {
            "network_name": "Ethereum – ERC20",
            "withdrawal_fee": "0.001 ETH",
            "deposit_limit": "безлимит",
            "withdrawal_limit": "от 0.001 ETH"
        }
    },
    "DOGE": {
        "DOGE": {
            "network_name": "DOGE – DOGE",
            "withdrawal_fee": "10 DOGE",
            "deposit_limit": "безлимит",
            "withdrawal_limit": "от 1 DOGE до 1,000,000 DOGE"
        }
    },
    "LTC": {
        "LTC": {
            "network_name": "Litecoin – LTC",
            "withdrawal_fee": "0.0125 LTC",
            "deposit_limit": "от 0.0001 LTC",
            "withdrawal_limit": "от 0.01 LTC до 3,000 LTC"
        }
    },
    "BNB": {
        "BEP20": {
            "network_name": "BNB Smart Chain – BEP20",
            "withdrawal_fee": "0.006 BNB",
            "deposit_limit": "безлимит",
            "withdrawal_limit": "от 0.001 BNB"
        }
    }
}


def get_currencies_keyboard() -> InlineKeyboardMarkup:
    buttons = []

    currencies = list(FEES_LIMITS_DATA.keys())

    for i in range(0, len(currencies), 2):
        row = []
        for j in range(2):
            if i + j < len(currencies):
                currency = currencies[i + j]
                if currency in ["USDT", "USDC"]:
                    networks_count = len(FEES_LIMITS_DATA[currency])
                    text = f"{currency} ({networks_count} сетей)"
                else:
                    text = currency

                row.append(InlineKeyboardButton(
                    text=text,
                    callback_data=f"fees_currency_{currency}"
                ))
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="◀️ Назад в Кошелек", callback_data="wallet_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_networks_keyboard(currency: str) -> InlineKeyboardMarkup:
    buttons = []

    if currency in FEES_LIMITS_DATA:
        networks = FEES_LIMITS_DATA[currency]

        for network_code, network_data in networks.items():
            network_name = network_data["network_name"]
            buttons.append([InlineKeyboardButton(
                text=network_name,
                callback_data=f"fees_network_{currency}_{network_code}"
            )])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="fees_limits")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard(callback_data: str = "fees_limits") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)]
    ])


@router.callback_query(F.data == "fees_limits")
async def show_fees_limits_menu(callback: CallbackQuery, state: FSMContext):
    try:
        text = "💰 Комиссии и лимиты\n\nВыберите криптовалюту для просмотра комиссий и лимитов:"

        keyboard = get_currencies_keyboard()

        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        await state.clear()

    except Exception as e:
        logger.error(
            "Fees limits menu failed",
            user_id=callback.from_user.id,
            error=str(e),
            exc_info=True
        )
        await callback.answer("❌ Произошла ошибка")


@router.callback_query(F.data.startswith("fees_currency_"))
async def show_currency_networks(callback: CallbackQuery, state: FSMContext):
    try:
        currency = callback.data.split("_", 2)[2]

        if currency not in FEES_LIMITS_DATA:
            await callback.answer("❌ Валюта не найдена")
            return

        networks = FEES_LIMITS_DATA[currency]

        if len(networks) == 1:
            network_code = list(networks.keys())[0]
            await show_fees_limits_info(callback, currency, network_code)
            return

        text = f"💰 Комиссии и лимиты для {currency}\n\nВыберите сеть:"
        keyboard = get_networks_keyboard(currency)

        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error(
            "Show currency networks failed",
            user_id=callback.from_user.id,
            currency=callback.data,
            error=str(e),
            exc_info=True
        )
        await callback.answer("❌ Произошла ошибка")


@router.callback_query(F.data.startswith("fees_network_"))
async def handle_network_selection(callback: CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split("_", 3)
        if len(parts) < 4:
            await callback.answer("❌ Неверный формат данных")
            return

        currency = parts[2]
        network_code = parts[3]

        await show_fees_limits_info(callback, currency, network_code)

    except Exception as e:
        logger.error(
            "Handle network selection failed",
            user_id=callback.from_user.id,
            callback_data=callback.data,
            error=str(e),
            exc_info=True
        )
        await callback.answer("❌ Произошла ошибка")


async def show_fees_limits_info(callback: CallbackQuery, currency: str, network_code: str):
    try:
        if currency not in FEES_LIMITS_DATA or network_code not in FEES_LIMITS_DATA[currency]:
            await callback.answer("❌ Данные не найдены")
            return

        data = FEES_LIMITS_DATA[currency][network_code]

        text = f"💰 Просмотр комиссий и лимитов для монеты {currency} в сети {data['network_name']}.\n\n"

        if "withdrawal_fee" in data:
            if "\n" in data["withdrawal_fee"]:
                text += f"{data['withdrawal_fee']}\n\n"
            else:
                text += f"Комиссия на вывод: {data['withdrawal_fee']}\n\n"

        text += "Лимиты:\n"
        if "deposit_limit" in data:
            text += f"Пополнение: {data['deposit_limit']}\n"
        if "withdrawal_limit" in data:
            text += f"Вывод: {data['withdrawal_limit']}"

        if len(FEES_LIMITS_DATA[currency]) > 1:
            back_callback = f"fees_currency_{currency}"
        else:
            back_callback = "fees_limits"

        keyboard = get_back_keyboard(back_callback)

        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error(
            "Show fees limits info failed",
            user_id=callback.from_user.id,
            currency=currency,
            network_code=network_code,
            error=str(e),
            exc_info=True
        )
        await callback.answer("❌ Произошла ошибка")
