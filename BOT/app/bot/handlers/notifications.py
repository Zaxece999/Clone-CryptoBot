from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.services.user import user_service
from app.services.notification import notification_service
from app.models.notification import NotificationType, NotificationChannel
from app.bot.keyboards.inline import create_inline_keyboard
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = Router()


class NotificationStates(StatesGroup):
    waiting_email = State()
    waiting_phone = State()
    waiting_quiet_hours_start = State()
    waiting_quiet_hours_end = State()


@router.message(Command("notifications"))
async def cmd_notifications(message: Message, state: FSMContext):
    await state.clear()
    await show_notification_settings(message)


async def show_notification_settings(message: Message):
    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        settings = await notification_service.get_user_settings(db, user.id)

        status = "🟢 Включены" if settings.enabled else "🔴 Отключены"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"🔔 Уведомления: {status}",
                callback_data=f"toggle_notifications_{not settings.enabled}"
            )],
            [InlineKeyboardButton(text="📱 Типы уведомлений", callback_data="notification_types")],
            [InlineKeyboardButton(text="📢 Каналы доставки", callback_data="notification_channels")],
            [InlineKeyboardButton(text="📧 Контактные данные", callback_data="notification_contacts")],
            [InlineKeyboardButton(text="⏰ Тихие часы", callback_data="quiet_hours")],
            [InlineKeyboardButton(text="📊 История уведомлений", callback_data="notification_history")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_menu")]
        ])

        text = (
            "🔔 <b>Настройки уведомлений</b>\n\n"
            f"📊 <b>Статус:</b> {status}\n\n"
            "Настройте, какие уведомления и как вы хотите получать:\n\n"
            "• <b>Типы уведомлений</b> - выберите события для уведомлений\n"
            "• <b>Каналы доставки</b> - способы получения уведомлений\n"
            "• <b>Контактные данные</b> - email и телефон для уведомлений\n"
            "• <b>Тихие часы</b> - время, когда уведомления не отправляются"
        )

        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("toggle_notifications_"))
async def toggle_notifications(callback: CallbackQuery):
    enabled = callback.data.split("_")[-1] == "True"

    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        try:
            await notification_service.update_user_settings(
                db, user.id, {"enabled": enabled}
            )

            status_text = "включены" if enabled else "отключены"
            await callback.answer(f"✅ Уведомления {status_text}")
            await show_notification_settings(callback.message)

        except Exception as e:
            logger.error("❌ Не удалось изменить настройки уведомлений", error=str(e))
            await callback.answer("❌ Ошибка при изменении настроек")


@router.callback_query(F.data == "notification_types")
async def show_notification_types(callback: CallbackQuery):
    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        settings = await notification_service.get_user_settings(db, user.id)

        keyboard_buttons = []

        notification_types = [
            ("deposit_notifications", "💰 Пополнения", "Уведомления о поступлении средств"),
            ("withdrawal_notifications", "💸 Выводы", "Уведомления о выводе средств"),
            ("trading_notifications", "📈 Торговля", "P2P сделки и обмены"),
            ("security_notifications", "🔒 Безопасность", "Важные события безопасности"),
            ("promotional_notifications", "📢 Реклама", "Промо-акции и новости")
        ]

        for field, title, description in notification_types:
            is_enabled = getattr(settings, field)
            status = "✅" if is_enabled else "☐"

            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{status} {title}",
                    callback_data=f"toggle_type_{field}_{not is_enabled}"
                )
            ])

        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data="notification_settings")
        ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        text = (
            "📱 <b>Типы уведомлений</b>\n\n"
            "Выберите, о каких событиях вы хотите получать уведомления:\n\n"
        )

        for field, title, description in notification_types:
            is_enabled = getattr(settings, field)
            status = "✅" if is_enabled else "☐"
            text += f"{status} <b>{title}</b>\n   {description}\n\n"

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data.startswith("toggle_type_"))
async def toggle_notification_type(callback: CallbackQuery):
    parts = callback.data.split("_")
    field = "_".join(parts[2:-1])
    enabled = parts[-1] == "True"

    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        try:
            await notification_service.update_user_settings(
                db, user.id, {field: enabled}
            )

            await callback.answer("✅ Настройки обновлены")
            await show_notification_types(callback)

        except Exception as e:
            logger.error("❌ Не удалось изменить тип уведомления", error=str(e))
            await callback.answer("❌ Ошибка при изменении настроек")


