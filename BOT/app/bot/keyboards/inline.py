from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Optional
import os

from app.bot.utils.texts import get_text


def get_main_menu_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    webapp_url = os.getenv("WEBAPP_URL", os.getenv("NGROK_URL", "http://127.0.0.1:5000"))
    builder.row(
        InlineKeyboardButton(
            text="📱 Открыть в приложении",
            web_app=WebAppInfo(url=webapp_url)
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="👛 " + get_text("wallet", language_code),
            callback_data="wallet_menu"
        ),
        InlineKeyboardButton(
            text="🔄 " + get_text("exchange", language_code),
            callback_data="exchange_menu"
        ),
    )

    builder.row(
        InlineKeyboardButton(
            text="💠 " + get_text("p2p_market", language_code),
            callback_data="p2p_menu"
        ),
        InlineKeyboardButton(
            text="🐬 " + get_text("market", language_code),
            callback_data="market"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🦋 " + get_text("checks", language_code),
            callback_data="check_menu"
        ),
        InlineKeyboardButton(
            text="📥 " + get_text("invoices", language_code),
            callback_data="invoice_menu"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🏝 " + get_text("pay", language_code),
            callback_data="pay"
        ),
        InlineKeyboardButton(
            text="🎁 " + get_text("giveaways", language_code),
            callback_data="giveaway"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🍑 " + get_text("subscriptions", language_code),
            callback_data="subscription_menu"
        ),
        InlineKeyboardButton(
            text="⚙️ " + get_text("settings", language_code),
            callback_data="settings_menu"
        )
    )

    return builder.as_markup()


def get_wallet_menu_keyboard(wallets=None, language_code: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📊 " + get_text("balance", language_code),
            callback_data="wallet_balance"
        ),
        InlineKeyboardButton(
            text="📋 " + get_text("history", language_code),
            callback_data="wallet_history"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📤 " + get_text("send", language_code),
            callback_data="wallet_send"
        ),
        InlineKeyboardButton(
            text="📥 " + get_text("receive", language_code),
            callback_data="wallet_receive"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🔄 " + get_text("exchange", language_code),
            callback_data="wallet_exchange"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ " + get_text("back", language_code),
            callback_data="main_menu"
        )
    )

    return builder.as_markup()


def get_check_menu_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="➕ " + get_text("create_check", language_code),
            callback_data="check_create"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📋 " + get_text("my_checks", language_code),
            callback_data="check_list"
        ),
        InlineKeyboardButton(
            text="🔗 " + get_text("activate_check", language_code),
            callback_data="check_activate"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ " + get_text("back", language_code),
            callback_data="main_menu"
        )
    )

    return builder.as_markup()


def get_invoice_menu_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="➕ " + get_text("create_invoice", language_code),
            callback_data="invoice_create"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📋 " + get_text("my_invoices", language_code),
            callback_data="invoice_list"
        ),
        InlineKeyboardButton(
            text="💳 " + get_text("pay_invoice", language_code),
            callback_data="invoice_pay"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ " + get_text("back", language_code),
            callback_data="main_menu"
        )
    )

    return builder.as_markup()


def get_p2p_menu_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="💰 " + get_text("buy", language_code),
            callback_data="p2p_buy"
        ),
        InlineKeyboardButton(
            text="💸 " + get_text("sell", language_code),
            callback_data="p2p_sell"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📊 " + get_text("my_orders", language_code),
            callback_data="p2p_orders"
        ),
        InlineKeyboardButton(
            text="📈 " + get_text("my_trades", language_code),
            callback_data="p2p_trades"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ " + get_text("back", language_code),
            callback_data="main_menu"
        )
    )

    return builder.as_markup()


def get_exchange_menu_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="⚡ " + get_text("quick_exchange", language_code),
            callback_data="exchange_quick"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📊 " + get_text("limit_order", language_code),
            callback_data="exchange_limit"
        ),
        InlineKeyboardButton(
            text="📋 " + get_text("exchange_history", language_code),
            callback_data="exchange_history"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ " + get_text("back", language_code),
            callback_data="main_menu"
        )
    )

    return builder.as_markup()


def get_subscription_menu_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="➕ " + get_text("connect_channel", language_code),
            callback_data="subscription_connect"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="💳 " + get_text("my_subscriptions", language_code),
            callback_data="subscription_list"
        ),
        InlineKeyboardButton(
            text="📊 " + get_text("statistics", language_code),
            callback_data="subscription_stats"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ " + get_text("back", language_code),
            callback_data="main_menu"
        )
    )

    return builder.as_markup()


def get_settings_menu_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    from app.bot.keyboards.settings import get_settings_main_keyboard

    return get_settings_main_keyboard(
        user_timezone="UTC",
        user_currency="USD",
        language_code=language_code
    )


def get_currency_keyboard(currencies: List[str], language_code: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for i in range(0, len(currencies), 3):
        row_currencies = currencies[i:i+3]
        buttons = []
        for currency in row_currencies:
            buttons.append(
                InlineKeyboardButton(
                    text=currency,
                    callback_data=f"currency_{currency}"
                )
            )
        builder.row(*buttons)

    builder.row(
        InlineKeyboardButton(
            text="◀️ " + get_text("back", language_code),
            callback_data="back"
        )
    )

    return builder.as_markup()


def get_back_keyboard(callback_data: str, language_code: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="◀️ " + get_text("back", language_code),
            callback_data=callback_data
        )
    )

    return builder.as_markup()


def get_confirm_keyboard(confirm_data: str, cancel_data: str, language_code: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ " + get_text("confirm", language_code),
            callback_data=confirm_data
        ),
        InlineKeyboardButton(
            text="❌ " + get_text("cancel", language_code),
            callback_data=cancel_data
        )
    )

    return builder.as_markup()


