from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any, Optional

from app.models.settings import ReferralPeriod, NotificationSubtype


def get_settings_main_keyboard(
    user_timezone: str = "UTC",
    user_currency: str = "USD",
    language_code: str = "ru"
) -> InlineKeyboardMarkup:

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="👥 Рефералы",
            callback_data="settings_referrals"
        ),
        InlineKeyboardButton(
            text="🛎 Уведомления",
            callback_data="settings_notifications"
        )
    )

    timezone_text = "🌎 Часовой пояс"
    if language_code == "en":
        timezone_text = "🌎 Timezone"

    language_flag = "🇷🇺" if language_code == "ru" else "🇺🇸"
    language_text = f"{language_flag} Язык бота" if language_code == "ru" else f"{language_flag} Language"

    builder.row(
        InlineKeyboardButton(
            text=timezone_text,
            url="https://app.cr.bot/account/settings"
        ),
        InlineKeyboardButton(
            text=language_text,
            callback_data="settings_language"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text=f"🤑 Валюта бота · {user_currency}",
            callback_data="settings_currency"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Комиссии и лимиты",
            callback_data="settings_fees_limits"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Конкурсы",
            callback_data="settings_contests"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Справка Crypto Bot",
            url="https://help.send.tg/ru/"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Что умеет Crypto Bot",
            url="http://t.me/CryptoBotTips"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Написать в поддержку",
            url="http://t.me/CryptoSupportBot"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="main_menu"
        )
    )

    return builder.as_markup()


def get_referrals_keyboard(
    selected_period: ReferralPeriod = ReferralPeriod.ALL_TIME
) -> InlineKeyboardMarkup:

    builder = InlineKeyboardBuilder()

    periods = [
        ("За всё время", ReferralPeriod.ALL_TIME),
        ("За вчера", ReferralPeriod.YESTERDAY),
        ("За неделю", ReferralPeriod.WEEK),
        ("За месяц", ReferralPeriod.MONTH)
    ]

    period1_text = f"· {periods[0][0]} ·" if selected_period == periods[0][1] else periods[0][0]
    period2_text = f"· {periods[1][0]} ·" if selected_period == periods[1][1] else periods[1][0]

    builder.row(
        InlineKeyboardButton(
            text=period1_text,
            callback_data=f"referrals_period_{periods[0][1].value}"
        ),
        InlineKeyboardButton(
            text=period2_text,
            callback_data=f"referrals_period_{periods[1][1].value}"
        )
    )

    period3_text = f"· {periods[2][0]} ·" if selected_period == periods[2][1] else periods[2][0]
    period4_text = f"· {periods[3][0]} ·" if selected_period == periods[3][1] else periods[3][0]

    builder.row(
        InlineKeyboardButton(
            text=period3_text,
            callback_data=f"referrals_period_{periods[2][1].value}"
        ),
        InlineKeyboardButton(
            text=period4_text,
            callback_data=f"referrals_period_{periods[3][1].value}"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="settings_menu"
        )
    )

    return builder.as_markup()


def get_notifications_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📣 Общие рассылки",
            callback_data="notifications_broadcasts"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="👥 Рефералы",
            callback_data="notifications_referrals"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🏝 Crypto Pay",
            callback_data="notifications_crypto_pay"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="💠 P2P Маркет",
            callback_data="notifications_p2p_market"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🎁 Розыгрыши",
            callback_data="notifications_giveaways"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🍑 Для владельцев каналов",
            callback_data="notifications_subscriptions_creator"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="💦 Для подписчиков",
            callback_data="notifications_subscriptions_subscriber"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="settings_menu"
        )
    )

    return builder.as_markup()


def get_notifications_broadcasts_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="Новостные рассылки",
            callback_data="notifications_news_broadcasts"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Маркетинговые рассылки",
            callback_data="notifications_marketing_broadcasts"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="settings_notifications"
        )
    )

    return builder.as_markup()


