from typing import Dict

def _(key: str, lang: str = "ru") -> str:
    if lang not in TEXTS:
        lang = "ru"

    lang_texts = TEXTS[lang]
    return lang_texts.get(key, f"Missing text: {key}")

TEXTS: Dict[str, Dict[str, str]] = {
    "ru": {
        "welcome": """
🦋 <a href="https://t.me/CryptoBotRU/14">Мультивалютный криптокошелёк</a>. Покупайте, продавайте, храните, <a href="https://t.me/CryptoBotRU/228">отправляйте</a> и платите криптовалютой, когда хотите.

Подписывайтесь на <a href="https://t.me/CryptoBotRU">наш канал</a> и вступайте в <a href="https://t.me/CryptoBotRussian">наш чат</a>.
        """,

        "main_menu": """
🦋 <a href="https://t.me/CryptoBotRU/14">Мультивалютный криптокошелёк</a>. Покупайте, продавайте, храните, <a href="https://t.me/CryptoBotRU/228">отправляйте</a> и платите криптовалютой, когда хотите.

Подписывайтесь на <a href="https://t.me/CryptoBotRU">наш канал</a> и вступайте в <a href="https://t.me/CryptoBotRussian">наш чат</a>.
        """,
        "help": """
ℹ️ <b>Помощь</b>

<b>Основные команды:</b>
/start - Запустить бота
/wallet - Кошелек
/help - Помощь

<b>Поддерживаемые валюты:</b>""",

        "check_menu": """
Отправляйте криптовалюту любому пользователю Telegram с помощью чеков. <a href='https://youtu.be/hOxI23ZFtVI'>Смотреть видеоинструкцию ›</a>
        """,

        "about": """
ℹ️ <b>О боте</b>

<b>CryptoBot Clone v1.0</b>

Полнофункциональный криптовалютный бот для работы с цифровыми активами в Telegram.

<b>Возможности:</b>
• Мультивалютный кошелек
• Чеки и инвойсы
• P2P торговля
• Обмен валют
• Подписки для каналов
• API для разработчиков

<b>Безопасность:</b>
• Шифрование приватных ключей
• Двухфакторная аутентификация
• Мониторинг транзакций

<b>Поддержка:</b>
@CryptoBotCloneSupport
        """,

        "back": "Назад",
        "cancel": "Отмена",
        "confirm": "Подтвердить",
        "continue": "Продолжить",
        "done": "Готово",
        "skip": "Пропустить",

        "wallet": "Кошелёк",
        "checks": "Чеки",
        "invoices": "Счета",
        "market": "Биржа",
        "p2p_market": "P2P",
        "exchange": "Обмен",
        "pay": "Crypto Pay",
        "giveaways": "Розыгрыши",
        "subscriptions": "Подписки",
        "settings": "Настройки",

        "balance": "Баланс",
        "history": "История",
        "send": "Отправить",
        "receive": "Получить",

        "create_check": "Создать чек",
        "my_checks": "Мои чеки",
        "activate_check": "Активировать чек",

        "create_invoice": "Создать инвойс",
        "my_invoices": "Мои инвойсы",
        "pay_invoice": "Оплатить инвойс",

        "buy": "Купить",
        "sell": "Продать",
        "my_orders": "Мои ордера",
        "my_trades": "Мои сделки",
        "p2p_menu": """
💠 Здесь вы можете <a href="https://help.send.tg/ru/articles/9819562-%D0%BA%D0%B0%D0%BA-%D0%BA%D1%83%D0%BF%D0%B8%D1%82%D1%8C-%D0%BC%D0%BE%D0%BD%D0%B5%D1%82%D1%8B">купить</a> или <a href="https://help.send.tg/ru/articles/9819582-%D0%BA%D0%B0%D0%BA-%D0%BF%D1%80%D0%BE%D0%B4%D0%B0%D1%82%D1%8C-%D0%BC%D0%BE%D0%BD%D0%B5%D1%82%D1%8B">продать</a> криптовалюту переводом на карту или электронный кошелёк. <a href="https://youtu.be/PuD59ai_VNg">Смотреть видеоинструкцию ›</a>
""",
        "p2p_menu": """
💠 Здесь вы можете <a href="https://help.send.tg/ru/articles/9819562-%D0%BA%D0%B0%D0%BA-%D0%BA%D1%83%D0%BF%D0%B8%D1%82%D1%8C-%D0%BC%D0%BE%D0%BD%D0%B5%D1%82%D1%8B">купить</a> или <a href="https://help.send.tg/ru/articles/9819582-%D0%BA%D0%B0%D0%BA-%D0%BF%D1%80%D0%BE%D0%B4%D0%B0%D1%82%D1%8C-%D0%BC%D0%BE%D0%BD%D0%B5%D1%82%D1%8B">продать</a> криптовалюту переводом на карту или электронный кошелёк. <a href="https://youtu.be/PuD59ai_VNg">Смотреть видеоинструкцию ›</a>
""",
        "p2p_menu": """
💠 Здесь вы можете <a href="https://help.send.tg/ru/articles/9819562-%D0%BA%D0%B0%D0%BA-%D0%BA%D1%83%D0%BF%D0%B8%D1%82%D1%8C-%D0%BC%D0%BE%D0%BD%D0%B5%D1%82%D1%8B">купить</a> или <a href="https://help.send.tg/ru/articles/9819582-%D0%BA%D0%B0%D0%BA-%D0%BF%D1%80%D0%BE%D0%B4%D0%B0%D1%82%D1%8C-%D0%BC%D0%BE%D0%BD%D0%B5%D1%82%D1%8B">продать</a> криптовалюту переводом на карту или электронный кошелёк. <a href="https://youtu.be/PuD59ai_VNg">Смотреть видеоинструкцию ›</a>
""",

        "quick_exchange": "Быстрый обмен",
        "limit_order": "Лимитный ордер",
        "exchange_history": "История обменов",

        "connect_channel": "Подключить канал",
        "my_subscriptions": "Мои подписки",
        "statistics": "Статистика",

        "language": "Язык",
        "currency": "Валюта",
        "notifications": "Уведомления",
        "api": "API",

        "unknown_command": "❌ Неизвестная команда. Используйте меню ниже.",
        "unknown_parameter": "❌ Неизвестный параметр. Возвращаемся в главное меню.",
        "use_menu": "Используйте меню для навигации:",

        "loading": "⏳ Загрузка...",
        "error": "❌ Произошла ошибка",
        "success": "✅ Успешно",
        "not_implemented": "🚧 Функция в разработке",
    },

    "en": {
        "welcome": """
🚀 <b>Welcome to CryptoBot Clone!</b>

Hello, {name}! 👋

I'll help you work with cryptocurrencies right in Telegram:

💰 <b>Wallet</b> - store and send cryptocurrencies
🎫 <b>Checks</b> - create checks to transfer funds
🧾 <b>Invoices</b> - create payment invoices
🏪 <b>P2P Market</b> - buy and sell cryptocurrencies
🔄 <b>Exchange</b> - exchange currencies at best rates
📺 <b>Subscriptions</b> - monetize your channels

Choose the section you need from the menu below! 👇
        """,

        "main_menu": """
🏠 <b>Main Menu</b>

Choose the section you need:
        """,

        "help": """
ℹ️ <b>Help</b>

<b>Main commands:</b>
/start - Start the bot
/wallet - Wallet
/help - Help

<b>Supported currencies:</b>
• Bitcoin (BTC)
• Ethereum (ETH)
• Tether (USDT)
• Litecoin (LTC)
• Binance Coin (BNB)
• Tron (TRX)
• Toncoin (TON)
• Litecoin (LTC)
• Binance Coin (BNB)
• USD Coin (USDC)

<b>Support:</b>
@CryptoBotCloneSupport
        """,

        "about": """
ℹ️ <b>About the bot</b>

<b>CryptoBot Clone v1.0</b>

Full-featured cryptocurrency bot for working with digital assets in Telegram.

<b>Features:</b>
• Multi-currency wallet
• Checks and invoices
• P2P trading
• Currency exchange
• Channel subscriptions
• Developer API

<b>Security:</b>
• Private key encryption
• Two-factor authentication
• Transaction monitoring

<b>Support:</b>
@CryptoBotCloneSupport
        """,

        "back": "Back",
        "cancel": "Cancel",
        "confirm": "Confirm",
        "continue": "Continue",
        "done": "Done",
        "skip": "Skip",

        "wallet": "Wallet",
        "checks": "Checks",
        "invoices": "Invoices",
        "p2p_market": "P2P Market",
        "exchange": "Exchange",
        "subscriptions": "Subscriptions",
        "settings": "Settings",

        "balance": "Balance",
        "history": "History",
        "send": "Send",
        "receive": "Receive",

        "create_check": "Create Check",
        "my_checks": "My Checks",
        "activate_check": "Activate Check",

        "create_invoice": "Create Invoice",
        "my_invoices": "My Invoices",
        "pay_invoice": "Pay Invoice",

        "buy": "Buy",
        "sell": "Sell",
        "my_orders": "My Orders",
        "my_trades": "My Trades",

        "quick_exchange": "Quick Exchange",
        "limit_order": "Limit Order",
        "exchange_history": "Exchange History",

        "connect_channel": "Connect Channel",
        "my_subscriptions": "My Subscriptions",
        "statistics": "Statistics",

        "language": "Language",
        "currency": "Currency",
        "notifications": "Notifications",
        "api": "API",

        "unknown_command": "❌ Unknown command. Use the menu below.",
        "unknown_parameter": "❌ Unknown parameter. Returning to main menu.",
        "use_menu": "Use the menu for navigation:",

        "loading": "⏳ Loading...",
        "error": "❌ An error occurred",
        "success": "✅ Success",
        "not_implemented": "🚧 Feature under development",
    }
}


