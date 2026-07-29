from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.services.user import user_service
from app.services.admin import admin_service
from app.models.admin import AdminRole, AdminPermission
from app.bot.keyboards.inline import create_inline_keyboard
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = Router()


class AdminStates(StatesGroup):
    waiting_announcement_title = State()
    waiting_announcement_content = State()
    waiting_maintenance_title = State()
    waiting_maintenance_message = State()


async def check_admin_permission(
    callback: CallbackQuery,
    permission: AdminPermission
) -> bool:
    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return False

        admin_user = await admin_service.get_admin_by_user_id(db, user.id)
        if not admin_user or not admin_user.is_active:
            await callback.answer("❌ У вас нет прав администратора")
            return False

        if not admin_user.has_permission(permission):
            await callback.answer("❌ Недостаточно прав для выполнения этого действия")
            return False

        return True


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()

    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        admin_user = await admin_service.get_admin_by_user_id(db, user.id)
        if not admin_user or not admin_user.is_active:
            await message.answer("❌ У вас нет прав администратора")
            return

        await show_admin_dashboard(message, admin_user)


async def show_admin_dashboard(message: Message, admin_user):
    async for db in get_db():
        stats = await admin_service.get_dashboard_stats(db)

        keyboard_buttons = []

        if admin_user.has_permission(AdminPermission.USER_VIEW):
            keyboard_buttons.append([
                InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
            ])

        if admin_user.has_permission(AdminPermission.FINANCE_VIEW):
            keyboard_buttons.append([
                InlineKeyboardButton(text="💰 Финансы", callback_data="admin_finance")
            ])

        if admin_user.has_permission(AdminPermission.SYSTEM_CONFIG):
            keyboard_buttons.append([
                InlineKeyboardButton(text="⚙️ Система", callback_data="admin_system")
            ])

        if admin_user.has_permission(AdminPermission.CONTENT_MANAGE):
            keyboard_buttons.append([
                InlineKeyboardButton(text="📢 Объявления", callback_data="admin_announcements")
            ])

        if admin_user.has_permission(AdminPermission.SUPPORT_TICKETS):
            keyboard_buttons.append([
                InlineKeyboardButton(text="🎫 Поддержка", callback_data="admin_support")
            ])

        if admin_user.has_permission(AdminPermission.ANALYTICS_VIEW):
            keyboard_buttons.append([
                InlineKeyboardButton(text="📊 Аналитика", callback_data="admin_analytics")
            ])

        keyboard_buttons.extend([
            [InlineKeyboardButton(text="📋 Логи действий", callback_data="admin_logs")],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_dashboard")]
        ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        text = (
            f"🛡️ <b>Админ-панель</b>\n"
            f"👤 <b>Роль:</b> {admin_user.role.value.title()}\n\n"
            f"📊 <b>Статистика системы:</b>\n"
            f"👥 Всего пользователей: {stats.get('total_users', 0)}\n"
            f"📈 Новых за сегодня: {stats.get('today_users', 0)}\n"
            f"💳 Транзакций сегодня: {stats.get('today_transactions', 0)}\n"
            f"🎫 Активных тикетов: {stats.get('active_tickets', 0)}\n"
            f"🟢 Статус системы: {stats.get('system_status', 'unknown').title()}\n\n"
            f"Выберите раздел для управления:"
        )

        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin_users")
async def show_admin_users(callback: CallbackQuery):
    if not await check_admin_permission(callback, AdminPermission.USER_VIEW):
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_users_list")],
        [InlineKeyboardButton(text="🔍 Поиск пользователя", callback_data="admin_users_search")],
        [InlineKeyboardButton(text="📊 Статистика пользователей", callback_data="admin_users_stats")],
        [InlineKeyboardButton(text="🚫 Заблокированные", callback_data="admin_users_banned")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_dashboard")]
    ])

    text = (
        "👥 <b>Управление пользователями</b>\n\n"
        "Выберите действие:\n\n"
        "• <b>Список пользователей</b> - просмотр всех пользователей\n"
        "• <b>Поиск пользователя</b> - найти конкретного пользователя\n"
        "• <b>Статистика</b> - аналитика по пользователям\n"
        "• <b>Заблокированные</b> - управление блокировками"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_finance")
async def show_admin_finance(callback: CallbackQuery):
    if not await check_admin_permission(callback, AdminPermission.FINANCE_VIEW):
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Балансы", callback_data="admin_finance_balances")],
        [InlineKeyboardButton(text="📊 Транзакции", callback_data="admin_finance_transactions")],
        [InlineKeyboardButton(text="📤 Выводы", callback_data="admin_finance_withdrawals")],
        [InlineKeyboardButton(text="📥 Депозиты", callback_data="admin_finance_deposits")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_finance_settings")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_dashboard")]
    ])

    text = (
        "💰 <b>Управление финансами</b>\n\n"
        "Выберите раздел:\n\n"
        "• <b>Балансы</b> - просмотр балансов пользователей\n"
        "• <b>Транзакции</b> - история всех транзакций\n"
        "• <b>Выводы</b> - управление запросами на вывод\n"
        "• <b>Депозиты</b> - мониторинг поступлений\n"
        "• <b>Настройки</b> - лимиты и комиссии"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_system")
async def show_admin_system(callback: CallbackQuery):
    if not await check_admin_permission(callback, AdminPermission.SYSTEM_CONFIG):
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Конфигурация", callback_data="admin_system_config")],
        [InlineKeyboardButton(text="🔧 Техобслуживание", callback_data="admin_system_maintenance")],
        [InlineKeyboardButton(text="📊 Мониторинг", callback_data="admin_system_monitoring")],
        [InlineKeyboardButton(text="🗂️ Логи системы", callback_data="admin_system_logs")],
        [InlineKeyboardButton(text="🔄 Перезагрузка", callback_data="admin_system_restart")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_dashboard")]
    ])

    text = (
        "⚙️ <b>Системные настройки</b>\n\n"
        "Выберите действие:\n\n"
        "• <b>Конфигурация</b> - настройки системы\n"
        "• <b>Техобслуживание</b> - режим обслуживания\n"
        "• <b>Мониторинг</b> - состояние системы\n"
        "• <b>Логи системы</b> - системные логи\n"
        "• <b>Перезагрузка</b> - перезапуск сервисов"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_system_maintenance")
async def show_maintenance_mode(callback: CallbackQuery):
    if not await check_admin_permission(callback, AdminPermission.SYSTEM_MAINTENANCE):
        return

    async for db in get_db():
        maintenance = await admin_service.get_current_maintenance_mode(db)

        if maintenance and maintenance.is_enabled:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔴 Отключить обслуживание", callback_data="admin_maintenance_disable")],
                [InlineKeyboardButton(text="✏️ Изменить сообщение", callback_data="admin_maintenance_edit")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_system")]
            ])

            status = "🔴 Включен"
            started_at = maintenance.started_at.strftime("%d.%m.%Y %H:%M") if maintenance.started_at else "Неизвестно"
            estimated_end = maintenance.estimated_end_at.strftime("%d.%m.%Y %H:%M") if maintenance.estimated_end_at else "Не указано"

            text = (
                f"🔧 <b>Режим технического обслуживания</b>\n\n"
                f"📊 <b>Статус:</b> {status}\n"
                f"🕐 <b>Начало:</b> {started_at}\n"
                f"⏰ <b>Планируемое окончание:</b> {estimated_end}\n\n"
                f"📝 <b>Заголовок:</b> {maintenance.title or 'Не указан'}\n"
                f"💬 <b>Сообщение:</b>\n{maintenance.message or 'Не указано'}\n\n"
                f"⚠️ Пользователи не могут использовать бота"
            )
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🟢 Включить обслуживание", callback_data="admin_maintenance_enable")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_system")]
            ])

            text = (
                f"🔧 <b>Режим технического обслуживания</b>\n\n"
                f"📊 <b>Статус:</b> 🟢 Отключен\n\n"
                f"Система работает в обычном режиме.\n"
                f"Все функции доступны пользователям."
            )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "admin_maintenance_enable")
