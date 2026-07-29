from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional, List
from app.models.exchange import Exchange, ExchangeStatus


def get_exchange_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Создать обмен", callback_data="exchange_create")
        ],
        [
            InlineKeyboardButton(text="📊 История обменов", callback_data="exchange_history"),
            InlineKeyboardButton(text="📈 Курсы валют", callback_data="exchange_rates")
        ],
        [
            InlineKeyboardButton(text="📋 Мои лимиты", callback_data="exchange_limits"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="exchange_stats")
        ],
        [
            InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")
        ]
    ])
    return keyboard


def get_currency_selection_keyboard(
    currency_type: str = "all",
    exclude: Optional[str] = None
) -> InlineKeyboardMarkup:

    crypto_currencies = [
        ("BTC", "Bitcoin"),
        ("ETH", "Ethereum"),
        ("USDT", "Tether USD"),
        ("LTC", "Litecoin"),
        ("BNB", "Binance Coin"),
        ("TRX", "TRON"),
        ("TON", "The Open Network")
    ]

    fiat_currencies = [
        ("USD", "US Dollar"),
        ("EUR", "Euro"),
        ("RUB", "Russian Ruble"),
        ("CNY", "Chinese Yuan"),
        ("KRW", "Korean Won"),
        ("JPY", "Japanese Yen")
    ]

    buttons = []

    if currency_type in ["all", "crypto"]:
        for code, name in crypto_currencies:
            if exclude and code == exclude:
                continue

            buttons.append([
                InlineKeyboardButton(
                    text=f"₿ {code} - {name}",
                    callback_data=f"exchange_from_{code}" if currency_type == "crypto" else f"exchange_to_{code}"
                )
            ])

    if currency_type in ["all", "fiat"]:
        for code, name in fiat_currencies:
            if exclude and code == exclude:
                continue

            buttons.append([
                InlineKeyboardButton(
                    text=f"💵 {code} - {name}",
                    callback_data=f"exchange_from_{code}" if currency_type == "fiat" else f"exchange_to_{code}"
                )
            ])

    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="exchange_main")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_exchange_confirmation_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить обмен", callback_data="exchange_confirm")
        ],
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data="exchange_cancel")
        ]
    ])
    return keyboard


def get_exchange_actions_keyboard(exchange: Exchange) -> InlineKeyboardMarkup:
    buttons = []

    if exchange.status == ExchangeStatus.PENDING.value:
        buttons.append([
            InlineKeyboardButton(text="⚡ Обработать", callback_data=f"exchange_process_{exchange.exchange_id}"),
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"exchange_cancel_{exchange.exchange_id}")
        ])

    elif exchange.status == ExchangeStatus.PROCESSING.value:
        buttons.append([
            InlineKeyboardButton(text="🔄 Обновить статус", callback_data=f"exchange_refresh_{exchange.exchange_id}")
        ])

    elif exchange.status == ExchangeStatus.FAILED.value:
        buttons.append([
            InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="exchange_create")
        ])

    buttons.extend([
        [
            InlineKeyboardButton(text="📋 Детали", callback_data=f"exchange_details_{exchange.exchange_id}"),
            InlineKeyboardButton(text="📊 Транзакции", callback_data=f"exchange_transactions_{exchange.exchange_id}")
        ],
        [
            InlineKeyboardButton(text="◀️ К истории", callback_data="exchange_history"),
            InlineKeyboardButton(text="🔄 Обмен", callback_data="exchange_main")
        ]
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_exchange_history_keyboard(exchanges: List[Exchange]) -> InlineKeyboardMarkup:
    buttons = []

    for i, exchange in enumerate(exchanges[:5], 1):
        status_emoji = {
            "completed": "✅",
            "pending": "🟡",
            "processing": "🔵",
            "failed": "❌",
            "cancelled": "❌",
            "expired": "⏰"
        }.get(exchange.status, "❓")

        buttons.append([
            InlineKeyboardButton(
                text=f"{status_emoji} #{i} {exchange.from_currency}→{exchange.to_currency}",
                callback_data=f"exchange_view_{exchange.exchange_id}"
            )
        ])

    control_buttons = []
    if len(exchanges) > 5:
        control_buttons.append(
            InlineKeyboardButton(text="📄 Показать все", callback_data="exchange_history_all")
        )

    control_buttons.append(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="exchange_history")
    )

    if control_buttons:
        buttons.append(control_buttons)

    buttons.extend([
        [
            InlineKeyboardButton(text="➕ Новый обмен", callback_data="exchange_create")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="exchange_main")
        ]
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_exchange_rates_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить курсы", callback_data="exchange_rates_refresh")
        ],
        [
            InlineKeyboardButton(text="📊 BTC курсы", callback_data="exchange_rates_btc"),
            InlineKeyboardButton(text="📊 ETH курсы", callback_data="exchange_rates_eth")
        ],
        [
            InlineKeyboardButton(text="📊 USDT курсы", callback_data="exchange_rates_usdt"),
            InlineKeyboardButton(text="📊 Все курсы", callback_data="exchange_rates_all")
        ],
        [
            InlineKeyboardButton(text="💱 Создать обмен", callback_data="exchange_create")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="exchange_main")
        ]
    ])
    return keyboard