def get_text(key: str, language_code: str = "ru") -> str:
    if language_code not in TEXTS:
        language_code = "ru"

    return TEXTS[language_code].get(key, key)


def format_currency(amount: float, currency: str) -> str:
    if currency in ["BTC", "ETH", "LTC"]:
        return f"{amount:.8f} {currency}"
    elif currency in ["USDT", "USDC"]:
        return f"{amount:.2f} {currency}"
    else:
        return f"{amount:.4f} {currency}"


def format_address(address: str, length: int = 8) -> str:
    if len(address) <= length * 2 + 3:
        return address

    return f"{address[:length]}...{address[-length:]}"


def format_transaction_hash(tx_hash: str, length: int = 6) -> str:
    if len(tx_hash) <= length * 2 + 3:
        return tx_hash

    return f"{tx_hash[:length]}...{tx_hash[-length:]}"


def get_currency_emoji(currency: str) -> str:
    emojis = {
        "BTC": "₿",
        "ETH": "Ξ",
        "USDT": "₮",
        "LTC": "Ł",
        "BNB": "🔸",
        "TRX": "🔺",
        "TON": "💎",
        "USD": "💵",
        "EUR": "💶",
        "RUB": "₽",
    }

    return emojis.get(currency, "💰")


def get_status_emoji(status: str) -> str:
    emojis = {
        "active": "🟢",
        "pending": "🟡",
        "completed": "✅",
        "cancelled": "❌",
        "expired": "⏰",
        "failed": "🔴",
        "processing": "⏳",
    }

    return emojis.get(status, "⚪")
