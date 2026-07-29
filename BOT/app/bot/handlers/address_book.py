from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import structlog

from app.database import get_async_db
from app.services.auth import auth_service
from app.services.address_book import address_book_service
from app.bot.utils.texts import get_text
from app.utils.exceptions import ValidationError

logger = structlog.get_logger(__name__)
router = Router()


class AddressBookStates(StatesGroup):
    selecting_network = State()
    entering_address = State()
    entering_name = State()
    editing_name = State()


def get_networks_keyboard(address_counts: dict = None, language: str = "ru") -> InlineKeyboardMarkup:
    networks = [
        ("Tron", "TRX"),
        ("The Open Network", "TON"),
        ("Solana", "SOL"),
        ("Bitcoin", "BTC"),
        ("Litecoin", "LTC"),
        ("Ethereum", "ETH"),
        ("BNB Smart Chain", "BNB"),
        ("DOGE", "DOGE")
    ]

    buttons = []
    for display_name, network_code in networks:
        count = address_counts.get(network_code, 0) if address_counts else 0

        button_text = f"{display_name} • {count}" if count > 0 else display_name

        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"ab_network_{network_code}"
        )])

    buttons.append([InlineKeyboardButton(text="◀️ Назад в Кошелек", callback_data="wallet_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_network_addresses_keyboard(entries: List, network: str, language: str = "ru") -> InlineKeyboardMarkup:
    buttons = []

    buttons.append([InlineKeyboardButton(
        text="Добавить адрес",
        callback_data=f"ab_add_{network}"
    )])

    for entry in entries:
        buttons.append([InlineKeyboardButton(
            text=entry.name,
            callback_data=f"ab_entry_{entry.id}"
        )])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="address_book")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_entry_actions_keyboard(entry_id: str, language: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить название", callback_data=f"ab_edit_{entry_id}")],
        [InlineKeyboardButton(text="Удалить адрес", callback_data=f"ab_delete_{entry_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="address_book")]
    ])


def get_back_keyboard(callback_data: str = "address_book", language: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)]
    ])


@router.callback_query(F.data == "address_book")
async def show_address_book(callback: CallbackQuery, state: FSMContext):
    try:
        async for db in get_async_db():
            user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
            if not user:
                await callback.answer("❌ Пользователь не найден")
                return

            address_counts = await address_book_service.get_address_counts_by_network(db, user.id)

            text = ("Здесь вы можете управлять адресной книгой, в которой "
                   "хранятся ваши сохраненные адреса для быстрого вывода монет "
                   "на них.")

            keyboard = get_networks_keyboard(address_counts)

            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            await state.clear()
            break

    except Exception as e:
        logger.error(
            "Address book menu failed",
            user_id=callback.from_user.id,
            error=str(e),
            exc_info=True
        )
        await callback.answer("❌ Произошла ошибка")


@router.callback_query(F.data.startswith("ab_network_"))
async def show_network_addresses(callback: CallbackQuery, state: FSMContext):
    try:
        network = callback.data.split("_", 2)[2]

        async for db in get_async_db():
            user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
            if not user:
                await callback.answer("❌ Пользователь не найден")
                return

            entries = await address_book_service.get_entries_by_network(db, user.id, network)

            network_names = {
                "TRX": "Tron",
                "TON": "The Open Network",
                "SOL": "Solana",
                "BTC": "Bitcoin",
                "LTC": "Litecoin",
                "ETH": "Ethereum",
                "BNB": "BNB Smart Chain",
                "DOGE": "DOGE"
            }

            network_name = network_names.get(network, network)
            text = f"Адресная книга для сети {network_name}."

            keyboard = get_network_addresses_keyboard(entries, network)

            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            break

    except Exception as e:
        logger.error(
            "Show network addresses failed",
            user_id=callback.from_user.id,
            network=callback.data,
            error=str(e),
            exc_info=True
        )
        await callback.answer("❌ Произошла ошибка")


@router.callback_query(F.data.startswith("ab_add_"))
async def start_add_address(callback: CallbackQuery, state: FSMContext):
    try:
        network = callback.data.split("_", 2)[2]

        await state.clear()

        await state.update_data(network=network)
        await state.set_state(AddressBookStates.entering_address)

        logger.info(
            "Start add address debug",
            user_id=callback.from_user.id,
            network=network,
            callback_data=callback.data
        )

        text = "Пришлите адрес для добавления в адресную книгу."
        keyboard = get_back_keyboard("address_book")

        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error(
            "Start add address failed",
            user_id=callback.from_user.id,
            error=str(e),
            exc_info=True
        )
        await callback.answer("❌ Произошла ошибка")