async def enable_maintenance_start(callback: CallbackQuery, state: FSMContext):
    if not await check_admin_permission(callback, AdminPermission.SYSTEM_MAINTENANCE):
        return

    await state.set_state(AdminStates.waiting_maintenance_title)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_system_maintenance")]
    ])

    text = (
        "🔧 <b>Включение режима обслуживания</b>\n\n"
        "Введите заголовок для сообщения об обслуживании:"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.message(AdminStates.waiting_maintenance_title)
async def enable_maintenance_title(message: Message, state: FSMContext):
    title = message.text.strip()

    if len(title) > 255:
        await message.answer("❌ Заголовок слишком длинный (максимум 255 символов)")
        return

    await state.update_data(title=title)
    await state.set_state(AdminStates.waiting_maintenance_message)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="admin_maintenance_skip_message")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_system_maintenance")]
    ])

    text = (
        f"🔧 <b>Включение режима обслуживания</b>\n\n"
        f"Заголовок: <b>{title}</b>\n\n"
        f"Введите сообщение для пользователей:"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(AdminStates.waiting_maintenance_message)
async def enable_maintenance_message(message: Message, state: FSMContext):
    message_text = message.text.strip()

    if len(message_text) > 1000:
        await message.answer("❌ Сообщение слишком длинное (максимум 1000 символов)")
        return

    await finish_maintenance_enable(message, state, message_text)


@router.callback_query(F.data == "admin_maintenance_skip_message")
async def skip_maintenance_message(callback: CallbackQuery, state: FSMContext):
    await finish_maintenance_enable(callback.message, state, None)
    await callback.answer()


async def finish_maintenance_enable(message: Message, state: FSMContext, message_text: Optional[str]):
    data = await state.get_data()
    title = data.get("title")

    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        admin_user = await admin_service.get_admin_by_user_id(db, user.id)
        if not admin_user:
            await message.answer("❌ У вас нет прав администратора")
            return

        try:
            await admin_service.enable_maintenance_mode(
                db=db,
                title=title,
                message=message_text or "Система временно недоступна",
                admin_user_id=admin_user.id
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔧 Управление обслуживанием", callback_data="admin_system_maintenance")],
                [InlineKeyboardButton(text="🏠 Главная", callback_data="admin_dashboard")]
            ])

            text = (
                f"✅ <b>Режим обслуживания включен</b>\n\n"
                f"📝 <b>Заголовок:</b> {title}\n"
                f"💬 <b>Сообщение:</b> {message_text or 'Система временно недоступна'}\n\n"
                f"⚠️ Пользователи больше не могут использовать бота"
            )

            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

        except Exception as e:
            logger.error("❌ Не удалось включить режим обслуживания", error=str(e))
            await message.answer("❌ Ошибка при включении режима обслуживания")

    await state.clear()


