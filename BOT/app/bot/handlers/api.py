from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import secrets
import string

from app.database import get_db
from app.services.user import user_service
from app.services.api import api_service
from app.models.api import ApiKeyScope
from app.bot.keyboards.inline import create_inline_keyboard
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = Router()


class ApiStates(StatesGroup):
    waiting_app_name = State()
    waiting_app_description = State()
    waiting_key_name = State()
    selecting_scopes = State()


@router.message(Command("api"))
async def cmd_api(message: Message, state: FSMContext):
    await state.clear()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Мои приложения", callback_data="api_apps")],
        [InlineKeyboardButton(text="🔑 Мои API ключи", callback_data="api_keys")],
        [InlineKeyboardButton(text="📊 Статистика API", callback_data="api_stats")],
        [InlineKeyboardButton(text="📖 Документация", callback_data="api_docs")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])

    text = (
        "🔧 <b>API для разработчиков</b>\n\n"
        "Crypto Pay API позволяет интегрировать функции бота в ваши приложения:\n\n"
        "• Создание и управление инвойсами\n"
        "• Создание и управление чеками\n"
        "• Переводы между пользователями\n"
        "• Получение баланса и курсов валют\n"
        "• Webhook уведомления\n\n"
        "Выберите действие:"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "api_apps")
async def show_api_apps(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        apps = await api_service.get_user_applications(db, user.id)

        if not apps:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать приложение", callback_data="create_app")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="api_menu")]
            ])

            text = (
                "📱 <b>Мои приложения</b>\n\n"
                "У вас пока нет приложений.\n"
                "Создайте первое приложение для получения API ключей."
            )
        else:
            keyboard_buttons = []
            text = "📱 <b>Мои приложения</b>\n\n"

            for app in apps:
                text += f"• <b>{app.name}</b>\n"
                text += f"  ID: <code>{app.id}</code>\n"
                text += f"  Статус: {'🟢 Активно' if app.is_active else '🔴 Неактивно'}\n\n"

                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"⚙️ {app.name}",
                        callback_data=f"app_manage_{app.id}"
                    )
                ])

            keyboard_buttons.extend([
                [InlineKeyboardButton(text="➕ Создать приложение", callback_data="create_app")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="api_menu")]
            ])

            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "create_app")
async def create_app_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ApiStates.waiting_app_name)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="api_apps")]
    ])

    text = (
        "📱 <b>Создание приложения</b>\n\n"
        "Введите название приложения:\n"
        "(например: 'Мой магазин', 'Игровой бот')"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.message(ApiStates.waiting_app_name)
async def create_app_name(message: Message, state: FSMContext):
    name = message.text.strip()

    if len(name) < 3 or len(name) > 50:
        await message.answer(
            "❌ Название должно быть от 3 до 50 символов.\n"
            "Попробуйте еще раз:"
        )
        return

    await state.update_data(app_name=name)
    await state.set_state(ApiStates.waiting_app_description)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_description")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="api_apps")]
    ])

    text = (
        f"📱 <b>Создание приложения</b>\n\n"
        f"Название: <b>{name}</b>\n\n"
        f"Введите описание приложения (необязательно):"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(ApiStates.waiting_app_description)
async def create_app_description(message: Message, state: FSMContext):
    description = message.text.strip()

    if len(description) > 200:
        await message.answer(
            "❌ Описание не должно превышать 200 символов.\n"
            "Попробуйте еще раз:"
        )
        return

    await finish_app_creation(message, state, description)


@router.callback_query(F.data == "skip_description")
async def skip_app_description(callback: CallbackQuery, state: FSMContext):
    await finish_app_creation(callback.message, state, None)
    await callback.answer()


async def finish_app_creation(message: Message, state: FSMContext, description: Optional[str]):
    data = await state.get_data()

    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        try:
            app = await api_service.create_application(
                db=db,
                user_id=user.id,
                name=data["app_name"],
                description=description
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔑 Создать API ключ", callback_data=f"create_key_{app.id}")],
                [InlineKeyboardButton(text="📱 Мои приложения", callback_data="api_apps")]
            ])

            text = (
                f"✅ <b>Приложение создано!</b>\n\n"
                f"📱 <b>Название:</b> {app.name}\n"
                f"🆔 <b>ID:</b> <code>{app.id}</code>\n"
            )

            if description:
                text += f"📝 <b>Описание:</b> {description}\n"

            text += "\nТеперь вы можете создать API ключи для этого приложения."

            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

        except Exception as e:
            logger.error("❌ Не удалось создать приложение", error=str(e), exc_info=True)
            await message.answer("❌ Ошибка при создании приложения. Попробуйте позже.")

    await state.clear()


