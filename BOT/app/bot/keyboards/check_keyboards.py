from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums.chat_type import ChatType
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.utils.texts import get_text
from app.models.check import Check, CheckStatus, CheckType


def get_check_main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="Создать чек",
            callback_data="check_create_new"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Создать из чата",
            callback_data="check_create_from_chat"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Активные чеки",
            callback_data="check_list_active"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="« Назад",
            callback_data="menu_main"
        )
    )

    return builder.as_markup()


def get_check_view_keyboard(check: Check, page: int = 1) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if check.is_gift:
        builder.row(
            InlineKeyboardButton(
                text="🎁 Отправить подарок",
                switch_inline_query=f"gift_{check.activation_code}"
            )
        )

        builder.row(
            InlineKeyboardButton(
                text="Добавить описание",
                callback_data=f"check_add_description:{check.id}"
            )
        )

        builder.row(
            InlineKeyboardButton(
                text="Закрепить за пользователем",
                callback_data=f"check_bind_user:{check.id}"
            )
        )

        builder.row(
            InlineKeyboardButton(
                text="Удалить подарок",
                callback_data=f"check_delete:{check.id}"
            )
        )

        builder.row(
            InlineKeyboardButton(
                text="← Назад к списку чеков",
                callback_data="check_list_active"
            )
        )

    else:
        builder.row(
            InlineKeyboardButton(
                text="Конвертировать в подарок",
                callback_data=f"check_convert_to_gift:{check.id}"
            )
        )

        builder.row(
            InlineKeyboardButton(
                text="Поделиться чеком",
                callback_data=f"check_share:{check.id}"
            ),
            InlineKeyboardButton(
                text="Показать QR-код",
                callback_data=f"check_show_qr:{check.id}"
            )
        )

        builder.row(
            InlineKeyboardButton(
                text="Добавить описание",
                callback_data=f"check_add_description:{check.id}"
            )
        )

        builder.row(
            InlineKeyboardButton(
                text="Добавить картинку",
                callback_data=f"check_add_image:{check.id}"
            )
        )

        builder.row(
            InlineKeyboardButton(
                text="Ограничения",
                callback_data=f"check_restrictions:{check.id}"
            )
        )

        builder.row(
            InlineKeyboardButton(
                text="Показать информацию о чеке",
                callback_data=f"check_show_info:{check.id}"
            )
        )

        builder.row(
            InlineKeyboardButton(
                text="Удалить чек",
                callback_data=f"check_delete:{check.id}"
            )
        )

        builder.row(
            InlineKeyboardButton(
                text="« Назад",
                callback_data="check_list_active"
            )
        )

    return builder.as_markup()


def get_check_restrictions_keyboard(check: Check, restrictions: dict = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if restrictions is None:
        restrictions = {}

    builder.row(
        InlineKeyboardButton(
            text="🔐 Добавить пароль",
            callback_data=f"check_add_password:{check.id}"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="👤 Закрепить за пользователем",
            callback_data=f"check_bind_user:{check.id}"
        )
    )

    premium_status = "Да" if restrictions.get("premium_only") else "Нет"
    builder.row(
        InlineKeyboardButton(
            text=f"💎 Только для Premium: {premium_status}",
            callback_data=f"check_toggle_premium:{check.id}"
        )
    )

    new_users = "Да" if restrictions.get("new_users_only") else "Нет"
    builder.row(
        InlineKeyboardButton(
            text=f"🆕 Только новые пользователи: {new_users}",
            callback_data=f"check_toggle_new_users:{check.id}"
        )
    )

    sub_check = "Вкл" if restrictions.get("subscription_required") else "Выкл"
    builder.row(
        InlineKeyboardButton(
            text=f"📢 Проверка подписки: {sub_check}",
            callback_data=f"check_subscription_settings:{check.id}"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="« Назад",
            callback_data=f"check_view:{check.id}"
        )
    )

    return builder.as_markup()


def get_subscription_settings_keyboard(check: Check) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="Добавить канал",
            callback_data=f"check_add_channel:{check.id}",
            request_chat={"chat_is_channel": True, "bot_is_member": True}
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Добавить группу",
            callback_data=f"check_add_group:{check.id}",
            request_chat={"chat_is_channel": False, "bot_is_member": True}
        )
    )

    if check.subscription_chat_ids:
        for chat_id in check.subscription_chat_ids[:3]:
            builder.row(
                InlineKeyboardButton(
                    text=f"❌ Удалить {chat_id}",
                    callback_data=f"check_remove_chat:{check.id}:{chat_id}"
                )
            )

    builder.row(
        InlineKeyboardButton(
            text="« Назад к ограничениям",
            callback_data=f"check_restrictions:{check.id}"
        )
    )

    return builder.as_markup()


def get_check_list_keyboard(
    checks: List[Check],
    page: int = 1,
    items_per_page: int = 10
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_checks = checks[start_idx:end_idx]

    for check in page_checks:
        amount_text = f"{check.amount} {check.currency}"
        text = f"Чек на {amount_text}"

        builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=f"check_view:{check.id}"
            )
        )

    nav_buttons = []

    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="« Назад",
                callback_data=f"check_list_page:{page-1}"
            )
        )

    if end_idx < len(checks):
        nav_buttons.append(
            InlineKeyboardButton(
                text="Вперед »",
                callback_data=f"check_list_page:{page+1}"
            )
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(
            text="« В меню чеков",
            callback_data="check_menu"
        )
    )

    return builder.as_markup()


def get_currency_selection_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    currencies = [
        "USDT", "TON", "SOL",
        "TRX", "GRAM", "BTC",
        "ETH", "DOGE", "LTC",
        "NOT", "TRUMP", "MELANIA",
        "PEPE", "WIF", "BONK",
        "MAJOR", "MY", "DOGS",
        "MEMHASH", "BNB", "HMSTR",
        "CATI", "USDC"
    ]

    for i in range(0, len(currencies), 3):
        row_currencies = currencies[i:i+3]
        buttons = [
            InlineKeyboardButton(
                text=currency,
                callback_data=f"check_currency_{currency}"
            )
            for currency in row_currencies
        ]
        builder.row(*buttons)

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к чекам",
            callback_data="check_menu"
        )
    )

    return builder.as_markup()


def get_check_delete_confirm_keyboard(check_id: str, language_code: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="Да",
            callback_data=f"check_delete_{check_id}"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Нет",
            callback_data=f"check_details_{check_id}"
        )
    )

    return builder.as_markup()


def get_check_details_keyboard(check_id: str, language_code: str = "ru", show_cancel: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🎁 Конвертировать в подарок",
            callback_data=f"check_convert_gift_{check_id}"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📤 Поделиться чеком",
            callback_data=f"check_share_{check_id}"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📱 Показать QR-код",
            callback_data=f"check_qr_{check_id}"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📝 Добавить описание",
            callback_data=f"check_add_description_{check_id}"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🖼️ Добавить картинку",
            callback_data=f"check_add_image_{check_id}"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="⚙️ Ограничения",
            callback_data=f"check_restrictions_{check_id}"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🗑️ Удалить чек",
            callback_data=f"check_delete_{check_id}"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к списку чеков",
            callback_data="check_list"
        )
    )

    return builder.as_markup()


def get_check_actions_keyboard(check_id: str, language_code: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="Закрепить за пользователем",
            callback_data=f"check_bind_user_{check_id}"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Добавить описание",
            callback_data=f"check_add_description_{check_id}"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="❌ Удалить чек",
            callback_data=f"delete_check_{check_id}"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="check_list"
        )
    )

    return builder.as_markup()