@router.message(AddressBookStates.entering_address)
async def process_address_input(message: Message, state: FSMContext):
    try:
        address = message.text.strip()
        data = await state.get_data()
        network = data.get("network")

        logger.info(
            "Process address input debug",
            user_id=message.from_user.id,
            address=address,
            network=network,
            state_data=data
        )

        if not address:
            await message.answer("❌ Адрес не может быть пустым. Попробуйте еще раз.")
            return

        if len(address) < 10:
            await message.answer("❌ Адрес слишком короткий. Попробуйте еще раз.")
            return

        await state.update_data(address=address)
        await state.set_state(AddressBookStates.entering_name)

        short_address = f"{address[:8]}...{address[-8:]}" if len(address) > 16 else address
        text = f"Пришлите название для адреса {short_address}."

        keyboard = get_back_keyboard("address_book")
        await message.answer(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(
            "Process address input failed",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True
        )
        await message.answer("❌ Произошла ошибка")


@router.message(AddressBookStates.entering_name)
async def process_name_input(message: Message, state: FSMContext):
    try:
        name = message.text.strip()
        data = await state.get_data()
        address = data.get("address")
        network = data.get("network")

        logger.info(
            "Process name input debug",
            user_id=message.from_user.id,
            name=name,
            address=address,
            network=network,
            state_data=data
        )

        if not name:
            await message.answer("❌ Название не может быть пустым. Попробуйте еще раз.")
            return

        if len(name) > 100:
            await message.answer("❌ Название слишком длинное (максимум 100 символов). Попробуйте еще раз.")
            return

        if not address:
            await message.answer("❌ Адрес не найден в состоянии. Пожалуйста, начните добавление адреса заново.")
            await state.clear()
            return

        if not network:
            await message.answer("❌ Сеть не найдена в состоянии. Пожалуйста, начните добавление адреса заново.")
            await state.clear()
            return

        async for db in get_async_db():
            user = await auth_service.get_user_by_telegram_id(db, message.from_user.id)
            if not user:
                await message.answer("❌ Пользователь не найден")
                return

            try:
                entry = await address_book_service.create_entry(
                    db=db,
                    user=user,
                    name=name,
                    address=address,
                    network=network,
                    currency=network
                )

                text = (f"✅ Адрес добавлен в адресную книгу!\n\n"
                       f"📝 Название: {name}\n"
                       f"🌐 Сеть: {network}\n"
                       f"📍 Адрес: `{address}`")

                keyboard = get_back_keyboard("address_book")
                await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
                await state.clear()

            except ValueError as e:
                await message.answer(f"❌ {str(e)}")
            except Exception as e:
                logger.error("❌ Не удалось создать запись в адресной книге", error=str(e))
                await message.answer("❌ Произошла ошибка при сохранении адреса")

            break

    except Exception as e:
        logger.error(
            "Process name input failed",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True
        )
        await message.answer("❌ Произошла ошибка")


@router.callback_query(F.data.startswith("ab_entry_"))
async def show_entry_details(callback: CallbackQuery, state: FSMContext):
    try:
        entry_id = callback.data.split("_", 2)[2]

        async for db in get_async_db():
            user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
            if not user:
                await callback.answer("❌ Пользователь не найден")
                return

            entry = await address_book_service.get_entry_by_id(db, user.id, entry_id)
            if not entry:
                await callback.answer("❌ Запись не найдена")
                return

            text = (f"📝 {entry.name}\n\n"
                   f"Сеть: {entry.network} - {entry.currency}\n"
                   f"Адрес: `{entry.address}`")

            keyboard = get_entry_actions_keyboard(entry_id)

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            await callback.answer()
            break

    except Exception as e:
        logger.error(
            "Show entry details failed",
            user_id=callback.from_user.id,
            entry_id=callback.data,
            error=str(e),
            exc_info=True
        )
        await callback.answer("❌ Произошла ошибка")


@router.callback_query(F.data.startswith("ab_edit_"))
async def start_edit_entry(callback: CallbackQuery, state: FSMContext):
    try:
        entry_id = callback.data.split("_", 2)[2]

        await state.update_data(entry_id=entry_id)
        await state.set_state(AddressBookStates.editing_name)

        text = "Пришлите новое название для адреса."
        keyboard = get_back_keyboard("address_book")

        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error(
            "Start edit entry failed",
            user_id=callback.from_user.id,
            error=str(e),
            exc_info=True
        )
        await callback.answer("❌ Произошла ошибка")


@router.message(AddressBookStates.editing_name)
async def process_edit_name(message: Message, state: FSMContext):
    try:
        name = message.text.strip()
        data = await state.get_data()
        entry_id = data.get("entry_id")

        if not name:
            await message.answer("❌ Название не может быть пустым. Попробуйте еще раз.")
            return

        if len(name) > 100:
            await message.answer("❌ Название слишком длинное (максимум 100 символов). Попробуйте еще раз.")
            return

        async for db in get_async_db():
            user = await auth_service.get_user_by_telegram_id(db, message.from_user.id)
            if not user:
                await message.answer("❌ Пользователь не найден")
                return

            entry = await address_book_service.update_entry(
                db=db,
                user_id=user.id,
                entry_id=entry_id,
                name=name
            )

            if entry:
                text = f"✅ Название изменено на: {name}"
                keyboard = get_back_keyboard("address_book")
                await message.answer(text, reply_markup=keyboard)
                await state.clear()
            else:
                await message.answer("❌ Запись не найдена")

            break

    except Exception as e:
        logger.error(
            "Process edit name failed",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True
        )
        await message.answer("❌ Произошла ошибка")


@router.callback_query(F.data.startswith("ab_delete_"))
async def delete_entry(callback: CallbackQuery, state: FSMContext):
    try:
        entry_id = callback.data.split("_", 2)[2]

        async for db in get_async_db():
            user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
            if not user:
                await callback.answer("❌ Пользователь не найден")
                return

            success = await address_book_service.delete_entry(db, user.id, entry_id)

            if success:
                text = "✅ Адрес удален из адресной книги"
                keyboard = get_back_keyboard("address_book")
                await callback.message.edit_text(text, reply_markup=keyboard)
                await callback.answer("✅ Адрес удален")
            else:
                await callback.answer("❌ Запись не найдена")

            break

    except Exception as e:
        logger.error(
            "Delete entry failed",
            user_id=callback.from_user.id,
            entry_id=callback.data,
            error=str(e),
            exc_info=True
        )
        await callback.answer("❌ Произошла ошибка")