@router.callback_query(F.data == "notification_channels")
async def show_notification_channels(callback: CallbackQuery):
    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        settings = await notification_service.get_user_settings(db, user.id)

        keyboard_buttons = []

        channels = [
            ("telegram_enabled", "📱 Telegram", "Уведомления в этом боте"),
            ("email_enabled", "📧 Email", "Уведомления на email"),
            ("push_enabled", "🔔 Push", "Push-уведомления в приложении"),
            ("sms_enabled", "📱 SMS", "SMS на телефон")
        ]

        for field, title, description in channels:
            is_enabled = getattr(settings, field)
            status = "✅" if is_enabled else "☐"

            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{status} {title}",
                    callback_data=f"toggle_channel_{field}_{not is_enabled}"
                )
            ])

        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data="notification_settings")
        ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        text = (
            "📢 <b>Каналы доставки</b>\n\n"
            "Выберите, как вы хотите получать уведомления:\n\n"
        )

        for field, title, description in channels:
            is_enabled = getattr(settings, field)
            status = "✅" if is_enabled else "☐"
            text += f"{status} <b>{title}</b>\n   {description}\n\n"

        text += (
            "💡 <b>Примечание:</b>\n"
            "• Telegram всегда доступен\n"
            "• Для Email и SMS нужно указать контактные данные\n"
            "• Push-уведомления работают в мобильном приложении"
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data.startswith("toggle_channel_"))
async def toggle_notification_channel(callback: CallbackQuery):
    parts = callback.data.split("_")
    field = "_".join(parts[2:-1])
    enabled = parts[-1] == "True"

    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        try:
            await notification_service.update_user_settings(
                db, user.id, {field: enabled}
            )

            await callback.answer("✅ Настройки обновлены")
            await show_notification_channels(callback)

        except Exception as e:
            logger.error("❌ Не удалось изменить канал уведомления", error=str(e))
            await callback.answer("❌ Ошибка при изменении настроек")


