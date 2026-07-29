from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

BACK_SYMBOL = "‹"

def get_accounts_menu_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать счёт", callback_data="create_invoice")],
        [InlineKeyboardButton(text="Создать из чата", callback_data="create_from_chat")],
        [InlineKeyboardButton(text="Неоплаченные счета", callback_data="unpaid_invoices")],
        [InlineKeyboardButton(text=f"{BACK_SYMBOL} Назад", callback_data="main_menu")]
    ])

def get_create_invoice_type_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Одноразовый", callback_data="invoice_type_single"),
            InlineKeyboardButton(text="Многоразовый", callback_data="invoice_type_multiple")
        ],
        [InlineKeyboardButton(text=f"{BACK_SYMBOL} Назад к счетам", callback_data="accounts_menu")]
    ])

def get_currency_keyboard(selected_currencies: list[str] = None) -> InlineKeyboardMarkup:
    if selected_currencies is None:
        selected_currencies = []

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

def get_invoice_actions_keyboard(invoice_code: str, language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Поделиться счётом", switch_inline_query=invoice_code)],
        [InlineKeyboardButton(text="Показать QR-код", callback_data=f"qr_{invoice_code}")],
        [InlineKeyboardButton(text="Разрешения", callback_data=f"permissions_{invoice_code}")],
        [InlineKeyboardButton(text="Скрытое сообщение: Выкл.", callback_data=f"toggle_hidden_{invoice_code}")],
        [InlineKeyboardButton(text="Удалить счёт", callback_data=f"delete_invoice_{invoice_code}")],
        [InlineKeyboardButton(text=f"{BACK_SYMBOL} Назад к списку счетов", callback_data="accounts_menu")]
    ])

def get_permissions_keyboard(invoice_code: str, language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Комментарии: Вкл.", callback_data=f"toggle_comments_{invoice_code}")],
        [InlineKeyboardButton(text="Анонимные платежи: Вкл.", callback_data=f"toggle_anonymous_{invoice_code}")],
        [InlineKeyboardButton(text=f"{BACK_SYMBOL} Назад к счёту", callback_data=f"invoice_{invoice_code}")]
    ])

def get_delete_confirmation_keyboard(invoice_code: str, language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data=f"confirm_delete_{invoice_code}"),
            InlineKeyboardButton(text="Нет", callback_data=f"invoice_{invoice_code}")
        ]
    ])