def get_exchange_limits_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Дневные лимиты", callback_data="exchange_limits_daily"),
            InlineKeyboardButton(text="📊 Месячные лимиты", callback_data="exchange_limits_monthly")
        ],
        [
            InlineKeyboardButton(text="📊 Годовые лимиты", callback_data="exchange_limits_yearly")
        ],
        [
            InlineKeyboardButton(text="⭐ Увеличить лимиты", callback_data="exchange_limits_upgrade")
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="exchange_limits")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="exchange_main")
        ]
    ])
    return keyboard


def get_exchange_stats_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 За день", callback_data="exchange_stats_daily"),
            InlineKeyboardButton(text="📊 За неделю", callback_data="exchange_stats_weekly")
        ],
        [
            InlineKeyboardButton(text="📊 За месяц", callback_data="exchange_stats_monthly"),
            InlineKeyboardButton(text="📊 За год", callback_data="exchange_stats_yearly")
        ],
        [
            InlineKeyboardButton(text="📈 Популярные пары", callback_data="exchange_stats_popular")
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="exchange_stats")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="exchange_main")
        ]
    ])
    return keyboard


def get_quick_exchange_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡ BTC → USDT", callback_data="quick_exchange_BTC_USDT"),
            InlineKeyboardButton(text="⚡ ETH → USDT", callback_data="quick_exchange_ETH_USDT")
        ],
        [
            InlineKeyboardButton(text="⚡ USDT → BTC", callback_data="quick_exchange_USDT_BTC"),
            InlineKeyboardButton(text="⚡ USDT → ETH", callback_data="quick_exchange_USDT_ETH")
        ],
        [
            InlineKeyboardButton(text="⚡ BTC → ETH", callback_data="quick_exchange_BTC_ETH"),
            InlineKeyboardButton(text="⚡ ETH → BTC", callback_data="quick_exchange_ETH_BTC")
        ],
        [
            InlineKeyboardButton(text="🔧 Настроить обмен", callback_data="exchange_create")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="exchange_main")
        ]
    ])
    return keyboard


def get_exchange_amount_keyboard(currency: str) -> InlineKeyboardMarkup:
    if currency == "BTC":
        amounts = ["0.001", "0.01", "0.1", "1"]
    elif currency == "ETH":
        amounts = ["0.01", "0.1", "1", "10"]
    elif currency in ["USDT", "USD"]:
        amounts = ["100", "500", "1000", "5000"]
    elif currency == "RUB":
        amounts = ["10000", "50000", "100000", "500000"]
    else:
        amounts = ["1", "10", "100", "1000"]

    buttons = []

    row = []
    for i, amount in enumerate(amounts):
        row.append(
            InlineKeyboardButton(
                text=f"{amount} {currency}",
                callback_data=f"exchange_amount_{amount}"
            )
        )

        if len(row) == 2 or i == len(amounts) - 1:
            buttons.append(row)
            row = []

    buttons.append([
        InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="exchange_amount_manual")
    ])

    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="exchange_main")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_back_keyboard(callback_data: str = "exchange_main") -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)
        ]
    ])
    return keyboard


def get_exchange_filter_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Завершенные", callback_data="exchange_filter_completed"),
            InlineKeyboardButton(text="🟡 Ожидающие", callback_data="exchange_filter_pending")
        ],
        [
            InlineKeyboardButton(text="❌ Неудачные", callback_data="exchange_filter_failed"),
            InlineKeyboardButton(text="🔵 В процессе", callback_data="exchange_filter_processing")
        ],
        [
            InlineKeyboardButton(text="📅 За сегодня", callback_data="exchange_filter_today"),
            InlineKeyboardButton(text="📅 За неделю", callback_data="exchange_filter_week")
        ],
        [
            InlineKeyboardButton(text="🔄 Сбросить фильтры", callback_data="exchange_filter_reset")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="exchange_history")
        ]
    ])
    return keyboard


def get_exchange_help_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❓ Как создать обмен", callback_data="exchange_help_create"),
            InlineKeyboardButton(text="❓ Курсы и комиссии", callback_data="exchange_help_rates")
        ],
        [
            InlineKeyboardButton(text="❓ Лимиты обмена", callback_data="exchange_help_limits"),
            InlineKeyboardButton(text="❓ Безопасность", callback_data="exchange_help_security")
        ],
        [
            InlineKeyboardButton(text="📞 Связаться с поддержкой", callback_data="contact_support")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="exchange_main")
        ]
    ])
    return keyboard
