from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from app.models.p2p import P2POrder, P2PTrade, P2POrderType, P2POrderStatus
from app.models.user import User
from app.models.wallet import Wallet
from app.models.check import Check
from app.models.invoice import Invoice


def format_currency(amount: Decimal, currency: str, show_symbol: bool = True) -> str:
    if currency in ["BTC", "ETH", "LTC"]:
        formatted = f"{amount:.8f}".rstrip('0').rstrip('.')
    elif currency in ["USDT", "USDC", "DAI"]:
        formatted = f"{amount:.6f}".rstrip('0').rstrip('.')
    elif currency in ["USD", "EUR", "RUB", "CNY", "KRW", "JPY"]:
        formatted = f"{amount:,.2f}"
    else:
        formatted = f"{amount:.6f}".rstrip('0').rstrip('.')

    if show_symbol:
        return f"{formatted} {currency}"
    return formatted


def format_percentage(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}%"


def format_datetime(dt: datetime, show_time: bool = True) -> str:
    now = datetime.utcnow()
    diff = now - dt

    if diff.days == 0:
        if diff.seconds < 60:
            return "только что"
        elif diff.seconds < 3600:
            minutes = diff.seconds // 60
            return f"{minutes} мин назад"
        elif diff.seconds < 86400:
            hours = diff.seconds // 3600
            return f"{hours} ч назад"
    elif diff.days == 1:
        return "вчера"
    elif diff.days < 7:
        return f"{diff.days} дн назад"
    else:
        if show_time:
            return dt.strftime("%d.%m.%Y %H:%M")
        return dt.strftime("%d.%m.%Y")


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} мин"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours} ч {minutes} мин"
        return f"{hours} ч"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        if hours > 0:
            return f"{days} дн {hours} ч"
        return f"{days} дн"


def format_user_info(user: User, show_details: bool = False) -> str:
    name = user.first_name
    if user.last_name:
        name += f" {user.last_name}"

    if user.username:
        name += f" (@{user.username})"

    if show_details:
        details = []
        if user.is_verified:
            details.append("✅ Верифицирован")
        if user.is_premium:
            details.append("⭐ Premium")

        if details:
            name += f" ({', '.join(details)})"

    return name


def format_wallet_balance(wallet: Wallet) -> str:
    available = format_currency(wallet.balance, wallet.currency)

    if wallet.frozen_balance > 0:
        frozen = format_currency(wallet.frozen_balance, wallet.currency)
        return f"{available} (заморожено: {frozen})"

    return available


def format_p2p_order(order: P2POrder, short: bool = False, detailed: bool = False) -> str:
    if short:
        action = "Покупка" if order.type == P2POrderType.BUY else "Продажа"
        price = format_currency(Decimal(order.price_per_unit), order.fiat_currency)
        amount = format_currency(Decimal(order.crypto_amount), order.crypto_currency)

        return f"{action} {amount} за {price}"

    elif detailed:
        action = "Покупка" if order.type == P2POrderType.BUY else "Продажа"
        crypto_amount = format_currency(Decimal(order.crypto_amount), order.crypto_currency)
        price_per_unit = format_currency(Decimal(order.price_per_unit), order.fiat_currency)
        total_amount = format_currency(Decimal(order.total_fiat_amount), order.fiat_currency)

        text_parts = [
            f"🏷️ <b>{action} {order.crypto_currency}</b>",
            f"💰 Количество: {crypto_amount}",
            f"💵 Цена: {price_per_unit} за 1 {order.crypto_currency}",
            f"💸 Общая сумма: {total_amount}",
        ]

        if order.min_amount:
            min_amt = format_currency(Decimal(order.min_amount), order.fiat_currency)
            text_parts.append(f"📉 Минимум: {min_amt}")

        if order.max_amount:
            max_amt = format_currency(Decimal(order.max_amount), order.fiat_currency)
            text_parts.append(f"📈 Максимум: {max_amt}")

        if order.payment_methods:
            methods = ", ".join([method.value.replace("_", " ").title() for method in order.payment_methods])
            text_parts.append(f"💳 Оплата: {methods}")

        if order.terms:
            text_parts.append(f"📝 Условия: {order.terms}")

        text_parts.append(f"👁️ Просмотров: {order.views_count}")
        text_parts.append(f"⏰ Создан: {format_datetime(order.created_at)}")

        status_emoji = {
            P2POrderStatus.ACTIVE: "🟢",
            P2POrderStatus.PAUSED: "🟡",
            P2POrderStatus.COMPLETED: "✅",
            P2POrderStatus.CANCELLED: "❌",
            P2POrderStatus.EXPIRED: "⏰"
        }

        status_text = {
            P2POrderStatus.ACTIVE: "Активен",
            P2POrderStatus.PAUSED: "Приостановлен",
            P2POrderStatus.COMPLETED: "Завершен",
            P2POrderStatus.CANCELLED: "Отменен",
            P2POrderStatus.EXPIRED: "Истек"
        }

        emoji = status_emoji.get(order.status, "❓")
        status = status_text.get(order.status, "Неизвестно")
        text_parts.append(f"{emoji} Статус: {status}")

        return "\n".join(text_parts)

    else:
        action = "Покупка" if order.type == P2POrderType.BUY else "Продажа"
        crypto_amount = format_currency(Decimal(order.crypto_amount), order.crypto_currency)
        price = format_currency(Decimal(order.price_per_unit), order.fiat_currency)

        return f"{action} {crypto_amount} по {price}"