def get_pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str,
    language_code: str = "ru"
) -> InlineKeyboardMarkup:

    builder = InlineKeyboardBuilder()

    buttons = []

    if current_page > 1:
        buttons.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=f"{callback_prefix}_page_{current_page - 1}"
            )
        )

    buttons.append(
        InlineKeyboardButton(
            text=f"{current_page}/{total_pages}",
            callback_data="current_page"
        )
    )

    if current_page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"{callback_prefix}_page_{current_page + 1}"
            )
        )

    if buttons:
        builder.row(*buttons)

    return builder.as_markup()


def get_currency_selection_keyboard(
    callback_prefix: str,
    currencies: List[str] = None,
    language_code: str = "ru"
) -> InlineKeyboardMarkup:

    builder = InlineKeyboardBuilder()

    if currencies is None:
        currencies = ["BTC", "ETH", "USDT", "LTC", "BNB", "TRX", "TON"]

    for i in range(0, len(currencies), 3):
        row_currencies = currencies[i:i+3]
        buttons = []
        for currency in row_currencies:
            buttons.append(
                InlineKeyboardButton(
                    text=currency,
                    callback_data=f"{callback_prefix}_{currency}"
                )
            )
        builder.row(*buttons)

    builder.row(
        InlineKeyboardButton(
            text="◀️ " + get_text("back", language_code),
            callback_data="wallet_menu"
        )
    )

    return builder.as_markup()


def get_wallet_actions_keyboard(wallet_id: str, language_code: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📤 " + get_text("send", language_code),
            callback_data=f"wallet_send_{wallet_id}"
        ),
        InlineKeyboardButton(
            text="📥 " + get_text("receive", language_code),
            callback_data=f"wallet_receive_{wallet_id}"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📋 " + get_text("history", language_code),
            callback_data=f"wallet_history_{wallet_id}"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ " + get_text("back", language_code),
            callback_data="wallet_menu"
        )
    )

    return builder.as_markup()


def get_transaction_history_keyboard(
    has_more: bool = False,
    page: int = 1,
    language_code: str = "ru"
) -> InlineKeyboardMarkup:

    builder = InlineKeyboardBuilder()

    if has_more:
        if page > 1:
            builder.row(
                InlineKeyboardButton(
                    text="◀️ " + get_text("previous", language_code),
                    callback_data=f"history_page_{page - 1}"
                ),
                InlineKeyboardButton(
                    text="▶️ " + get_text("next", language_code),
                    callback_data=f"history_page_{page + 1}"
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text="▶️ " + get_text("next", language_code),
                    callback_data=f"history_page_{page + 1}"
                )
            )
    elif page > 1:
        builder.row(
            InlineKeyboardButton(
                text="◀️ " + get_text("previous", language_code),
                callback_data=f"history_page_{page - 1}"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="◀️ " + get_text("back", language_code),
            callback_data="wallet_menu"
        )
    )

    return builder.as_markup()


def get_check_type_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🎫 " + get_text("one_time_check", language_code),
            callback_data="check_type_one_time"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🔄 " + get_text("multi_use_check", language_code),
            callback_data="check_type_multi_use"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="👤 " + get_text("personal_check", language_code),
            callback_data="check_type_personal"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ " + get_text("back", language_code),
            callback_data="check_menu"
        )
    )

    return builder.as_markup()


def get_check_actions_keyboard(
    check_id: str,
    language_code: str = "ru",
    show_cancel: bool = True
) -> InlineKeyboardMarkup:

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📋 " + get_text("details", language_code),
            callback_data=f"check_details_{check_id}"
        )
    )

    if show_cancel:
        builder.row(
            InlineKeyboardButton(
                text="❌ " + get_text("cancel_check", language_code),
                callback_data=f"check_cancel_{check_id}"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="◀️ " + get_text("back", language_code),
            callback_data="check_menu"
        )
    )

    return builder.as_markup()


def get_check_list_keyboard(
    checks: List = None,
    language_code: str = "ru",
    page: int = 1,
    has_more: bool = False
) -> InlineKeyboardMarkup:

    builder = InlineKeyboardBuilder()

    if checks:
        for check in checks[:5]:
            status_emoji = {
                "active": "🟢",
                "activated": "✅",
                "expired": "⏰",
                "cancelled": "❌"
            }.get(check.status, "❓")

            check_text = f"{status_emoji} {check.check_id} - {check.amount} {check.currency}"

            builder.row(
                InlineKeyboardButton(
                    text=check_text,
                    callback_data=f"check_details_{check.check_id}"
                )
            )

    if has_more:
        if page > 1:
            builder.row(
                InlineKeyboardButton(
                    text="◀️ " + get_text("previous", language_code),
                    callback_data=f"check_list_page_{page - 1}"
                ),
                InlineKeyboardButton(
                    text="▶️ " + get_text("next", language_code),
                    callback_data=f"check_list_page_{page + 1}"
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text="▶️ " + get_text("next", language_code),
                    callback_data=f"check_list_page_{page + 1}"
                )
            )
    elif page > 1:
        builder.row(
            InlineKeyboardButton(
                text="◀️ " + get_text("previous", language_code),
                callback_data=f"check_list_page_{page - 1}"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="◀️ " + get_text("back", language_code),
            callback_data="check_menu"
        )
    )

    return builder.as_markup()


def create_inline_keyboard(buttons: List[List[dict]], language_code: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for row in buttons:
        row_buttons = []
        for button in row:
            row_buttons.append(
                InlineKeyboardButton(
                    text=button.get("text", ""),
                    callback_data=button.get("callback_data", ""),
                    url=button.get("url")
                )
            )
        builder.row(*row_buttons)

    return builder.as_markup()