@router.callback_query(F.data.startswith("app_manage_"))
async def manage_app(callback: CallbackQuery):
    app_id = int(callback.data.split("_")[-1])

    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        app = await api_service.get_application(db, app_id, user.id)
        if not app:
            await callback.answer("❌ Приложение не найдено")
            return

        keys = await api_service.get_application_keys(db, app_id)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔑 API ключи", callback_data=f"app_keys_{app_id}")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data=f"app_stats_{app_id}")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data=f"app_settings_{app_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="api_apps")]
        ])

        text = (
            f"📱 <b>{app.name}</b>\n\n"
            f"🆔 <b>ID:</b> <code>{app.id}</code>\n"
            f"📅 <b>Создано:</b> {app.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"🔑 <b>API ключей:</b> {len(keys)}\n"
            f"📊 <b>Статус:</b> {'🟢 Активно' if app.is_active else '🔴 Неактивно'}\n"
        )

        if app.description:
            text += f"📝 <b>Описание:</b> {app.description}\n"

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "api_keys")
async def show_api_keys(callback: CallbackQuery):
    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        keys = await api_service.get_user_keys(db, user.id)

        if not keys:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📱 Создать приложение", callback_data="create_app")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="api_menu")]
            ])

            text = (
                "🔑 <b>Мои API ключи</b>\n\n"
                "У вас пока нет API ключей.\n"
                "Сначала создайте приложение."
            )
        else:
            keyboard_buttons = []
            text = "🔑 <b>Мои API ключи</b>\n\n"

            for key in keys:
                status = "🟢" if key.is_active else "🔴"
                text += f"{status} <b>{key.name}</b>\n"
                text += f"   Приложение: {key.application.name}\n"
                text += f"   Создан: {key.created_at.strftime('%d.%m.%Y')}\n\n"

                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"⚙️ {key.name}",
                        callback_data=f"key_manage_{key.id}"
                    )
                ])

            keyboard_buttons.append([
                InlineKeyboardButton(text="◀️ Назад", callback_data="api_menu")
            ])

            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data.startswith("create_key_"))