@router.callback_query(F.data == "notification_contacts")
async def show_notification_contacts(callback: CallbackQuery):
    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        settings = await notification_service.get_user_settings(db, user.id)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📧 Изменить Email", callback_data="change_email")],
            [InlineKeyboardButton(text="📱 Изменить телефон", callback_data="change_phone")],
            [InlineKeyboardButton(text="🗑️ Удалить Email", callback_data="remove_email")],
            [InlineKeyboardButton(text="🗑️ Удалить телефон", callback_data="remove_phone")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="notification_settings")]
        ])

        email_status = settings.email if settings.email else "Не указан"
        phone_status = settings.phone if settings.phone else "Не указан"

        text = (
            "📧 <b>Контактные данные</b>\n\n"
            f"📧 <b>Email:</b> {email_status}\n"
            f"📱 <b>Телефон:</b> {phone_status}\n\n"
            "Контактные данные используются для отправки уведомлений по email и SMS.\n\n"
            "⚠️ <b>Важно:</b>\n"
            "• Email и телефон проверяются при добавлении\n"
            "• Данные используются только для уведомлений\n"
            "• Вы можете удалить данные в любое время"
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "change_email")
async def change_email_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(NotificationStates.waiting_email)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="notification_contacts")]
    ])

    text = (
        "📧 <b>Изменение Email</b>\n\n"
        "Введите ваш email адрес для получения уведомлений:"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.message(NotificationStates.waiting_email)
async def change_email_process(message: Message, state: FSMContext):
    email = message.text.strip()

    if "@" not in email or "." not in email:
        await message.answer("❌ Неверный формат email. Попробуйте еще раз:")
        return

    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        try:
            await notification_service.update_user_settings(
                db, user.id, {"email": email}
            )

            await message.answer(f"✅ Email обновлен: {email}")
            await state.clear()
            await show_notification_contacts(message)

        except Exception as e:
            logger.error("❌ Не удалось обновить email", error=str(e))
            await message.answer("❌ Ошибка при обновлении email")


@router.callback_query(F.data == "change_phone")
async def change_phone_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(NotificationStates.waiting_phone)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="notification_contacts")]
    ])

    text = (
        "📱 <b>Изменение телефона</b>\n\n"
        "Введите номер телефона в международном формате (например: +79123456789):"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.message(NotificationStates.waiting_phone)
async def change_phone_process(message: Message, state: FSMContext):
    phone = message.text.strip()

    if not phone.startswith("+") or len(phone) < 10:
        await message.answer("❌ Неверный формат телефона. Используйте международный формат (+79123456789):")
        return

    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        try:
            await notification_service.update_user_settings(
                db, user.id, {"phone": phone}
            )

            await message.answer(f"✅ Телефон обновлен: {phone}")
            await state.clear()
            await show_notification_contacts(message)

        except Exception as e:
            logger.error("❌ Не удалось обновить телефон", error=str(e))
            await message.answer("❌ Ошибка при обновлении телефона")


@router.callback_query(F.data == "remove_email")
async def remove_email(callback: CallbackQuery):
    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        try:
            await notification_service.update_user_settings(
                db, user.id, {"email": None, "email_enabled": False}
            )

            await callback.answer("✅ Email удален")
            await show_notification_contacts(callback)

        except Exception as e:
            logger.error("❌ Не удалось удалить email", error=str(e))
            await callback.answer("❌ Ошибка при удалении email")


@router.callback_query(F.data == "remove_phone")
async def remove_phone(callback: CallbackQuery):
    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        try:
            await notification_service.update_user_settings(
                db, user.id, {"phone": None, "sms_enabled": False}
            )

            await callback.answer("✅ Телефон удален")
            await show_notification_contacts(callback)

        except Exception as e:
            logger.error("❌ Не удалось удалить телефон", error=str(e))
            await callback.answer("❌ Ошибка при удалении телефона")


@router.callback_query(F.data == "quiet_hours")
async def show_quiet_hours(callback: CallbackQuery):
    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        settings = await notification_service.get_user_settings(db, user.id)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌙 Установить начало", callback_data="set_quiet_start")],
            [InlineKeyboardButton(text="🌅 Установить конец", callback_data="set_quiet_end")],
            [InlineKeyboardButton(text="🗑️ Отключить тихие часы", callback_data="disable_quiet_hours")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="notification_settings")]
        ])

        start_time = settings.quiet_hours_start or "Не установлено"
        end_time = settings.quiet_hours_end or "Не установлено"

        text = (
            "⏰ <b>Тихие часы</b>\n\n"
            f"🌙 <b>Начало:</b> {start_time}\n"
            f"🌅 <b>Конец:</b> {end_time}\n"
            f"🌍 <b>Часовой пояс:</b> {settings.timezone}\n\n"
            "В тихие часы уведомления не отправляются, кроме критически важных.\n\n"
            "💡 <b>Примечание:</b>\n"
            "• Время указывается в формате ЧЧ:ММ (например: 23:00)\n"
            "• Уведомления безопасности отправляются всегда\n"
            "• Настройки применяются к вашему часовому поясу"
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "notification_history")
async def show_notification_history(callback: CallbackQuery):
    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return


        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="notification_history")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="notification_settings")]
        ])

        text = (
            "📊 <b>История уведомлений</b>\n\n"
            "У вас пока нет уведомлений.\n\n"
            "Здесь будет отображаться история всех отправленных уведомлений:\n"
            "• Время отправки\n"
            "• Тип уведомления\n"
            "• Статус доставки\n"
            "• Канал доставки"
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "notification_settings")
async def back_to_notification_settings(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_notification_settings(callback.message)
    await callback.answer()