def format_p2p_trade(trade: P2PTrade, short: bool = False, detailed: bool = False) -> str:
    if short:
        action = "Покупка" if trade.order.type == P2POrderType.BUY else "Продажа"
        amount = format_currency(Decimal(trade.trade_amount), trade.order.fiat_currency)

        status_emoji = {
            P2POrderStatus.PENDING: "🟡",
            P2POrderStatus.ACTIVE: "🔵",
            P2POrderStatus.COMPLETED: "✅",
            P2POrderStatus.CANCELLED: "❌",
            P2POrderStatus.DISPUTE: "⚠️"
        }

        emoji = status_emoji.get(trade.status, "❓")
        return f"{emoji} {action} {amount}"

    elif detailed:
        action = "Покупка" if trade.order.type == P2POrderType.BUY else "Продажа"
        fiat_amount = format_currency(Decimal(trade.trade_amount), trade.order.fiat_currency)
        crypto_amount = format_currency(Decimal(trade.crypto_amount), trade.order.crypto_currency)
        price = format_currency(Decimal(trade.order.price_per_unit), trade.order.fiat_currency)

        text_parts = [
            f"🤝 <b>Сделка #{trade.trade_id[:8]}</b>",
            f"🏷️ {action} {trade.order.crypto_currency}",
            f"💰 Сумма: {fiat_amount}",
            f"🪙 Количество: {crypto_amount}",
            f"💵 Курс: {price} за 1 {trade.order.crypto_currency}",
        ]

        if hasattr(trade, 'buyer') and trade.buyer:
            buyer_name = format_user_info(trade.buyer)
            text_parts.append(f"👤 Покупатель: {buyer_name}")

        if hasattr(trade, 'seller') and trade.seller:
            seller_name = format_user_info(trade.seller)
            text_parts.append(f"👤 Продавец: {seller_name}")

        if trade.payment_method:
            method_name = trade.payment_method.value.replace("_", " ").title()
            text_parts.append(f"💳 Оплата: {method_name}")

        if trade.payment_timeout_at:
            timeout_str = format_datetime(trade.payment_timeout_at)
            text_parts.append(f"⏰ Оплатить до: {timeout_str}")

        if trade.payment_confirmed_by_buyer:
            text_parts.append("✅ Оплата подтверждена покупателем")

        if trade.crypto_released:
            text_parts.append("✅ Криптовалюта отправлена")

        status_text = {
            P2POrderStatus.PENDING: "Ожидает подтверждения",
            P2POrderStatus.ACTIVE: "Активна",
            P2POrderStatus.COMPLETED: "Завершена",
            P2POrderStatus.CANCELLED: "Отменена",
            P2POrderStatus.DISPUTE: "Спор"
        }

        status_emoji = {
            P2POrderStatus.PENDING: "🟡",
            P2POrderStatus.ACTIVE: "🔵",
            P2POrderStatus.COMPLETED: "✅",
            P2POrderStatus.CANCELLED: "❌",
            P2POrderStatus.DISPUTE: "⚠️"
        }

        emoji = status_emoji.get(trade.status, "❓")
        status = status_text.get(trade.status, "Неизвестно")
        text_parts.append(f"{emoji} Статус: {status}")

        text_parts.append(f"📅 Создана: {format_datetime(trade.created_at)}")

        return "\n".join(text_parts)

    else:
        action = "Покупка" if trade.order.type == P2POrderType.BUY else "Продажа"
        amount = format_currency(Decimal(trade.trade_amount), trade.order.fiat_currency)

        return f"{action} {amount} - {trade.status.value}"


def format_check(check: Check, short: bool = False) -> str:
    amount = format_currency(check.amount, check.currency)

    if short:
        return f"Чек {amount}"

    text_parts = [
        f"🎁 <b>Чек {amount}</b>",
        f"🔗 Ссылка: {check.check_url}",
    ]

    if check.description:
        text_parts.append(f"📝 Описание: {check.description}")

    if check.uses_left > 0:
        text_parts.append(f"🔢 Активаций: {check.activations_count}/{check.uses_left}")
    else:
        text_parts.append(f"🔢 Активаций: {check.activations_count}")

    if check.expires_at:
        text_parts.append(f"⏰ Истекает: {format_datetime(check.expires_at)}")

    status = "✅ Активен" if check.is_active else "❌ Неактивен"
    text_parts.append(f"📊 Статус: {status}")

    text_parts.append(f"📅 Создан: {format_datetime(check.created_at)}")

    return "\n".join(text_parts)


