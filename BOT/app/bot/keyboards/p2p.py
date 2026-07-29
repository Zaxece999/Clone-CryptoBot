from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_p2p_menu_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📈 Купить", callback_data="market-trade-buy"),
        InlineKeyboardButton(text="📉 Продать", callback_data="market-trade-sell")
    )

    builder.row(
        InlineKeyboardButton(text="🗳 Мои сделки", callback_data="market-manage-orders")
    )

    builder.row(
        InlineKeyboardButton(text="💸 Создать объявления", callback_data="market-create-offer")
    )

    builder.row(
        InlineKeyboardButton(text="⚙️ Оплата и валюта", callback_data="market-settings")
    )

    builder.row(
        InlineKeyboardButton(text="👤 Мой профиль", callback_data="open-profile")
    )

    builder.row(
        InlineKeyboardButton(text="Назад", callback_data="main_menu")
    )

    return builder.as_markup()

def get_p2p_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📈 Купить", callback_data="market-trade-buy"),
        InlineKeyboardButton(text="📉 Продать", callback_data="market-trade-sell")
    )
    builder.row(
        InlineKeyboardButton(text="🗳 Мои сделки", callback_data="market-manage-orders")
    )
    builder.row(
        InlineKeyboardButton(text="💸 Создать объявление", callback_data="market-create-offer")
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="market-settings")
    )
    return builder.as_markup()

def get_order_type_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💰 Купить криптовалюту", callback_data="order_type_buy"),
        InlineKeyboardButton(text="💸 Продать криптовалюту", callback_data="order_type_sell")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="p2p_main")
    )
    return builder.as_markup()


def get_currency_keyboard(currency_type: str):
    builder = InlineKeyboardBuilder()

    if currency_type == "crypto":
        currencies = [
            ("BTC", "crypto_BTC"),
            ("ETH", "crypto_ETH"),
            ("USDT", "crypto_USDT"),
            ("BNB", "crypto_BNB"),
            ("TRX", "crypto_TRX"),
            ("TON", "crypto_TON")
        ]
    else:
        currencies = [
            ("RUB", "fiat_RUB"),
            ("USD", "fiat_USD"),
            ("EUR", "fiat_EUR"),
            ("KZT", "fiat_KZT"),
            ("UAH", "fiat_UAH"),
            ("◀️ Назад", "p2p_main")
        ]

    for text, callback_data in currencies:
        builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))

    builder.adjust(3)
    return builder.as_markup()


def get_payment_methods_keyboard():
    builder = InlineKeyboardBuilder()
    methods = [
        ("💳 Банковская карта", "payment_card"),
        ("🏦 Сбербанк", "payment_sberbank"),
        ("🏦 Тинькофф", "payment_tinkoff"),
        ("📱 СБП", "payment_sbp"),
        ("💰 Наличные", "payment_cash"),
        ("🔄 Другое", "payment_other")
    ]

    for text, callback_data in methods:
        builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))

    builder.adjust(2)
    return builder.as_markup()


def get_order_actions_keyboard(order_id: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"order_edit_{order_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"order_delete_{order_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data=f"order_stats_{order_id}"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="p2p_my_orders")
    )
    return builder.as_markup()


def get_trade_actions_keyboard(trade, user_id: int):
    builder = InlineKeyboardBuilder()

    if trade.buyer_id == user_id:
        if trade.status == "waiting_payment":
            builder.add(InlineKeyboardButton(text="💳 Отметить оплату", callback_data=f"trade_action_confirm_payment:{trade.trade_id}"))
        elif trade.status == "paid":
            builder.add(InlineKeyboardButton(text="✅ Подтвердить получение", callback_data=f"trade_action_confirm_receipt:{trade.trade_id}"))
    elif trade.seller_id == user_id:
        if trade.status == "waiting_payment":
            builder.add(InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"trade_action_confirm_payment:{trade.trade_id}"))
        elif trade.status == "paid":
            builder.add(InlineKeyboardButton(text="🚀 Отправить криптовалюту", callback_data=f"trade_action_release_crypto:{trade.trade_id}"))

    builder.add(
        InlineKeyboardButton(text="💬 Чат", callback_data=f"trade_chat_{trade.trade_id}"),
        InlineKeyboardButton(text="⚠️ Спор", callback_data=f"trade_action_dispute:{trade.trade_id}")
    )

    if trade.status in ["waiting_payment", "paid"]:
        builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data=f"trade_action_cancel:{trade.trade_id}"))

    return builder.as_markup()


def get_back_keyboard(callback_data: str):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data))
    return builder.as_markup()