def get_notification_setting_keyboard(
    subtype: NotificationSubtype,
    enabled: bool = True,
    sound: bool = True,
    show_sound: bool = True
) -> InlineKeyboardMarkup:

    builder = InlineKeyboardBuilder()

    if subtype != NotificationSubtype.INSUFFICIENT_BALANCE:
        enabled_text = "Уведомления: Вкл." if enabled else "Уведомления: Выкл."
        builder.row(
            InlineKeyboardButton(
                text=enabled_text,
                callback_data=f"notification_toggle_{subtype.value}_enabled"
            )
        )

    if show_sound and (enabled or subtype == NotificationSubtype.INSUFFICIENT_BALANCE):
        sound_text = "Звук: Вкл." if sound else "Звук: Выкл."
        builder.row(
            InlineKeyboardButton(
                text=sound_text,
                callback_data=f"notification_toggle_{subtype.value}_sound"
            )
        )

    back_callbacks = {
        NotificationSubtype.NEWS_BROADCASTS: "notifications_broadcasts",
        NotificationSubtype.MARKETING_BROADCASTS: "notifications_broadcasts",
        NotificationSubtype.REFERRAL_REWARDS: "notifications_referrals",
        NotificationSubtype.PAYMENT_NOTIFICATIONS: "notifications_crypto_pay",
        NotificationSubtype.NEW_REVIEW: "notifications_p2p_market",
        NotificationSubtype.INVITATION_PARTICIPATION: "notifications_giveaways",
        NotificationSubtype.NEW_SUBSCRIBERS: "notifications_subscriptions_creator",
        NotificationSubtype.SUBSCRIPTION_RENEWALS: "notifications_subscriptions_creator",
        NotificationSubtype.SUBSCRIPTION_CANCELLATIONS: "notifications_subscriptions_creator",
        NotificationSubtype.RENEWAL_NOTIFICATIONS: "notifications_subscriptions_subscriber",
        NotificationSubtype.INSUFFICIENT_BALANCE: "notifications_subscriptions_subscriber",
        NotificationSubtype.CANCELLATION_NOTIFICATIONS: "notifications_subscriptions_subscriber",
    }

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data=back_callbacks.get(subtype, "settings_notifications")
        )
    )

    return builder.as_markup()


def get_notifications_referrals_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="Реферальные вознаграждения",
            callback_data="notifications_referral_rewards"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="settings_notifications"
        )
    )

    return builder.as_markup()


def get_notifications_crypto_pay_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="Уведомления об оплате счёта",
            callback_data="notifications_payment_notifications"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="settings_notifications"
        )
    )

    return builder.as_markup()


def get_notifications_p2p_market_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="Новый отзыв",
            callback_data="notifications_new_review"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="settings_notifications"
        )
    )

    return builder.as_markup()


def get_notifications_giveaways_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="Участие по приглашению",
            callback_data="notifications_invitation_participation"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="settings_notifications"
        )
    )

    return builder.as_markup()


def get_notifications_subscriptions_creator_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="Новые подписчики",
            callback_data="notifications_new_subscribers"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Продление подписок",
            callback_data="notifications_subscription_renewals"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Отмена подписок",
            callback_data="notifications_subscription_cancellations"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="settings_notifications"
        )
    )

    return builder.as_markup()


def get_notifications_subscriptions_subscriber_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="Уведомления о продлении",
            callback_data="notifications_renewal_notifications"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Уведомления о недостаточном балансе",
            callback_data="notifications_insufficient_balance"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Уведомления об отмене",
            callback_data="notifications_cancellation_notifications"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="settings_notifications"
        )
    )

    return builder.as_markup()


def get_language_keyboard(current_language: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    en_text = "🇺🇸 English"
    if current_language == "en":
        en_text = f"· {en_text} ·"

    ru_text = "🇷🇺 Русский"
    if current_language == "ru":
        ru_text = f"· {ru_text} ·"

    builder.row(
        InlineKeyboardButton(
            text=en_text,
            callback_data="language_en"
        ),
        InlineKeyboardButton(
            text=ru_text,
            callback_data="language_ru"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="settings_menu"
        )
    )

    return builder.as_markup()


def get_currency_keyboard(current_currency: str = "USD") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    currencies = [
        ["RUB", "USD", "EUR", "BYN"],
        ["UAH", "GBP", "CNY", "KZT"],
        ["UZS", "GEL", "TRY", "AMD"],
        ["THB", "INR", "BRL", "IDR"],
        ["AZN", "AED", "PLN", "ILS"],
        ["KGS", "TJS"]
    ]

    for row in currencies:
        buttons = []
        for currency in row:
            text = currency
            if currency == current_currency:
                text = f"· {currency} ·"

            buttons.append(
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"currency_{currency}"
                )
            )
        builder.row(*buttons)

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="settings_menu"
        )
    )

    return builder.as_markup()


def get_back_to_settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="settings_menu"
        )
    )

    return builder.as_markup()