def format_invoice(invoice: Invoice, short: bool = False) -> str:
    amount = format_currency(invoice.amount, invoice.currency)

    if short:
        return f"Инвойс {amount}"

    text_parts = [
        f"🧾 <b>Инвойс {amount}</b>",
        f"🔗 Ссылка: {invoice.invoice_url}",
    ]

    if invoice.description:
        text_parts.append(f"📝 Описание: {invoice.description}")

    if invoice.expires_at:
        text_parts.append(f"⏰ Истекает: {format_datetime(invoice.expires_at)}")

    status_text = {
        "pending": "🟡 Ожидает оплаты",
        "paid": "✅ Оплачен",
        "expired": "⏰ Истек",
        "cancelled": "❌ Отменен"
    }

    status = status_text.get(invoice.status, f"❓ {invoice.status}")
    text_parts.append(f"📊 Статус: {status}")

    if invoice.paid_at:
        text_parts.append(f"💰 Оплачен: {format_datetime(invoice.paid_at)}")

    text_parts.append(f"📅 Создан: {format_datetime(invoice.created_at)}")

    return "\n".join(text_parts)


def format_transaction_history(transactions: list, limit: int = 10) -> str:
    if not transactions:
        return "📭 История транзакций пуста"

    text_parts = ["📊 <b>История транзакций</b>\n"]

    for tx in transactions[:limit]:
        amount = format_currency(tx.amount, tx.currency)
        time_str = format_datetime(tx.created_at)

        if tx.type == "deposit":
            emoji = "📥"
            type_text = "Пополнение"
        elif tx.type == "withdrawal":
            emoji = "📤"
            type_text = "Вывод"
        elif tx.type == "transfer":
            emoji = "🔄"
            type_text = "Перевод"
        elif tx.type == "p2p_trade":
            emoji = "🤝"
            type_text = "P2P сделка"
        elif tx.type == "check_activation":
            emoji = "🎁"
            type_text = "Активация чека"
        elif tx.type == "invoice_payment":
            emoji = "🧾"
            type_text = "Оплата инвойса"
        else:
            emoji = "💰"
            type_text = tx.type.title()

        if tx.status == "completed":
            status_emoji = "✅"
        elif tx.status == "pending":
            status_emoji = "🟡"
        elif tx.status == "failed":
            status_emoji = "❌"
        else:
            status_emoji = "❓"

        tx_text = f"{emoji} {type_text} {amount} {status_emoji}"
        if tx.description:
            tx_text += f"\n   📝 {tx.description}"
        tx_text += f"\n   ⏰ {time_str}"

        text_parts.append(tx_text)

    if len(transactions) > limit:
        text_parts.append(f"\n... и еще {len(transactions) - limit} транзакций")

    return "\n\n".join(text_parts)


def format_user_stats(stats: dict) -> str:
    text_parts = ["📊 <b>Статистика</b>\n"]

    if "p2p" in stats:
        p2p_stats = stats["p2p"]
        text_parts.extend([
            "🤝 <b>P2P торговля:</b>",
            f"   📈 Всего сделок: {p2p_stats.get('total_trades', 0)}",
            f"   ✅ Завершено: {p2p_stats.get('completed_trades', 0)}",
            f"   📊 Рейтинг завершения: {format_percentage(p2p_stats.get('completion_rate', 0))}",
            f"   ⭐ Средняя оценка: {p2p_stats.get('average_rating', 0):.1f}/5",
            f"   💰 Объем торгов: {format_currency(Decimal(str(p2p_stats.get('total_volume', 0))), 'USD')}",
            ""
        ])

    if "wallet" in stats:
        wallet_stats = stats["wallet"]
        text_parts.extend([
            "💼 <b>Кошелек:</b>",
            f"   📥 Пополнений: {wallet_stats.get('deposits_count', 0)}",
            f"   📤 Выводов: {wallet_stats.get('withdrawals_count', 0)}",
            f"   💰 Общий оборот: {format_currency(Decimal(str(wallet_stats.get('total_turnover', 0))), 'USD')}",
            ""
        ])

    if "checks" in stats:
        check_stats = stats["checks"]
        text_parts.extend([
            "🎁 <b>Чеки:</b>",
            f"   📝 Создано: {check_stats.get('created_count', 0)}",
            f"   ✅ Активировано: {check_stats.get('activated_count', 0)}",
            f"   💰 Общая сумма: {format_currency(Decimal(str(check_stats.get('total_amount', 0))), 'USD')}",
            ""
        ])

    return "\n".join(text_parts)


def format_error_message(error: str, suggestion: Optional[str] = None) -> str:
    text = f"❌ <b>Ошибка</b>\n\n{error}"

    if suggestion:
        text += f"\n\n💡 <b>Совет:</b> {suggestion}"

    return text


def format_success_message(message: str, details: Optional[str] = None) -> str:
    text = f"✅ <b>Успешно</b>\n\n{message}"

    if details:
        text += f"\n\n{details}"

    return text


def truncate_text(text: str, max_length: int = 4000) -> str:
    if len(text) <= max_length:
        return text

    return text[:max_length - 3] + "..."


def escape_markdown(text: str) -> str:
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    for char in special_chars:
        text = text.replace(char, f'\\{char}')

    return text