@router.callback_query(F.data == "admin_maintenance_disable")
async def disable_maintenance_mode(callback: CallbackQuery):
    if not await check_admin_permission(callback, AdminPermission.SYSTEM_MAINTENANCE):
        return

    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        admin_user = await admin_service.get_admin_by_user_id(db, user.id)
        if not admin_user:
            await callback.answer("❌ У вас нет прав администратора")
            return

        try:
            success = await admin_service.disable_maintenance_mode(db, admin_user.id)

            if success:
                await callback.answer("✅ Режим обслуживания отключен")
                await show_maintenance_mode(callback)
            else:
                await callback.answer("❌ Режим обслуживания уже отключен")

        except Exception as e:
            logger.error("❌ Не удалось отключить режим обслуживания", error=str(e))
            await callback.answer("❌ Ошибка при отключении режима обслуживания")


@router.callback_query(F.data == "admin_announcements")
async def show_admin_announcements(callback: CallbackQuery):
    if not await check_admin_permission(callback, AdminPermission.CONTENT_MANAGE):
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать объявление", callback_data="admin_announcement_create")],
        [InlineKeyboardButton(text="📋 Список объявлений", callback_data="admin_announcement_list")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_announcement_stats")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_dashboard")]
    ])

    text = (
        "📢 <b>Управление объявлениями</b>\n\n"
        "Выберите действие:\n\n"
        "• <b>Создать объявление</b> - новое объявление\n"
        "• <b>Список объявлений</b> - все объявления\n"
        "• <b>Статистика</b> - просмотры и клики"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_logs")
async def show_admin_logs(callback: CallbackQuery):
    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        admin_user = await admin_service.get_admin_by_user_id(db, user.id)
        if not admin_user:
            await callback.answer("❌ У вас нет прав администратора")
            return

        logs = await admin_service.get_admin_action_logs(db, limit=10)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_logs")],
            [InlineKeyboardButton(text="📊 Фильтры", callback_data="admin_logs_filters")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_dashboard")]
        ])

        text = "📋 <b>Логи действий администраторов</b>\n\n"

        if logs:
            for log in logs[:5]:
                admin_name = f"Admin #{log.admin_user_id}"
                time_str = log.created_at.strftime("%d.%m %H:%M")
                text += f"• <b>{time_str}</b> - {admin_name}\n  {log.description}\n\n"
        else:
            text += "Логи отсутствуют"

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "admin_dashboard")
async def back_to_admin_dashboard(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        admin_user = await admin_service.get_admin_by_user_id(db, user.id)
        if not admin_user:
            await callback.answer("❌ У вас нет прав администратора")
            return

        await show_admin_dashboard(callback.message, admin_user)
        await callback.answer()