async def create_key_start(callback: CallbackQuery, state: FSMContext):
    app_id = int(callback.data.split("_")[-1])

    await state.update_data(app_id=app_id)
    await state.set_state(ApiStates.waiting_key_name)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"app_manage_{app_id}")]
    ])

    text = (
        "🔑 <b>Создание API ключа</b>\n\n"
        "Введите название для API ключа:\n"
        "(например: 'Production', 'Test', 'Mobile App')"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.message(ApiStates.waiting_key_name)
async def create_key_name(message: Message, state: FSMContext):
    name = message.text.strip()

    if len(name) < 3 or len(name) > 30:
        await message.answer(
            "❌ Название должно быть от 3 до 30 символов.\n"
            "Попробуйте еще раз:"
        )
        return

    await state.update_data(key_name=name)
    await show_scope_selection(message, state)


async def show_scope_selection(message: Message, state: FSMContext):
    await state.set_state(ApiStates.selecting_scopes)

    data = await state.get_data()
    selected_scopes = data.get("selected_scopes", [])

    keyboard_buttons = []

    scopes_info = {
        ApiKeyScope.READ: ("📖 Чтение", "Получение информации о балансе, курсах"),
        ApiKeyScope.INVOICE_WRITE: ("📄 Инвойсы", "Создание и управление инвойсами"),
        ApiKeyScope.INVOICE_READ: ("📄 Чтение инвойсов", "Просмотр инвойсов"),
        ApiKeyScope.CHECK_WRITE: ("💸 Чеки", "Создание и управление чеками"),
        ApiKeyScope.CHECK_READ: ("💸 Чтение чеков", "Просмотр чеков"),
        ApiKeyScope.WALLET_READ: ("👛 Чтение кошелька", "Просмотр баланса"),
        ApiKeyScope.WALLET_WRITE: ("👛 Переводы", "Выполнение переводов"),
    }

    for scope, (title, description) in scopes_info.items():
        is_selected = scope in selected_scopes
        prefix = "✅" if is_selected else "☐"

        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{prefix} {title}",
                callback_data=f"toggle_scope_{scope.value}"
            )
        ])

    keyboard_buttons.extend([
        [InlineKeyboardButton(text="✅ Создать ключ", callback_data="finish_key_creation")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_key_creation")]
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    text = (
        f"🔑 <b>Создание API ключа</b>\n\n"
        f"Название: <b>{data['key_name']}</b>\n\n"
        f"Выберите разрешения для API ключа:\n\n"
    )

    for scope, (title, description) in scopes_info.items():
        is_selected = scope in selected_scopes
        prefix = "✅" if is_selected else "☐"
        text += f"{prefix} <b>{title}</b>\n   {description}\n\n"

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("toggle_scope_"))
async def toggle_scope(callback: CallbackQuery, state: FSMContext):
    scope_value = callback.data.split("_")[-1]
    scope = ApiKeyScope(scope_value)

    data = await state.get_data()
    selected_scopes = data.get("selected_scopes", [])

    if scope in selected_scopes:
        selected_scopes.remove(scope)
    else:
        selected_scopes.append(scope)

    await state.update_data(selected_scopes=selected_scopes)
    await show_scope_selection(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "finish_key_creation")
async def finish_key_creation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if not data.get("selected_scopes"):
        await callback.answer("❌ Выберите хотя бы одно разрешение")
        return

    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        try:
            key = await api_service.create_api_key(
                db=db,
                application_id=data["app_id"],
                name=data["key_name"],
                scopes=data["selected_scopes"]
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📱 К приложению", callback_data=f"app_manage_{data['app_id']}")],
                [InlineKeyboardButton(text="🔑 Мои ключи", callback_data="api_keys")]
            ])

            scopes_text = ", ".join([scope.value for scope in data["selected_scopes"]])

            text = (
                f"✅ <b>API ключ создан!</b>\n\n"
                f"🔑 <b>Ключ:</b> <code>{key.key}</code>\n\n"
                f"⚠️ <b>ВАЖНО:</b> Сохраните этот ключ в безопасном месте!\n"
                f"Он больше не будет показан в полном виде.\n\n"
                f"📝 <b>Название:</b> {key.name}\n"
                f"🔐 <b>Разрешения:</b> {scopes_text}\n\n"
                f"📖 Документация API: /api → Документация"
            )

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

        except Exception as e:
            logger.error("❌ Не удалось создать API ключ", error=str(e), exc_info=True)
            await callback.answer("❌ Ошибка при создании ключа")

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_key_creation")
async def cancel_key_creation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    app_id = data.get("app_id")

    await state.clear()

    if app_id:
        await manage_app(callback)
    else:
        await show_api_keys(callback)


@router.callback_query(F.data == "api_stats")
async def show_api_stats(callback: CallbackQuery):
    async for db in get_db():
        user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        stats = await api_service.get_user_api_stats(db, user.id)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="api_menu")]
        ])

        text = (
            f"📊 <b>Статистика API</b>\n\n"
            f"📱 <b>Приложений:</b> {stats.get('applications', 0)}\n"
            f"🔑 <b>API ключей:</b> {stats.get('api_keys', 0)}\n"
            f"📈 <b>Запросов сегодня:</b> {stats.get('requests_today', 0)}\n"
            f"📊 <b>Запросов всего:</b> {stats.get('total_requests', 0)}\n\n"
            f"💰 <b>Инвойсов создано:</b> {stats.get('invoices_created', 0)}\n"
            f"💸 <b>Чеков создано:</b> {stats.get('checks_created', 0)}\n"
            f"💳 <b>Переводов выполнено:</b> {stats.get('transfers_made', 0)}\n"
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "api_docs")
async def show_api_docs(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Полная документация", url="https://help.crypt.bot/crypto-pay-api")],
        [InlineKeyboardButton(text="📝 Примеры кода", callback_data="api_examples")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="api_menu")]
    ])

    text = (
        "📖 <b>Документация Crypto Pay API</b>\n\n"
        "<b>Base URL:</b> <code>https://pay.crypt.bot/api</code>\n\n"
        "<b>Аутентификация:</b>\n"
        "Добавьте заголовок: <code>Crypto-Pay-API-Token: YOUR_API_KEY</code>\n\n"
        "<b>Основные методы:</b>\n"
        "• <code>GET /getMe</code> - информация о приложении\n"
        "• <code>GET /getBalance</code> - баланс кошелька\n"
        "• <code>GET /getExchangeRates</code> - курсы валют\n"
        "• <code>POST /createInvoice</code> - создать инвойс\n"
        "• <code>POST /createCheck</code> - создать чек\n"
        "• <code>POST /transfer</code> - перевод средств\n\n"
        "<b>Webhook:</b>\n"
        "Настройте webhook URL в настройках приложения для получения уведомлений о платежах.\n\n"
        "Нажмите кнопку ниже для просмотра полной документации."
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "api_examples")
async def show_api_examples(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐍 Python", callback_data="example_python")],
        [InlineKeyboardButton(text="📜 JavaScript", callback_data="example_js")],
        [InlineKeyboardButton(text="🌐 cURL", callback_data="example_curl")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="api_docs")]
    ])

    text = (
        "📝 <b>Примеры кода</b>\n\n"
        "Выберите язык программирования для просмотра примеров:"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "example_python")
async def show_python_example(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="api_examples")]
    ])

    text = (
        "🐍 <b>Пример на Python</b>\n\n"
        "<pre><code class=\"language-python\">"
        "import requests\n\n"
        "API_TOKEN = 'your_api_token_here'\n"
        "BASE_URL = 'https://pay.crypt.bot/api'\n\n"
        "headers = {\n"
        "    'Crypto-Pay-API-Token': API_TOKEN,\n"
        "    'Content-Type': 'application/json'\n"
        "}\n\n"
        "# Создать инвойс\n"
        "def create_invoice(asset, amount):\n"
        "    data = {\n"
        "        'asset': asset,\n"
        "        'amount': amount\n"
        "    }\n"
        "    response = requests.post(\n"
        "        f'{BASE_URL}/createInvoice',\n"
        "        json=data,\n"
        "        headers=headers\n"
        "    )\n"
        "    return response.json()\n\n"
        "# Использование\n"
        "invoice = create_invoice('USDT', '10.00')\n"
        "print(invoice)\n"
        "</code></pre>"
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "api_menu")
async def back_to_api_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await cmd_api(callback.message, state)
    await callback.answer()
