import qrcode
from io import BytesIO

async def generate_qr_code(url: str) -> BytesIO:
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, format='PNG')
    bio.seek(0)
    return bio
from datetime import datetime
import json
import html
import logging
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQuery, InlineQueryResultArticle, BufferedInputFile,
    InputMediaPhoto, InputMediaAnimation
)
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
import structlog

from app.bot.utils.texts import _
from app.config import settings
from app.services.errors import CheckError, InsufficientFundsError
from app.services.exchange_rates import exchange_rate_service

from app.models.check import Check, CheckStatus, CheckType
from app.bot.keyboards.check_keyboards import (
    get_check_list_keyboard,
    get_check_main_menu_keyboard,
    get_check_view_keyboard,
    get_check_restrictions_keyboard,
    get_subscription_settings_keyboard,
    get_check_actions_keyboard,
    get_currency_selection_keyboard
)
from app.bot.keyboards.inline import get_back_keyboard
from app.database import get_db, AsyncSessionLocal
from app.services.check import check_service
from app.services.auth import auth_service
from app.services.wallet import wallet_service
from app.bot.utils.texts import get_text
from app.services.settings import SettingsService

logger = structlog.get_logger(__name__)

router = Router()
settings_service = SettingsService()


class CheckStates(StatesGroup):
    selecting_type = State()
    selecting_currency = State()
    entering_amount = State()
    entering_activations = State()
    entering_password = State()
    entering_target_user = State()
    entering_expiry = State()
    entering_description = State()
    confirming_creation = State()
    entering_check_id = State()

    entering_activation_password = State()

    gift_creation = State()
    gift_description = State()
    gift_target_user = State()
    gift_delete_confirm = State()

    entering_restriction_password = State()
    binding_user_for_check = State()
    waiting_chat_share_for_check = State()

    uploading_check_image = State()
    waiting_chat_selection = State()
    entering_check_description = State()
    confirming_check_delete = State()


def _load_restrictions(check) -> dict:
    try:
        if hasattr(check, 'restrictions') and check.restrictions:
            data = json.loads(check.restrictions)
        elif hasattr(check, 'extra_data') and check.extra_data:
            data = json.loads(check.extra_data)
        else:
            data = {}
    except Exception:
        data = {}
    defaults = {
        "is_gift": False,
        "password_plain": None,
        "premium_only": False,
        "new_users_only": False,
        "subscription_chat_ids": []
    }
    for k, v in defaults.items():
        if k not in data:
            data[k] = v

    if hasattr(check, 'is_gift') and check.is_gift:
        data["is_gift"] = True

    if not isinstance(data.get("subscription_chat_ids"), list):
        data["subscription_chat_ids"] = []
    return data


async def _save_restrictions(db: AsyncSession, check, restrictions: dict) -> None:
    check.restrictions = json.dumps(restrictions, ensure_ascii=False)
    check.is_gift = restrictions.get("is_gift", False)
    check.image_file_id = restrictions.get("image_file_id")

    if not check.description and restrictions.get("description"):
        check.description = restrictions["description"]

    await db.commit()
    await db.refresh(check)

async def _format_check_info(check: Check, language_code: str = "ru", short_format: bool = False) -> str:
    restrictions = _load_restrictions(check)
    amount_str = f"{check.amount} {check.currency}"

    is_gift = check.is_gift or restrictions.get("is_gift", False)

    if is_gift:
        try:
            local_currency = "KZT"
            rate = await exchange_rate_service.get_exchange_rate(check.currency, local_currency) or 0.0
            amount_fiat = float(check.amount) * float(rate)

            text_parts = [
                f"🎁 <b>Подарок</b>",
                ""
            ]

            if check.target_user_id or check.target_username:
                username = check.target_username or "неизвестный"
                text_parts.append(f"@{username} получит 🪙 <b>{amount_str}</b> ({amount_fiat:.2f} {local_currency}) в виде подарочной 🎁 открытки.")
            else:
                text_parts.append(f"Получатель получит 🪙 <b>{amount_str}</b> ({amount_fiat:.2f} {local_currency}) в виде подарочной 🎁 открытки.")
        except:
            text_parts = [
                f"🎁 <b>Подарок</b>",
                ""
            ]

            if check.target_user_id or check.target_username:
                username = check.target_username or "неизвестный"
                text_parts.append(f"@{username} получит 🪙 <b>{amount_str}</b> в виде подарочной 🎁 открытки.")
            else:
                text_parts.append(f"Получатель получит 🪙 <b>{amount_str}</b> в виде подарочной 🎁 открытки.")

        if check.description:
            text_parts.extend([
                "",
                f"� {check.description}"
            ])

        text_parts.extend([
            "",
            "Получатель увидит сумму, описание и имя отправителя после открытия подарка."
        ])

    else:
        if short_format:
            try:
                local_currency = "KZT"
                rate = await exchange_rate_service.get_exchange_rate(check.currency, local_currency) or 0.0
                amount_fiat = float(check.amount) * float(rate)

                text_parts = [
                    f"<b>Чек</b>",
                    "",
                    f"Сумма: 🪙 <b>{amount_str}</b> ({amount_fiat:.2f} {local_currency})"
                ]
            except:
                text_parts = [
                    f"<b>Чек</b>",
                    "",
                    f"Сумма: 🪙 <b>{amount_str}</b>"
                ]

            if check.description:
                text_parts.extend([
                    "",
                    f"💬 {check.description}"
                ])

            text_parts.extend([
                "",
                "Любой может активировать этот чек.",
                "",
                "Скопируйте ссылку, чтобы поделиться чеком:",
                f"t.me/{getattr(settings, 'bot_username', 'your_bot')}?start=check_{check.check_id}",
                "",
                "⚠️ Никогда не делайте скриншот вашего чека и не отправляйте его никому! Ссылку на чек могут использовать мошенники, чтобы получить доступ к вашим средствам."
            ])
        else:
            text_parts = [
                f"<b>Чек на {amount_str}</b>",
                ""
            ]

            if restrictions.get("bound_user_id") or restrictions.get("bound_username"):
                username = restrictions.get("bound_username", "неизвестный")
                text_parts.append(f"Активировать может: @{username}")
            else:
                text_parts.append("Любой может активировать этот чек")

            restrictions_list = []

            if restrictions.get("premium_only"):
                restrictions_list.append("только Premium")

            if restrictions.get("new_users_only"):
                restrictions_list.append("только новые пользователи")

            if restrictions.get("password"):
                restrictions_list.append("требуется пароль")

            if restrictions.get("subscription_required") and restrictions.get("subscription_chat_ids"):
                num_channels = len(restrictions["subscription_chat_ids"])
                restrictions_list.append(f"требуется подписка на {num_channels} каналов")

            if restrictions_list:
                text_parts.append(
                    f"⚠️ Ограничения: {', '.join(restrictions_list)}"
                )

            if check.description:
                text_parts.extend([
                    "",
                    f"📝 {check.description}"
                ])

            try:
                bot_username = getattr(settings, 'bot_username', 'your_bot')
                deep_link = f"t.me/{bot_username}?start=check_{check.check_id}"
            except:
                deep_link = f"t.me/your_bot?start=check_{check.check_id}"

            text_parts.extend([
                "",
                "<b>Скопируйте ссылку, чтобы поделиться чеком:</b>",
                "",
                f"<tg-spoiler>{deep_link}</tg-spoiler>",
                "",
                "<tg-spoiler><i>⚠️ Никогда не делайте скриншот вашего чека и не отправляйте его никому! "
                "Ссылку на чек могут использовать мошенники, чтобы получить доступ к вашим средствам.</i></tg-spoiler>"
            ])

    return "\n".join(text_parts)

async def _update_check_message(
    message: Message | CallbackQuery,
    check: Check,
    keyboard: InlineKeyboardMarkup | None = None,
    edit: bool = True,
    short_format: bool = False
) -> None:

    text = await _format_check_info(check, short_format=short_format)

    if not keyboard:
        keyboard = get_check_view_keyboard(check)

    if isinstance(message, CallbackQuery):
        message = message.message

    restrictions = _load_restrictions(check)
    image_file_id = check.image_file_id or restrictions.get("image_file_id")
    is_animation = restrictions.get("is_animation", False)

    logger.debug(
        "Update check message logic",
        edit=edit,
        has_text=bool(message.text),
        has_photo=bool(message.photo),
        has_animation=bool(message.animation),
        image_file_id=bool(image_file_id),
        is_animation=is_animation,
        check_id=getattr(check, 'check_id', 'unknown')
    )

    if edit and image_file_id:
        try:
            if is_animation:
                media = InputMediaAnimation(
                    media=image_file_id,
                    caption=text,
                    parse_mode="HTML",
                    show_caption_above_media=True
                )
            else:
                media = InputMediaPhoto(
                    media=image_file_id,
                    caption=text,
                    parse_mode="HTML",
                    show_caption_above_media=True
                )

            await message.edit_media(media=media, reply_markup=keyboard)
            return

        except Exception as e:
            logger.warning(
                "Failed to edit message as media, trying fallback",
                error=str(e),
                check_id=getattr(check, 'check_id', 'unknown')
            )

    if edit and message.text and not image_file_id:
        await message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    elif edit and (message.photo or message.animation) and not image_file_id:
        await message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        if image_file_id:
            if is_animation:
                await message.answer_animation(
                    image_file_id,
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    show_caption_above_media=True
                )
            else:
                await message.answer_photo(
                    image_file_id,
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    show_caption_above_media=True
                )
        else:
            await message.answer(
                text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )


@router.message(Command("check"))
async def check_command(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    await message.answer(
        text=get_text("check_menu", message.from_user.language_code),
        reply_markup=get_check_main_menu_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "check_menu")
async def check_menu_callback(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()
    await callback.message.edit_text(
        text=get_text("check_menu", callback.from_user.language_code),
        reply_markup=get_check_main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "check_list_active")
async def list_active_checks(callback: CallbackQuery, db: AsyncSession) -> None:
    telegram_id = callback.from_user.id

    if db is None:
        await callback.message.edit_text(
            "❌ Ошибка подключения к базе данных. Попробуйте позже.",
            reply_markup=get_check_main_menu_keyboard()
        )
        await callback.answer()
        return

    try:
        user = await auth_service.get_user_by_telegram_id(db, telegram_id)
        if not user:
            await callback.message.edit_text(
                "❌ Пользователь не найден. Пожалуйста, начните сначала с команды /start",
                reply_markup=get_check_main_menu_keyboard()
            )
            await callback.answer()
            return

        user_id = user.id

        query = select(Check).where(
            and_(
                Check.creator_id == user_id,
                Check.status == CheckStatus.ACTIVE.value,
                or_(
                    Check.expires_at.is_(None),
                    Check.expires_at > datetime.utcnow()
                )
            )
        ).order_by(desc(Check.created_at))

        result = await db.execute(query)
        checks = result.scalars().all()

        check_details = [{
            'id': c.id,
            'check_id': c.check_id,
            'status': c.status,
            'created_at': c.created_at.isoformat() if c.created_at else None,
            'expires_at': c.expires_at.isoformat() if c.expires_at else None
        } for c in checks] if checks else []

        logger.info(
            "Active checks query result",
            telegram_id=telegram_id,
            user_id=user_id,
            active_checks_count=len(checks),
            check_details=check_details
        )

        if not checks:
            await callback.message.edit_text(
                "📭 <b>У вас пока нет активных чеков</b>\n\n"
                "Здесь вы можете управлять своими созданными чеками.\n"
                "Чтобы создать новый чек, нажмите «Создать чек»",
                reply_markup=get_check_main_menu_keyboard(),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                "Здесь вы можете управлять своими созданными чеками.",
                reply_markup=get_check_list_keyboard(checks, page=1),
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(
            "Error in list_active_checks",
            telegram_id=telegram_id,
            error=str(e),
            exc_info=True
        )
        await callback.message.edit_text(
            "❌ Произошла ошибка при получении списка чеков. Пожалуйста, попробуйте позже.",
            reply_markup=get_check_main_menu_keyboard()
        )

    await callback.answer()

@router.callback_query(F.data.startswith("check_list_page:"))
async def check_list_page(callback: CallbackQuery, db: AsyncSession):
    page = int(callback.data.split(":")[1])
    telegram_id = callback.from_user.id

    if db is None:
        await callback.message.edit_text(
            "❌ Ошибка подключения к базе данных. Попробуйте позже.",
            reply_markup=get_check_main_menu_keyboard()
        )
        await callback.answer()
        return

    user = await auth_service.get_user_by_telegram_id(db, telegram_id)
    if not user:
        await callback.message.edit_text(
            "❌ Пользователь не найден. Пожалуйста, начните сначала с команды /start",
            reply_markup=get_check_main_menu_keyboard()
        )
        await callback.answer()
        return

    user_id = user.id

    query = select(Check).where(
        and_(
            Check.creator_id == user_id,
            Check.status == CheckStatus.ACTIVE.value,
            or_(
                Check.expires_at.is_(None),
                Check.expires_at > datetime.utcnow()
            )
        )
    ).order_by(Check.created_at.desc())

    result = await db.execute(query)
    checks = result.scalars().all()

    await callback.message.edit_text(
        "Здесь вы можете управлять своими созданными чеками.",
        reply_markup=get_check_list_keyboard(checks, page=page),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("check_view:"))
async def view_check(callback: CallbackQuery, db: AsyncSession):
    if db is None:
        await callback.answer("❌ Ошибка подключения к базе данных. Попробуйте позже.", show_alert=True)
        return

    check_id = callback.data.split(":")[1]

    check = await db.get(Check, check_id)
    if not check:
        await callback.answer("❌ Чек не найден", show_alert=True)
        await list_active_checks(callback, db)
        return

    await db.refresh(check)

    await _update_check_message(callback, check)
    await callback.answer()

@router.callback_query(F.data.startswith("check_show_info:"))
async def show_check_info(callback: CallbackQuery, db: AsyncSession):
    if db is None:
        await callback.answer("❌ Ошибка подключения к базе данных. Попробуйте позже.", show_alert=True)
        return

    check_id = callback.data.split(":")[1]

    check = await db.get(Check, check_id)
    if not check:
        await callback.answer("❌ Чек не найден", show_alert=True)
        return

    deep_link = f"t.me/{settings.bot.username}?start=check_{check.check_id}"

    await callback.answer(
        f"🔗 Ссылка на чек:\n{deep_link}\n\n"
        "⚠️ Внимание! Не делитесь скриншотами чека!",
        show_alert=True
    )

@router.callback_query(F.data.startswith("check_delete:"))
async def confirm_delete_check(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    check_id = callback.data.split(":")[1]

    check = await db.get(Check, check_id)
    if not check:
        await callback.answer("❌ Чек не найден", show_alert=True)
        return

    amount_str = f"{check.amount} {check.currency}"
    restrictions = _load_restrictions(check)

    await state.set_state(CheckStates.confirming_check_delete)
    await state.update_data(check_id=check_id)

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text="Да, удалить",
            callback_data=f"check_delete_confirm:{check_id}"
        ),
        InlineKeyboardButton(
            text="Нет, отмена",
            callback_data=f"check_view:{check_id}"
        )
    )

    text = [
        "⚠️ <b>Подтвердите удаление чека</b>",
        "",
        f"Чек на сумму: {amount_str}"
    ]

    if restrictions.get("is_gift"):
        text.append("Тип: 🎁 Подарочный чек")

    text.extend([
        "",
        "Вы действительно хотите удалить этот чек?",
        "❗️ Это действие нельзя отменить"
    ])

    await callback.message.edit_text(
        "\n".join(text),
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("check_delete_confirm:"))
async def delete_check(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    check_id = callback.data.split(":")[1]

    check = await db.get(Check, check_id)
    if not check:
        await callback.answer("❌ Чек не найден", show_alert=True)
        await state.clear()
        return

    check.status = CheckStatus.CANCELLED
    await db.commit()

    await callback.answer("✅ Чек успешно удален", show_alert=True)
    await state.clear()

    await list_active_checks(callback, db)

@router.callback_query(F.data.startswith("check_add_image:"))
async def request_check_image(callback: CallbackQuery, state: FSMContext):
    check_id = callback.data.split(":")[1]

    await state.set_state(CheckStates.uploading_check_image)
    await state.update_data(check_id=check_id)

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text="« Отмена",
            callback_data=f"check_view_{check_id}"
        )
    )

    await callback.message.answer(
        "Пришлите картинку или GIF для прикрепления к чеку. Эта картинка или GIF будут видны пользователям, когда вы поделитесь чеком.",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(CheckStates.uploading_check_image, F.photo | F.animation)
async def handle_check_image(message: Message, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    check_id = data["check_id"]

    check = await db.get(Check, check_id)
    if not check:
        await message.answer("❌ Чек не найден")
        await state.clear()
        return

    restrictions = _load_restrictions(check)

    if message.photo:
        file_id = message.photo[-1].file_id
        restrictions["is_animation"] = False
    else:
        file_id = message.animation.file_id
        restrictions["is_animation"] = True

    restrictions["image_file_id"] = file_id
    await _save_restrictions(db, check, restrictions)

    text = await _format_check_info(check, short_format=True)
    keyboard = get_check_view_keyboard(check)

    if message.photo:
        await message.answer_photo(
            file_id,
            caption=text,
            reply_markup=keyboard,
            parse_mode="HTML",
            show_caption_above_media=True
        )
    else:
        await message.answer_animation(
            file_id,
            caption=text,
            reply_markup=keyboard,
            parse_mode="HTML",
            show_caption_above_media=True
        )

    await state.clear()

@router.callback_query(F.data.startswith("check_add_description"))
async def request_check_description(callback: CallbackQuery, state: FSMContext):
    if ":" in callback.data:
        check_id = callback.data.split(":")[1]
    else:
        check_id = callback.data.split("_")[-1]

    await state.set_state(CheckStates.entering_check_description)
    await state.update_data(check_id=check_id)

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text="« Отмена",
            callback_data=f"check_view_{check_id}"
        )
    )

    text = "Пришлите описание чека (до 512 символов). Пользователи увидят это описание, когда вы поделитесь чеком."

    await callback.message.answer(
        text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

    await callback.answer()

@router.message(CheckStates.entering_check_description, F.text)
async def handle_check_description(message: Message, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    check_id = data["check_id"]

    check = await db.get(Check, check_id)
    if not check:
        await message.answer("❌ Чек не найден")
        await state.clear()
        return

    restrictions = _load_restrictions(check)
    check.description = message.text
    restrictions["description"] = message.text

    await _save_restrictions(db, check, restrictions)

    await _update_check_message(message, check, edit=False, short_format=True)
    await state.clear()

@router.callback_query(F.data.startswith("check_restrictions:"))
async def show_check_restrictions(callback: CallbackQuery, db: AsyncSession):
    check_id = callback.data.split(":")[1]

    check = await db.get(Check, check_id)
    if not check:
        await callback.answer("❌ Чек не найден", show_alert=True)
        return

    restrictions = _load_restrictions(check)
    await callback.message.edit_text(
        "⚙️ <b>Настройки ограничений</b>\n\n"
        "Здесь вы можете настроить ограничения, которые будут\n"
        "действовать при активации чека. Только пользователи,\n"
        "подходящие по этим ограничениям, смогут активировать чек.",
        reply_markup=get_check_restrictions_keyboard(check, restrictions),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("check_toggle_premium:"))
async def toggle_premium_restriction(callback: CallbackQuery, db: AsyncSession):
    check_id = callback.data.split(":")[1]

    check = await db.get(Check, check_id)
    if not check:
        await callback.answer("❌ Чек не найден", show_alert=True)
        return

    restrictions = _load_restrictions(check)
    restrictions["premium_only"] = not restrictions.get("premium_only", False)

    await _save_restrictions(db, check, restrictions)

    premium_status = "включено" if restrictions["premium_only"] else "выключено"
    await callback.answer(
        f"✅ Ограничение Premium {premium_status}",
        show_alert=True
    )

    await callback.message.edit_reply_markup(
        reply_markup=get_check_restrictions_keyboard(check, _load_restrictions(check))
    )

@router.callback_query(F.data.startswith("check_toggle_new_users:"))
async def toggle_new_users_restriction(callback: CallbackQuery, db: AsyncSession):
    check_id = callback.data.split(":")[1]

    check = await db.get(Check, check_id)
    if not check:
        await callback.answer("❌ Чек не найден", show_alert=True)
        return

    restrictions = _load_restrictions(check)
    restrictions["new_users_only"] = not restrictions.get("new_users_only", False)

    await _save_restrictions(db, check, restrictions)

    new_users_status = "включено" if restrictions["new_users_only"] else "выключено"
    await callback.answer(
        f"✅ Ограничение для новых пользователей {new_users_status}",
        show_alert=True
    )

    await callback.message.edit_reply_markup(
        reply_markup=get_check_restrictions_keyboard(check, _load_restrictions(check))
    )

@router.callback_query(F.data.startswith("check_add_password:"))
async def request_check_password(callback: CallbackQuery, state: FSMContext):
    check_id = callback.data.split(":")[1]

    await state.set_state(CheckStates.entering_restriction_password)
    await state.update_data(check_id=check_id)

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text="« Отмена",
            callback_data=f"check_restrictions:{check_id}"
        )
    )

    await callback.message.edit_text(
        "🔐 <b>Установка пароля</b>\n\n"
        "Введите пароль для активации чека.\n"
        "Чек сможет активировать только тот, кто знает этот пароль.",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(CheckStates.entering_restriction_password, F.text)
async def handle_check_password(message: Message, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    check_id = data["check_id"]

    check = await db.get(Check, check_id)
    if not check:
        await message.answer("❌ Чек не найден")
        await state.clear()
        return

    restrictions = _load_restrictions(check)
    restrictions["password"] = message.text
    await _save_restrictions(db, check, restrictions)

    await message.answer(
        "✅ Пароль успешно установлен",
        reply_markup=get_check_restrictions_keyboard(check, _load_restrictions(check))
    )
    await state.clear()

@router.callback_query(F.data.startswith("check_bind_user:"))
async def request_user_binding(callback: CallbackQuery, state: FSMContext):
    check_id = callback.data.split(":")[1]

    await state.set_state(CheckStates.binding_user_for_check)
    await state.update_data(check_id=check_id)

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text="« Отмена",
            callback_data=f"check_restrictions:{check_id}"
        )
    )

    await callback.message.edit_text(
        "👤 <b>Привязка к пользователю</b>\n\n"
        "Перешлите любое сообщение от пользователя, к которому нужно привязать чек,\n"
        "или введите его @username.\n\n"
        "После привязки только этот пользователь сможет активировать чек.",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(CheckStates.binding_user_for_check, F.text | F.forward_from)
async def handle_user_binding(message: Message, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    check_id = data["check_id"]

    check = await db.get(Check, check_id)
    if not check:
        await message.answer("❌ Чек не найден")
        await state.clear()
        return

    bound_username = None
    bound_user_id = None

    if message.forward_from:
        bound_user_id = message.forward_from.id
        bound_username = message.forward_from.username
    else:
        username = message.text.strip()
        if not username.startswith("@"):
            await message.answer(
                "❌ Неверный формат. Отправьте @username пользователя или перешлите его сообщение"
            )
            return

        bound_username = username[1:]

    restrictions = _load_restrictions(check)
    restrictions["bound_username"] = bound_username
    restrictions["bound_user_id"] = bound_user_id
    await _save_restrictions(db, check, restrictions)

    await message.answer(
        f"✅ Чек привязан к пользователю @{bound_username}",
        reply_markup=get_check_restrictions_keyboard(check, _load_restrictions(check))
    )
    await state.clear()

@router.callback_query(F.data.startswith("check_qr_"))
async def show_check_qr_callback(callback: CallbackQuery, db: AsyncSession, state: FSMContext):
    try:
        check_id = callback.data.split("_", 2)[2]
        user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            await state.clear()
            return
        check = await check_service.get_check_by_id(db, check_id)
        if not check or check.creator_id != user.id:
            await callback.answer("Чек не найден", show_alert=True)
            await state.clear()
            return
        from app.config import settings
        bot_username = settings.bot_username
        check_url = f"https://t.me/{bot_username}?start=activate_check_{check.activation_code}"
        import qrcode
        from io import BytesIO
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(check_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        bio = BytesIO()
        img.save(bio, format='PNG')
        bio.seek(0)
        text = (
            f"QR-код чека\n\n"
            f"Сумма: {check.amount} {check.currency}\n"
            f"Отсканируйте QR-код для активации чека"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Назад к чеку",
                    callback_data=f"check_details_{check_id}"
                )
            ]
        ])
        try:
            await callback.message.delete()
        except Exception as delete_error:
            logger.warning(
                "Failed to delete old message before showing QR",
                error=str(delete_error),
                check_id=check_id
            )

        await callback.message.answer_photo(
            photo=bio,
            caption=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await callback.answer()
        await state.clear()
    except Exception as e:
        logger.error(
            "Failed to show check QR",
            user_id=callback.from_user.id,
            callback_data=callback.data,
            error=str(e),
            exc_info=True
        )
        await callback.answer("Ошибка при генерации QR-кода", show_alert=True)
    restrictions = _load_restrictions(check)
    chat_ids = restrictions.get("subscription_chat_ids", [])

    if len(chat_ids) >= 3:
        await callback.answer(
            "❌ Достигнут лимит каналов/групп (максимум 3)",
            show_alert=True
        )
        return

    chat_id = None
    if callback.data.startswith("check_add_channel:"):
        chat_id = callback.data.split(":")[1]
    elif callback.data.startswith("check_add_group:"):
        chat_id = callback.data.split(":")[1]

    if not chat_id:
        await callback.answer(
            "❌ Неверный формат данных",
            show_alert=True
        )
        return

    try:
        selected_chat = await callback.bot.get_chat(chat_id)
    except Exception as e:
        logger.error(f"Failed to get chat: {e}")
        await callback.answer(
            "❌ Не удалось получить информацию о чате",
            show_alert=True
        )
        return

    chat_member = await callback.bot.get_chat_member(
        chat_id=selected_chat.id,
        user_id=callback.bot.id
    )

    if not chat_member.can_manage_chat:
        await callback.answer(
            "❌ У бота недостаточно прав в канале/группе.\n"
            "Требуется право на управление чатом.",
            show_alert=True
        )
        return

    is_channel = callback.data.startswith("check_add_channel:")
    if is_channel and selected_chat.type != "channel":
        await callback.answer(
            "❌ Выбранный чат не является каналом",
            show_alert=True
        )
        return

    if not is_channel and selected_chat.type != "supergroup":
        await callback.answer(
            "❌ Выбранный чат не является супергруппой",
            show_alert=True
        )
        return

    if selected_chat.id not in chat_ids:
        chat_ids.append(selected_chat.id)
        restrictions["subscription_chat_ids"] = chat_ids
        restrictions["subscription_required"] = True

        await _save_restrictions(db, check, restrictions)

        chat_title = html.quote(selected_chat.title)
        await callback.answer(
            f"✅ Добавлен чат: {chat_title}",
            show_alert=True
        )

    await callback.message.edit_reply_markup(
        reply_markup=get_subscription_settings_keyboard(check)
    )

@router.callback_query(F.data.startswith("check_convert_to_gift:"))
async def convert_to_gift(callback: CallbackQuery, db: AsyncSession):
    check_id = callback.data.split(":")[1]

    check = await db.get(Check, check_id)
    if not check:
        await callback.answer("❌ Чек не найден", show_alert=True)
        return

    restrictions = _load_restrictions(check)

    if restrictions.get("is_gift"):
        await callback.answer(
            "❌ Этот чек уже является подарочным",
            show_alert=True
        )
        return

    restrictions["is_gift"] = True
    await _save_restrictions(db, check, restrictions)

    await callback.answer(
        "✅ Чек успешно преобразован в подарочный",
        show_alert=True
    )

    await _update_check_message(callback, check)

@router.callback_query(F.data.startswith("check_share:"))
async def share_check(callback: CallbackQuery, state: FSMContext):
    check_id = callback.data.split(":")[1]

    await state.set_state(CheckStates.waiting_chat_selection)
    await state.update_data(check_id=check_id)

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text="Выбрать чат для отправки",
            switch_inline_query=f"share_check_{check_id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text="« Отмена",
            callback_data=f"check_view:{check_id}"
        )
    )

    await callback.message.edit_text(
        "📤 <b>Отправка чека</b>\n\n"
        "Нажмите «Выбрать чат» и выберите, куда отправить чек",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("check_show_qr:"))
async def show_qr_code(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    check_id = callback.data.split(":")[1]

    check = await db.get(Check, check_id)
    try:
        if not check:
            await callback.answer("❌ Чек не найден", show_alert=True)
            return

        bot_info = await callback.bot.get_me()
        deep_link = f"t.me/{bot_info.username}?start=check_{check.check_id}"

        qr_image = await generate_qr_code(deep_link)

        text = await _format_check_info(check, short_format=True)

        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(
                text="« Назад",
                callback_data=f"check_view:{check_id}"
            )
        )

        try:
            await callback.message.delete()
        except Exception as delete_error:
            logger.warning(
                "Failed to delete old message before showing QR",
                error=str(delete_error),
                check_id=check_id
            )

        await callback.message.answer_photo(
            BufferedInputFile(qr_image.read(), filename="qr_code.png"),
            caption=text,
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML",
            show_caption_above_media=True
        )
        await callback.answer()
        await state.clear()

    except Exception as e:
        logger.error(
            "Check QR code generation failed",
            user_id=callback.from_user.id,
            error=str(e),
            exc_info=True
        )
        await callback.message.answer(get_text("error_occurred", callback.from_user.language_code))


async def show_check_menu(message: Message, db: AsyncSession, language_code: str = "ru"):
    try:
        keyboard = await get_check_main_menu_keyboard(db, message.from_user.id, language_code)
        text = get_text("check_menu", language_code)

        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logger.error("Show check menu failed", error=str(e))
        await message.answer(get_text("error_occurred", language_code))


@router.callback_query(F.data == "check_menu")
async def callback_check_menu(callback: CallbackQuery, db: AsyncSession):
    try:
        user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        from app.models.check import CheckStatus
        user_checks = await check_service.get_user_checks(db, user.id, status=CheckStatus.ACTIVE, limit=1)
        has_checks = len(user_checks) > 0

        keyboard = get_check_main_menu_keyboard()

        text = (
            "Здесь вы можете создать чек для мгновенной отправки криптовалюты любому пользователю. "
            "Смотреть видеоинструкцию ›"
        )

        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()

    except Exception as e:
        logger.error("Check menu callback failed", error=str(e))
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("check_"))
async def check_callback(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    try:
        action = callback.data.split("_", 1)[1]

        user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer(get_text("user_not_registered", callback.from_user.language_code))
            return

        if action == "create":
            await start_check_creation(callback, state, user, db)
        elif action == "activate":
            await start_check_activation(callback, state, user, db)
        elif action == "list":
            await show_check_list(callback, user, db)
        elif action == "stats":
            await show_check_stats(callback, user, db)
        elif action.startswith("details_"):
            check_id = action.split("_", 1)[1]
            await show_check_details(callback, user, db, check_id)
        elif action.startswith("cancel_"):
            check_id = action.split("_", 1)[1]
            await cancel_check_confirm(callback, user, check_id, db)
        elif action.startswith("create_currency_"):
            currency = action.split("_", 2)[2]
            await start_quick_check_creation(callback, state, user, db, currency)
        elif action == "create_from_chat":
            await show_create_from_chat_info(callback, user, db)
        elif action == "create_new":
            await start_check_creation(callback, state, user, db)
        elif action == "create_gift":
            await state.update_data(activations=1)
            async with AsyncSessionLocal() as db:
                user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
                await create_gift_and_show_screen(callback, state, user, db)
        elif action == "skip_activations":
            await state.update_data(activations=1)
            async with AsyncSessionLocal() as db:
                user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
                await create_check_and_show_screen(callback, state, user, db, check_type=CheckType.ONE_TIME)
        elif action.startswith("max_activations_"):
            max_activations = int(action.split("_", 2)[2])
            await state.update_data(activations=max_activations)
            async with AsyncSessionLocal() as db:
                user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
                await create_gift_and_show_screen(callback, state, user, db)
        elif action == "change_amount":
            data = await state.get_data()
            currency = data.get("currency", "")
            await state.set_state(CheckStates.entering_amount)
            await show_amount_input_screen(callback, state, currency)
        elif action == "add_description":
            await state.set_state(CheckStates.gift_description)
            text = (
                "Пришлите описание чека (до 512 символов). Пользователи увидят это описание, когда вы поделитесь чеком."
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад к чеку", callback_data="check_back_to_gift")]
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
        elif action == "pin_user":
            await state.set_state(CheckStates.gift_target_user)
            text = (
                "Пришлите @username или перешлите сообщение пользователя, за которым вы хотите закрепить чек."
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад к чеку", callback_data="check_back_to_gift")]
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
        elif action == "delete_gift":
            await state.set_state(CheckStates.gift_delete_confirm)
            text = "❌ Вы уверены, что хотите удалить этот чек?"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Да", callback_data="check_confirm_delete")],
                [InlineKeyboardButton(text="Нет", callback_data="check_back_to_gift")]
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
        elif action == "remove_description":
            await state.update_data(gift_description=None)

            data = await state.get_data()
            gift_activation_code = data.get("gift_activation_code")

            if gift_activation_code:
                check = await check_service.get_check_by_activation_code(db, gift_activation_code)
                if check:
                    check.description = None
                    await db.commit()

            await show_gift_creation_screen(callback, state)
        elif action == "unpin_user":
            await state.update_data(gift_target_user=None)

            data = await state.get_data()
            gift_activation_code = data.get("gift_activation_code")

            if gift_activation_code:
                check = await check_service.get_check_by_activation_code(db, gift_activation_code)
                if check:
                    check.target_user_id = None
                    check.target_username = None
                    check.type = CheckType.ONE_TIME.value
                    await db.commit()

            await show_gift_creation_screen(callback, state)
        elif action == "back_to_gift":
            await show_gift_creation_screen(callback, state)
        elif action == "confirm_delete":
            await state.clear()
            await callback.message.edit_text("✅ Подарок удален")
        elif action.startswith("set_min_"):
            min_amount = action.split("_", 2)[2]
            await state.update_data(amount=min_amount)

            async with AsyncSessionLocal() as db:
                user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
                data = await state.get_data()
                currency = data.get("currency")
                wallet = await wallet_service.get_user_wallet(db, user.id, currency)
                balance = float(wallet.available_balance)
                amount_float = float(min_amount)
                max_activations = int(balance // amount_float) if amount_float > 0 else 1

                if max_activations < 2:
                    await state.update_data(activations=1)
                    await create_check_and_show_screen(callback, state, user, db, check_type=CheckType.ONE_TIME)
                    return
                else:
                    await state.set_state(CheckStates.entering_activations)
                    await show_activations_screen(callback, state)

        elif action.startswith("set_max_"):
            max_amount = action.split("_", 2)[2]
            await state.update_data(amount=max_amount)

            async with AsyncSessionLocal() as db:
                user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
                data = await state.get_data()
                currency = data.get("currency")
                wallet = await wallet_service.get_user_wallet(db, user.id, currency)
                balance = float(wallet.available_balance)
                amount_float = float(max_amount)
                max_activations = int(balance // amount_float) if amount_float > 0 else 1

                if max_activations < 2:
                    await state.update_data(activations=1)
                    await create_check_and_show_screen(callback, state, user, db, check_type=CheckType.ONE_TIME)
                    return
                else:
                    await state.set_state(CheckStates.entering_activations)
                    await show_activations_screen(callback, state)

        await callback.answer()

    except Exception as e:
        logger.error(
            "Check callback failed",
            user_id=callback.from_user.id,
            action=callback.data,
            error=str(e),
            exc_info=True
        )
        await callback.answer(get_text("error_occurred", callback.from_user.language_code))


async def start_check_creation(callback: CallbackQuery, state: FSMContext, user, db: AsyncSession):
    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

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
                    callback_data=f"check_create_currency_{currency}"
                )
                for currency in row_currencies
            ]
            builder.row(*buttons)

        builder.row(
            InlineKeyboardButton(
                text="« Назад к чекам",
                callback_data="check_menu"
            )
        )

        text = "Выберите криптовалюту для создания чека"

        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup()
        )
        await state.set_state(CheckStates.selecting_currency)

    except Exception as e:
        logger.error(
            "Start check creation failed",
            user_id=callback.from_user.id,
            error=str(e),
            exc_info=True
        )
        raise


@router.callback_query(F.data.startswith("check_type_"))
async def select_check_type(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    try:
        check_type = callback.data.split("_", 2)[2]

        await state.update_data(check_type=check_type)

        keyboard = get_currency_selection_keyboard(
            callback_prefix="check_currency",
            language_code=callback.from_user.language_code
        )
        text = get_text("select_currency_for_check", callback.from_user.language_code)

        await callback.message.edit_text(text, reply_markup=keyboard)
        await state.set_state(CheckStates.selecting_currency)

    except Exception as e:
        logger.error(
            "Select check type failed",
            user_id=callback.from_user.id,
            error=str(e),
            exc_info=True
        )
        await callback.answer(get_text("error_occurred", callback.from_user.language_code))


@router.callback_query(F.data.startswith("check_currency_"))
async def select_check_currency(callback: CallbackQuery, state: FSMContext):
    try:
        currency = callback.data.split("_", 2)[2]

        await state.update_data(currency=currency)
        await show_amount_input_screen(callback, state, currency)

    except Exception as e:
        logger.error(
            "Select check currency failed",
            user_id=callback.from_user.id,
            error=str(e),
            exc_info=True
        )
        await callback.answer(get_text("error_occurred", callback.from_user.language_code))


async def show_amount_input_screen(callback_or_message: CallbackQuery | Message, state: FSMContext, currency: str):
    try:
        async with AsyncSessionLocal() as db:
            user = await auth_service.get_user_by_telegram_id(db, callback_or_message.from_user.id)
            wallet = await wallet_service.get_user_wallet(db, user.id, currency) if user else None
            balance = float(wallet.available_balance) if wallet else 0.0
            user_settings = await settings_service.get_or_create_user_settings(db, user.id)
            local_currency = user_settings.local_currency or "KZT"
        rate_fiat = await exchange_rate_service.get_exchange_rate(currency, local_currency) or 0.0
        balance_fiat = balance * float(rate_fiat)
        text = (
            f"Пришлите сумму чека в {currency}. Если вы хотите создать мультичек, "
            f"введите кратную вашему балансу сумму одной активации.\n\n"
            f"Ваш баланс: {balance:.6f} {currency}"
        )

        min_display = 0.02
        max_display = balance
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Мин. · {min_display:.2f} {currency}", callback_data=f"check_set_min_{min_display}")],
            [InlineKeyboardButton(text=f"Макс. · {max_display:.6f} {currency}", callback_data=f"check_set_max_{max_display}")],
            [InlineKeyboardButton(text="‹ Изменить монету", callback_data="check_create_new")]
        ])
        await state.set_state(CheckStates.entering_amount)
        if isinstance(callback_or_message, CallbackQuery):
            await callback_or_message.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await callback_or_message.answer()
        else:
            await callback_or_message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error("Show amount input screen failed", error=str(e), exc_info=True)


@router.message(CheckStates.entering_amount)
async def process_check_amount(message: Message, state: FSMContext):
    try:
        amount = message.text.strip()


        try:
            amount_float = float(amount)
            if amount_float <= 0:
                await message.answer("❌ Неверная сумма. Введите положительное число.")
                return

            data = await state.get_data()
            currency = data.get("currency")
            async with AsyncSessionLocal() as db:
                user = await auth_service.get_user_by_telegram_id(db, message.from_user.id)
                wallet = await wallet_service.get_user_wallet(db, user.id, currency)
                balance = float(wallet.available_balance)
                if amount_float > balance:
                    await message.answer(
                        f"Недостаточно средств для создания чека в {currency}. "
                        "Пожалуйста, пополните баланс."
                    )
                    return
        except ValueError:
            await message.answer("❌ Неверная сумма. Введите положительное число.")
            return
        except Exception as e:
            logger.error("Failed to validate check amount", error=str(e))
            await message.answer("❌ Произошла ошибка при валидации суммы чека.")
            return
        await state.update_data(amount=amount)
        await state.set_state(CheckStates.entering_activations)

        data = await state.get_data()
        currency = data.get("currency")

        max_activations = 1
        try:
            async with AsyncSessionLocal() as db:
                user = await auth_service.get_user_by_telegram_id(db, message.from_user.id)
                if user:
                    wallet = await wallet_service.get_user_wallet(db, user.id, currency)
                    if wallet:
                        balance = float(wallet.available_balance)
                        amount_float = float(amount)
                        if amount_float > 0:
                            max_activations = int(balance // amount_float)
        except Exception:
            max_activations = 1

        if max_activations < 1:
            max_activations = 1

        await state.update_data(max_activations=max_activations)

        if max_activations < 2:
            await state.update_data(activations=1)
            async with AsyncSessionLocal() as db:
                user = await auth_service.get_user_by_telegram_id(db, message.from_user.id)
                await create_check_and_show_screen(message, state, user, db, check_type=CheckType.ONE_TIME)
            return

        activations_text = (
            "Пришлите количество активаций, чтобы создать мультичек (до {max_count} активаций)."
            .format(max_count=max_activations)
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Создать подарок", callback_data="check_create_gift")],
            [InlineKeyboardButton(text="Пропустить ›", callback_data="check_skip_activations")],
            [InlineKeyboardButton(text=f"Макс. кол-во · {max_activations}", callback_data=f"check_max_activations_{max_activations}")],
            [InlineKeyboardButton(text="‹ Изменить сумму", callback_data="check_change_amount")]
        ])
        await message.answer(activations_text, reply_markup=keyboard)

    except Exception as e:
        logger.error(
            "Process check amount failed",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True
        )
        await message.answer("❌ Произошла ошибка")


@router.message(CheckStates.entering_activations)
async def process_check_activations(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        max_activations = int(data.get("max_activations", 1))

        text_value = message.text.strip()
        try:
            activations = int(text_value)
            if activations < 1:
                activations = 1
            if activations > max_activations:
                activations = max_activations
        except ValueError:
            activations = 1

        await state.update_data(activations=activations)
        await state.set_state(CheckStates.entering_password)

        text = (
            "🔐 Пароль для чека (опционально)\n\n"
            "Введите пароль для защиты чека или отправьте \"-\" чтобы пропустить:"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« Назад", callback_data="check_menu")]])
        await message.answer(text, reply_markup=keyboard)
    except Exception as e:
        logger.error("Process check activations failed", user_id=message.from_user.id, error=str(e), exc_info=True)
        await message.answer("❌ Произошла ошибка")


async def _send_gift_screen_message(message, state: FSMContext):
    try:
        data = await state.get_data()
        currency = data.get("currency")
        amount = data.get("amount")
        gift_description = data.get("gift_description")
        gift_target_user = data.get("gift_target_user")
        gift_activation_code = data.get("gift_activation_code")
        check_id = data.get("check_id")

        async with AsyncSessionLocal() as db:
            user = await auth_service.get_user_by_telegram_id(db, message.from_user.id)
            user_settings = await settings_service.get_or_create_user_settings(db, user.id)
            local_currency = user_settings.local_currency or "KZT"

        rate_fiat = await exchange_rate_service.get_exchange_rate(currency, local_currency) or 0.0
        amount_fiat = float(amount) * float(rate_fiat)

        if gift_target_user:
            recipient_text = f"@{gift_target_user} получит"
        else:
            recipient_text = "Получатель получит"

        text = f"🎁 Подарок\n\n{recipient_text} 🪙 {amount} {currency} ({amount_fiat:.2f} {local_currency}) в виде подарочной 🎁 открытки."

        if gift_description:
            text += f"\n\n💬 {gift_description}"

        if gift_description and gift_target_user:
            text += "\n\nПолучатель увидит сумму, описание и имя отправителя после открытия подарка."
        elif gift_description:
            text += "\n\nПолучатель увидит сумму, описание и имя отправителя после открытия подарка."
        elif gift_target_user:
            text += "\n\nПолучатель увидит сумму и имя отправителя после открытия подарка."
        else:
            text += "\n\nПолучатель увидит сумму и имя отправителя после открытия подарка."

        buttons = []

        buttons.append([InlineKeyboardButton(text="🎁 Отправить подарок", switch_inline_query=f"gift_{gift_activation_code}")])

        if gift_description:
            buttons.append([InlineKeyboardButton(text="Убрать описание", callback_data=f"check_remove_description:{check_id}")])
        else:
            buttons.append([InlineKeyboardButton(text="Добавить описание", callback_data=f"check_add_description:{check_id}")])

        if gift_target_user:
            buttons.append([InlineKeyboardButton(text="Открепить от пользователя", callback_data="check_unpin_user")])
        else:
            buttons.append([InlineKeyboardButton(text="Закрепить за пользователем", callback_data="check_pin_user")])

        buttons.append([InlineKeyboardButton(text="Удалить подарок", callback_data="check_delete_gift")])
        buttons.append([InlineKeyboardButton(text="‹ Назад к списку чеков", callback_data="check_list")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await state.set_state(CheckStates.gift_creation)
        await message.answer(text, reply_markup=keyboard)

    except Exception as e:
        logger.error("Send gift screen message failed", error=str(e), exc_info=True)
        await message.answer("❌ Произошла ошибка")

async def show_gift_creation_screen(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        currency = data.get("currency")
        amount = data.get("amount")
        activations = data.get("activations", 1)
        gift_activation_code = data.get("gift_activation_code")
        gift_description = data.get("gift_description")
        gift_target_user = data.get("gift_target_user")
        check_id = data.get("check_id")

        if not gift_activation_code:
            async with AsyncSessionLocal() as db:
                user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
                if not user:
                    await callback.answer("❌ Пользователь не найден", show_alert=True)
                    return

                check = await check_service.create_check(
                    db=db,
                    creator=user,
                    currency=currency,
                    amount=amount,
                    check_type=(CheckType.MULTI_USE if activations > 1 else CheckType.ONE_TIME),
                    password=None,
                    max_activations=(activations if activations > 1 else None),
                    description=None
                )

                logger.info("Gift check created",
                           check_id=check.check_id,
                           activation_code=check.activation_code,
                           activation_code_type=type(check.activation_code))

                await state.update_data(gift_activation_code=check.activation_code, check_id=check.check_id)
                gift_activation_code = check.activation_code

        async with AsyncSessionLocal() as db:
            user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
            user_settings = await settings_service.get_or_create_user_settings(db, user.id)
            local_currency = user_settings.local_currency or "KZT"

        rate_fiat = await exchange_rate_service.get_exchange_rate(currency, local_currency) or 0.0
        amount_fiat = float(amount) * float(rate_fiat)

        if gift_target_user:
            recipient_text = f"@{gift_target_user} получит"
        else:
            recipient_text = "Получатель получит"

        text = f"🎁 Подарок\n\n{recipient_text} 🪙 {amount} {currency} ({amount_fiat:.2f} {local_currency}) в виде подарочной 🎁 открытки."

        if gift_description:
            text += f"\n\n💬 {gift_description}"

        if gift_description and gift_target_user:
            text += "\n\nПолучатель увидит сумму, описание и имя отправителя после открытия подарка."
        elif gift_description:
            text += "\n\nПолучатель увидит сумму, описание и имя отправителя после открытия подарка."
        elif gift_target_user:
            text += "\n\nПолучатель увидит сумму и имя отправителя после открытия подарка."
        else:
            text += "\n\nПолучатель увидит сумму и имя отправителя после открытия подарка."

        buttons = []

        buttons.append([InlineKeyboardButton(text="🎁 Отправить подарок", switch_inline_query=f"gift_{gift_activation_code}")])

        if gift_description:
            buttons.append([InlineKeyboardButton(text="Убрать описание", callback_data=f"check_remove_description:{check_id}")])
        else:
            buttons.append([InlineKeyboardButton(text="Добавить описание", callback_data=f"check_add_description:{check_id}")])

        if gift_target_user:
            buttons.append([InlineKeyboardButton(text="Открепить от пользователя", callback_data=f"check_unpin_user:{check_id}")])
        else:
            buttons.append([InlineKeyboardButton(text="Закрепить за пользователем", callback_data=f"check_pin_user:{check_id}")])

        buttons.append([InlineKeyboardButton(text="Удалить подарок", callback_data=f"check_delete_gift:{check_id}")])
        buttons.append([InlineKeyboardButton(text="‹ Назад к списку чеков", callback_data="check_list")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await state.set_state(CheckStates.gift_creation)
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error("Show gift creation screen failed", error=str(e), exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


async def show_activations_screen(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        currency = data.get("currency")
        amount = float(data.get("amount"))

        async with AsyncSessionLocal() as db:
            user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
            wallet = await wallet_service.get_user_wallet(db, user.id, currency) if user else None
            balance = float(wallet.available_balance) if wallet else 0.0

        max_activations = int(balance // amount) if amount > 0 else 1
        if max_activations < 1:
            max_activations = 1

        await state.update_data(max_activations=max_activations)

        activations_text = (
            f"Пришлите количество активаций, чтобы создать мультичек (до {max_activations} активаций)."
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Создать подарок", callback_data="check_create_gift")],
            [InlineKeyboardButton(text="Пропустить ›", callback_data="check_skip_activations")],
            [InlineKeyboardButton(text=f"Макс. кол-во · {max_activations}", callback_data=f"check_max_activations_{max_activations}")],
            [InlineKeyboardButton(text="‹ Изменить сумму", callback_data="check_change_amount")]
        ])

        await callback.message.edit_text(activations_text, reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error("Show activations screen failed", error=str(e), exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


async def create_check_and_show_screen(message_or_callback, state: FSMContext, user, db: AsyncSession, check_type: CheckType):
    try:
        data = await state.get_data()
        currency = data.get("currency")
        amount = data.get("amount")
        activations = data.get("activations", 1)

        logger.info(
            "Creating check",
            activations=activations,
            amount=amount,
            currency=currency,
            user_id=user.id
        )

        check = await check_service.create_check(
            db=db,
            creator=user,
            currency=currency,
            amount=amount,
            check_type=check_type,
            max_activations=1 if check_type == CheckType.ONE_TIME else activations
        )

        logger.info(
            "Check created successfully",
            check_id=check.check_id,
            activation_code=check.activation_code,
            activation_code_type=type(check.activation_code)
        )

        text = await _format_check_info(check, getattr(message_or_callback.from_user, 'language_code', 'ru'), short_format=False)

        restrictions = _load_restrictions(check)
        has_image = bool(check.image_file_id or restrictions.get("image_file_id"))
        has_description = bool(restrictions.get("description"))

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Конвертировать в подарок", callback_data=f"check_convert_gift_{check.check_id}")],
            [InlineKeyboardButton(text="Поделиться чеком", callback_data=f"check_share_{check.check_id}")],
            [InlineKeyboardButton(text="Показать QR-код", callback_data=f"check_qr_{check.check_id}")],
            [InlineKeyboardButton(text="Удалить описание" if has_description else "Добавить описание", callback_data=f"check_remove_description:{check.check_id}" if has_description else f"check_add_description:{check.check_id}")],
            [InlineKeyboardButton(text="Удалить картинку" if has_image else "Добавить картинку", callback_data=f"check_remove_image:{check.check_id}" if has_image else f"check_add_image:{check.check_id}")],
            [InlineKeyboardButton(text="Ограничения", callback_data=f"check_restrictions:{check.check_id}")],
            [InlineKeyboardButton(text="Удалить чек", callback_data=f"check_delete:{check.check_id}")],
            [InlineKeyboardButton(text="‹ Назад к списку чеков", callback_data="check_list")]
        ])

        await _update_check_message(message_or_callback, check, keyboard, edit=hasattr(message_or_callback, 'message'))

        if hasattr(message_or_callback, 'message'):
            await message_or_callback.answer()

    except Exception as e:
        logger.error("Create check failed", error=str(e))
        if hasattr(message_or_callback, 'message'):
            await message_or_callback.answer("❌ Произошла ошибка при создании чека", show_alert=True)
        else:
            await message_or_callback.answer("❌ Произошла ошибка при создании чека")


async def create_gift_and_show_screen(callback: CallbackQuery, state: FSMContext, user, db: AsyncSession):
    try:
        data = await state.get_data()
        currency = data.get("currency")
        amount = data.get("amount")
        activations = data.get("activations", 1)
        description = data.get("gift_description")
        target_user = data.get("gift_target_user")
        logger.info("Creating gift check",
                   currency=currency,
                   amount=amount,
                   activations=activations,
                   user_id=user.id)

        check = await check_service.create_check(
            db=db,
            creator=user,
            currency=currency,
            amount=amount,
            check_type=(CheckType.MULTI_USE if activations > 1 else CheckType.ONE_TIME),
            password=None,
            max_activations=(activations if activations > 1 else None),
            description=description
        )

        restrictions = {"is_gift": True}

        if target_user:
            target_user_obj = await auth_service.get_user_by_username(db, target_user)
            if target_user_obj:
                check.target_user_id = target_user_obj.id
                check.target_username = target_user
                check.type = CheckType.PERSONAL.value
                restrictions["bound_username"] = target_user
                restrictions["bound_user_id"] = target_user_obj.id

        await _save_restrictions(db, check, restrictions)

        logger.info("Gift check created successfully",
                   check_id=check.check_id,
                   activation_code=check.activation_code,
                   activation_code_type=type(check.activation_code))

        await state.update_data(gift_activation_code=check.activation_code)

        user_settings = await settings_service.get_or_create_user_settings(db, user.id)
        local_currency = user_settings.local_currency or "KZT"

        rate_fiat = await exchange_rate_service.get_exchange_rate(currency, local_currency) or 0.0
        amount_fiat = float(amount) * float(rate_fiat)

        if description:
            text = (
                f"🎁 Подарок\n\n"
                f"Получатель получит 🪙 {amount} {currency} ({amount_fiat:,.2f} {local_currency}) в виде подарочной 🎁 открытки.\n\n"
                f"{description}\n\n"
                f"Получатель увидит сумму, описание и имя отправителя после открытия подарка."
            )
        else:
            text = (
                f"🎁 Подарок\n\n"
                f"Получатель получит 🪙 {amount} {currency} ({amount_fiat:,.2f} {local_currency}) в виде подарочной 🎁 открытки.\n\n"
                f"Получатель увидит сумму и имя отправителя после открытия подарка."
            )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Отправить подарок", switch_inline_query=f"gift_{check.activation_code}")],
            [InlineKeyboardButton(text="Добавить описание", callback_data="check_add_description")],
            [InlineKeyboardButton(text="Закрепить за пользователем", callback_data="check_pin_user")],
            [InlineKeyboardButton(text="Удалить подарок", callback_data="check_delete_gift")],
            [InlineKeyboardButton(text="‹ Назад к списку чеков", callback_data="check_list")]
        ])

        await state.set_state(CheckStates.gift_creation)
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error("Create gift and show screen failed", error=str(e), exc_info=True)
        await callback.answer("❌ Произошла ошибка при создании подарка", show_alert=True)


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()


@router.message(CheckStates.gift_description)
async def process_gift_description(message: Message, state: FSMContext):
    try:
        description = message.text.strip()
        if len(description) > 512:
            await message.answer("❌ Описание слишком длинное. Максимум 512 символов.")
            return

        await state.update_data(gift_description=description)

        data = await state.get_data()
        gift_activation_code = data.get("gift_activation_code")

        if gift_activation_code:
            async with AsyncSessionLocal() as db_session:
                check = await check_service.get_check_by_activation_code(db_session, gift_activation_code)
                if check:
                    check.description = description
                    await db_session.commit()

        await _send_gift_screen_message(message, state)

    except Exception as e:
        logger.error("Process gift description failed", error=str(e), exc_info=True)
        await message.answer("❌ Произошла ошибка")


@router.message(CheckStates.gift_target_user)
async def process_gift_target_user(message: Message, state: FSMContext, db: AsyncSession):
    try:
        username = message.text.strip().replace("@", "")

        target_user = await auth_service.get_user_by_username(db, username)
        if not target_user:
            await message.answer(f"❌ Пользователь @{username} не найден")
            return

        await state.update_data(gift_target_user=username)

        data = await state.get_data()
        gift_activation_code = data.get("gift_activation_code")

        if gift_activation_code:
            check = await check_service.get_check_by_activation_code(db, gift_activation_code)
            if check:
                check.target_user_id = target_user.id
                check.target_username = username
                check.type = CheckType.PERSONAL.value
                await db.commit()

        await _send_gift_screen_message(message, state)

    except Exception as e:
        logger.error("Process gift target user failed", error=str(e), exc_info=True)
        await message.answer("❌ Произошла ошибка")


@router.message(CheckStates.entering_target_user)
async def process_target_user(message: Message, state: FSMContext, db: AsyncSession):
    try:
        username = message.text.strip().replace("@", "")

        target_user = await auth_service.get_user_by_username(db, username)
        if not target_user:
            await message.answer(
                get_text("user_not_found", message.from_user.language_code).format(
                    username=username
                )
            )
            return

        await state.update_data(target_username=username)
        await state.set_state(CheckStates.entering_password)

        text = get_text("enter_check_password_optional", message.from_user.language_code)
        keyboard = get_back_keyboard("check_create", message.from_user.language_code)
        await message.answer(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(
            "Process target user failed",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True
        )
        await message.answer(get_text("error_occurred", message.from_user.language_code))


@router.message(CheckStates.entering_password)
async def process_check_password(message: Message, state: FSMContext):
    try:
        password = message.text.strip() if message.text.strip() != "-" else None

        data = await state.get_data()
        currency = data.get("currency")
        amount = data.get("amount")
        activations = int(data.get("activations", 1))

        async with AsyncSessionLocal() as db:
            user = await auth_service.get_user_by_telegram_id(db, message.from_user.id)
            if not user:
                await message.answer("❌ Пользователь не найден")
                return

            check = await check_service.create_check(
                db=db,
                creator=user,
                currency=currency,
                amount=amount,
                check_type=(CheckType.MULTI_USE if activations > 1 else CheckType.ONE_TIME),
                password=password,
                max_activations=(activations if activations > 1 else None),
                description=f"Чек создан через бота"
            )

            from app.config import settings
            bot_username = settings.bot_username
            check_url = f"https://t.me/{bot_username}?start=activate_check_{check.activation_code}"

            text = (
                f"✅ Чек создан успешно!\n\n"
                f"🎫 ID: {check.check_id}\n"
                f"💰 Сумма: {amount} {currency}\n"
                f"🔗 Ссылка: {check_url}"
            )

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🎫 Мои чеки",
                        callback_data="check_list"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="« Назад к чекам",
                        callback_data="check_menu"
                    )
                ]
            ])

            await message.answer(text, reply_markup=keyboard)
            await state.clear()

    except Exception as e:
        logger.error(
            "Process check password failed",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True
        )
        await message.answer("❌ Произошла ошибка при создании чека")


@router.message(CheckStates.entering_expiry)
async def process_check_expiry(message: Message, state: FSMContext):
    try:
        expiry_text = message.text.strip()
        expires_in_hours = None

        if expiry_text != "-":
            try:
                expires_in_hours = int(expiry_text)
                if expires_in_hours <= 0 or expires_in_hours > 720:
                    raise ValueError()
            except ValueError:
                await message.answer(
                    get_text("invalid_expiry", message.from_user.language_code)
                )
                return

        await state.update_data(expires_in_hours=expires_in_hours)
        await state.set_state(CheckStates.entering_description)

        text = get_text("enter_check_description_optional", message.from_user.language_code)
        keyboard = get_back_keyboard("check_create", message.from_user.language_code)
        await message.answer(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(
            "Process check expiry failed",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True
        )
        await message.answer(get_text("error_occurred", message.from_user.language_code))


@router.message(CheckStates.entering_description)
async def process_check_description(message: Message, state: FSMContext, db: AsyncSession):
    try:
        description = message.text.strip() if message.text.strip() != "-" else None

        data = await state.get_data()
        check_type = data.get("check_type")
        currency = data.get("currency")
        amount = data.get("amount")
        password = data.get("password")
        target_username = data.get("target_username")
        expires_in_hours = data.get("expires_in_hours")

        user = await auth_service.get_user_by_telegram_id(db, message.from_user.id)
        if not user:
            await message.answer(get_text("user_not_registered", message.from_user.language_code))
            return

        check = await check_service.create_check(
            db=db,
            creator=user,
            currency=currency,
            amount=amount,
            check_type=CheckType(check_type),
            password=password,
            target_user_id=None,
            expires_in_hours=expires_in_hours,
            description=description
        )

        text = get_text("check_created", message.from_user.language_code).format(
            check_id=check.check_id,
            amount=check.amount,
            currency=check.currency,
            type=check.type,
            expires_at=check.expires_at.strftime("%d.%m.%Y %H:%M") if check.expires_at else "Не ограничен"
        )

        bot_username = getattr(settings, 'bot_username', 'your_bot')
        check_url = f"https://t.me/{bot_username}?start={check.activation_code}"
        text += f"\n\n🔗 Ссылка для активации:\n{check_url}"

        keyboard = get_check_actions_keyboard(
            check_id=check.check_id,
            language_code=message.from_user.language_code
        )

        await message.answer(text, reply_markup=keyboard)
        await state.clear()

    except InsufficientFundsError as e:
        await message.answer(str(e))
    except CheckError as e:
        await message.answer(str(e))
    except Exception as e:
        logger.error(
            "Process check description failed",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True
        )
        await message.answer(get_text("error_occurred", message.from_user.language_code))


async def start_check_activation(callback: CallbackQuery, state: FSMContext, user, db: AsyncSession):
    try:
        await state.set_state(CheckStates.entering_check_id)

        text = get_text("enter_check_id", callback.from_user.language_code)
        keyboard = get_back_keyboard("check_menu", callback.from_user.language_code)

        await callback.message.edit_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(
            "Start check activation failed",
            user_id=callback.from_user.id,
            error=str(e),
            exc_info=True
        )
        raise


@router.message(CheckStates.entering_check_id)
async def process_check_id(message: Message, state: FSMContext, db: AsyncSession):
    try:
        check_id = message.text.strip().upper()

        if len(check_id) != 8 or not check_id.isalnum():
            await message.answer(get_text("invalid_check_id", message.from_user.language_code))
            return

        check = await check_service.get_check_by_id(db, check_id)
        if not check:
            await message.answer(get_text("check_not_found", message.from_user.language_code))
            return

        user = await auth_service.get_user_by_telegram_id(db, message.from_user.id)
        if not user:
            await message.answer(get_text("user_not_registered", message.from_user.language_code))
            return

        if not check.can_be_activated_by(user.id, user.username):
            if check.creator_id == user.id:
                reason = get_text("cannot_activate_own_check", message.from_user.language_code)
            elif check.status != CheckStatus.ACTIVE:
                reason = get_text("check_not_active", message.from_user.language_code).format(
                    status=check.status
                )
            elif check.is_expired:
                reason = get_text("check_expired", message.from_user.language_code)
            else:
                reason = get_text("check_cannot_activate", message.from_user.language_code)

            await message.answer(reason)
            return

        await state.update_data(activation_code=check.activation_code)

        if check.password:
            await state.set_state(CheckStates.entering_activation_password)
            text = get_text("enter_activation_password", message.from_user.language_code)
            keyboard = get_back_keyboard("check_activate", message.from_user.language_code)
            await message.answer(text, reply_markup=keyboard)
        else:
            await activate_check_final(message, state, user, db, check.activation_code, None)

    except Exception as e:
        logger.error(
            "Process check ID failed",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True
        )
        await message.answer(get_text("error_occurred", message.from_user.language_code))


@router.message(CheckStates.entering_activation_password)
async def process_activation_password(message: Message, state: FSMContext, db: AsyncSession):
    try:
        password = message.text.strip()
        data = await state.get_data()
        activation_code = data.get("activation_code")

        user = await auth_service.get_user_by_telegram_id(db, message.from_user.id)
        if not user:
            await message.answer(get_text("user_not_registered", message.from_user.language_code))
            return

        await activate_check_final(message, state, user, db, activation_code, password)

    except Exception as e:
        logger.error(
            "Process activation password failed",
            user_id=message.from_user.id,
            error=str(e),
            exc_info=True
        )
        await message.answer(get_text("error_occurred", message.from_user.language_code))


async def activate_check_final(message: Message, state: FSMContext, user, db: AsyncSession, activation_code: str, password: str):
    try:
        check = await check_service.get_check_by_activation_code(db, activation_code)
        if not check:
            await message.answer(get_text("check_not_found", message.from_user.language_code))
            return

        check_id = check.check_id
        check_amount = check.amount
        check_currency = check.currency

        activation = await check_service.activate_check(
            db=db,
            check_id=check_id,
            activator=user,
            password=password
        )

        try:
            creator = await auth_service.get_user_by_id(db, check.creator_id)
            if creator and creator.telegram_id:
                notification_text = (
                    f"@{user.username or user.first_name} активировал(а) ваш чек "
                    f"и получил(а) 🪙 {check_amount} {check_currency}."
                )
                await message.bot.send_message(
                    chat_id=creator.telegram_id,
                    text=notification_text
                )
        except Exception as e:
            logger.error(
                "Failed to send check activation notification",
                creator_id=check.creator_id,
                activator_id=user.id,
                error=str(e)
            )

        gift_image_url = "https://i.imgur.com/oS7vyaL.jpeg"
        text = f"🎁 У меня для тебя подарок!\n\nВы получили 🪙 {check_amount} {check_currency}"

        await message.answer_photo(
            photo=gift_image_url,
            caption=text,
            parse_mode="HTML"
        )
        await state.clear()

    except CheckError as e:
        await message.answer(str(e))
    except Exception as e:
        logger.error(
            "Activate check final failed",
            user_id=message.from_user.id,
            activation_code=activation_code,
            error=str(e),
            exc_info=True
        )
        await message.answer(get_text("error_occurred", message.from_user.language_code))


async def show_check_list(callback: CallbackQuery, user, db: AsyncSession):
    try:
        from app.models.check import CheckStatus
        page = 1
        if callback.data and "_" in callback.data:
            try:
                page = int(callback.data.split("_", 2)[2])
            except Exception:
                page = 1
        per_page = 10
        offset = (page - 1) * per_page
        checks = await check_service.get_user_checks(
            db=db,
            user_id=user.id,
            status=CheckStatus.ACTIVE,
            limit=per_page,
            offset=offset
        )
        more = len(await check_service.get_user_checks(db, user.id, status=CheckStatus.ACTIVE, limit=1, offset=offset + per_page)) > 0

        if not checks:
            text = "Здесь вы можете управлять своими созданными чеками."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Назад к чекам",
                        callback_data="check_menu"
                    )
                ]
            ])
        else:
            text = "Здесь вы можете управлять своими созданными чеками."

            keyboard_buttons = []
            for check in checks:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"{check.amount} {check.currency}",
                        callback_data=f"check_details_{check.check_id}"
                    )
                ])

            nav_row = []
            if page > 1:
                nav_row.append(InlineKeyboardButton(text="‹ Назад", callback_data=f"check_list_{page-1}"))
            if more:
                nav_row.append(InlineKeyboardButton(text="Вперед ›", callback_data=f"check_list_{page+1}"))
            if nav_row:
                keyboard_buttons.append(nav_row)

            keyboard_buttons.append([
                InlineKeyboardButton(text="‹ Назад к чекам", callback_data="check_menu")
            ])

            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.edit_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(
            "Show check list failed",
            user_id=callback.from_user.id,
            error=str(e),
            exc_info=True
        )
        raise


async def show_check_stats(callback: CallbackQuery, user, db: AsyncSession):
    try:
        stats = await check_service.get_check_stats(db, user.id)

        text = get_text("check_stats", callback.from_user.language_code).format(
            created_total=stats["created"]["total"],
            created_active=stats["created"]["active"],
            created_activated=stats["created"]["activated"],
            created_expired=stats["created"]["expired"],
            created_cancelled=stats["created"]["cancelled"],
            activated_total=stats["activated"]["total"],
            total_received=stats["activated"]["total_received"]
        )

        keyboard = get_back_keyboard("check_menu", callback.from_user.language_code)
        await callback.message.edit_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(
            "Show check stats failed",
            user_id=callback.from_user.id,
            error=str(e),
            exc_info=True
        )
        raise


async def show_check_details(callback: CallbackQuery, user, db: AsyncSession, check_id: str):
    try:
        check = await check_service.get_check_by_id(db, check_id, include_activations=True)

        if not check or check.creator_id != user.id:
            await callback.answer("❌ Чек не найден", show_alert=True)
            return

        text = await _format_check_info(check, callback.from_user.language_code, short_format=False)

        restrictions = _load_restrictions(check)
        is_gift = check.is_gift or restrictions.get("is_gift", False)

        kb_rows = []

        if is_gift:
            kb_rows.append([InlineKeyboardButton(text="🎁 Отправить подарок", callback_data=f"check_share_{check.check_id}")])

            if check.description:
                kb_rows.append([InlineKeyboardButton(text="Убрать описание", callback_data=f"gift_remove_description_{check.check_id}")])

            if check.target_user_id or check.target_username:
                kb_rows.append([InlineKeyboardButton(text="Открепить от пользователя", callback_data=f"gift_unpin_user_{check.check_id}")])

            kb_rows.extend([
                [InlineKeyboardButton(text="Удалить подарок", callback_data=f"check_cancel_{check.check_id}")],
                [InlineKeyboardButton(text="‹ Назад к списку чеков", callback_data="check_list")]
            ])
        else:
            has_image = bool(check.image_file_id or restrictions.get("image_file_id"))

            kb_rows = [
                [InlineKeyboardButton(text="🎁 Конвертировать в подарок", callback_data=f"check_convert_gift_{check.check_id}")],
                [InlineKeyboardButton(text="Поделиться чеком", callback_data=f"check_share_{check.check_id}")],
                [InlineKeyboardButton(text="Показать QR-код", callback_data=f"check_qr_{check.check_id}")],
                [InlineKeyboardButton(text="Добавить описание", callback_data=f"check_add_description_{check.check_id}")],
                [InlineKeyboardButton(text="Удалить картинку" if has_image else "Добавить картинку", callback_data=f"check_remove_image_{check.check_id}" if has_image else f"check_add_image_{check.check_id}")],
                [InlineKeyboardButton(text="Ограничения", callback_data=f"check_restrictions_{check.check_id}")],
                [InlineKeyboardButton(text="Удалить чек", callback_data=f"check_cancel_{check.check_id}")],
                [InlineKeyboardButton(text="‹ Назад к списку чеков", callback_data="check_list")]
            ]

        keyboard = InlineKeyboardMarkup(inline_keyboard=kb_rows)

        await _update_check_message(callback, check, keyboard)

    except Exception as e:
        logger.error(
            "Show check details failed",
            user_id=callback.from_user.id,
            check_id=check_id,
            error=str(e),
            exc_info=True
        )
        await callback.answer("❌ Произошла ошибка", show_alert=True)


async def cancel_check_confirm(callback: CallbackQuery, user, check_id: str, db: AsyncSession):
    try:
        check = await check_service.cancel_check(
            db=db,
            check_id=check_id,
            user=user
        )

        text = get_text("check_cancelled", callback.from_user.language_code).format(
            check_id=check.check_id,
            amount=check.amount,
            currency=check.currency
        )

        keyboard = get_back_keyboard("check_menu", callback.from_user.language_code)
        await callback.message.edit_text(text, reply_markup=keyboard)

    except CheckError as e:
        await callback.answer(str(e), show_alert=True)
    except Exception as e:
        logger.error(
            "Cancel check confirm failed",
            user_id=callback.from_user.id,
            check_id=check_id,
            error=str(e),
            exc_info=True
        )
        await callback.answer(get_text("error_occurred", callback.from_user.language_code))


@router.message(F.text.startswith("/start "))
async def handle_check_deep_link(message: Message, state: FSMContext, db: AsyncSession):
    try:
        param = message.text.split("/start ", 1)[1].strip()

        if param.startswith("activate_check_"):
            activation_code = param[15:]
        elif len(param) == 15 and param.isdigit():
            activation_code = param
        elif param.startswith("check_"):
            activation_code = param[6:]
        else:
            return

        user = await auth_service.get_user_by_telegram_id(db, message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        check = await check_service.get_check_by_activation_code(db, activation_code)
        if not check:
            await message.answer("❌ Чек не найден")
            return

        check_id = check.check_id
        check_amount = check.amount
        check_currency = check.currency

        if not check.can_be_activated_by(user.id, user.username):
            if check.creator_id == user.id:
                text = f"❌ Вы не можете активировать собственный чек"
            elif check.status != CheckStatus.ACTIVE:
                if check.status == CheckStatus.ACTIVATED:
                    text = f"❌ Этот чек уже активирован."
                else:
                    text = f"❌ Чек неактивен (статус: {check.status})"
            elif check.is_expired:
                text = f"❌ Срок действия чека истек"
            else:
                text = f"❌ Чек нельзя активировать"

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Назад",
                        callback_data="main_menu"
                    )
                ]
            ])
            await message.answer(text, reply_markup=keyboard)
            return

        if check.password:
            await state.update_data(activation_code=activation_code)
            await state.set_state(CheckStates.entering_activation_password)

            text = (
                f"🎫 Чек на {check_amount} {check_currency}\n\n"
                f"🔐 Для получения чека введите пароль:"
            )

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Отмена",
                        callback_data="main_menu"
                    )
                ]
            ])
            await message.answer(text, reply_markup=keyboard)
            return

        try:
            activation = await check_service.activate_check(
                db=db,
                check_id=check_id,
                activator=user,
                password=None
            )

            try:
                creator = await auth_service.get_user_by_id(db, check.creator_id)
                if creator and creator.telegram_id:
                    is_gift = not check.password and check.description and "Подарок" in check.description

                    if is_gift:
                        notification_text = (
                            f"🎁 {user.display_name or user.first_name} получил(а) ваш подарок. "
                            f"Вы подарили 🪙 {check_amount} {check_currency}."
                        )

                        recipient_text = (
                            f"🎁 {creator.display_name or creator.first_name} подарил(а) вам криптовалюту. "
                            f"Вы получили 🪙 {check_amount} {check_currency} на кошелёк в 🦋 Crypto Bot (http://t.me/CryptoBotRU/14).\n\n"
                            f"💬 {check.description or ''}"
                        )
                    else:
                        notification_text = (
                            f"@{user.username or user.first_name} активировал(а) ваш чек "
                            f"и получил(а) 🪙 {check_amount} {check_currency}."
                        )
                        recipient_text = f"Вы получили 🪙 {check_amount} {check_currency}"

                    await message.bot.send_message(
                        chat_id=creator.telegram_id,
                        text=notification_text
                    )

                    await message.answer(recipient_text)

            except Exception as e:
                logger.error(
                    "Failed to send check activation notification",
                    creator_id=check.creator_id,
                    activator_id=user.id,
                    error=str(e)
                )
                await message.answer(f"Вы получили 🪙 {check_amount} {check_currency}")

        except Exception as e:
            logger.error(
                "Check activation failed",
                check_id=check_id,
                user_id=user.id,
                error=str(e)
            )
            await message.answer("❌ Произошла ошибка при активации чека")

    except Exception as e:
        logger.error(
            "Handle check deep link failed",
            user_id=message.from_user.id,
            text=message.text,
            error=str(e),
            exc_info=True
        )
        await message.answer("❌ Произошла ошибка при обработке чека")


@router.callback_query(F.data.startswith("activate_check_"))
async def activate_check_from_link(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    try:
        activation_code = callback.data.split("_", 2)[2]

        user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        check = await check_service.get_check_by_activation_code(db, activation_code)
        if not check:
            await callback.answer("❌ Чек не найден", show_alert=True)
            return

        check_id = check.check_id
        check_amount = check.amount
        check_currency = check.currency

        if not check.can_be_activated_by(user.id, user.username):
            if check.creator_id == user.id:
                await callback.answer("❌ Вы не можете активировать собственный чек", show_alert=True)
            elif check.status != "active":
                if check.status == "activated":
                    await callback.answer("❌ Этот чек уже активирован.", show_alert=True)
                else:
                    await callback.answer(f"❌ Чек неактивен (статус: {check.status})", show_alert=True)
            elif check.is_expired:
                await callback.answer("❌ Срок действия чека истек", show_alert=True)
            else:
                await callback.answer("❌ Чек нельзя активировать", show_alert=True)
            return

        if check.password:
            await callback.answer("❌ Чек защищен паролем. Используйте ссылку для активации.", show_alert=True)
            return

        activation = await check_service.activate_check(
            db=db,
            check_id=check_id,
            activator=user,
            password=None
        )

        try:
            creator = await auth_service.get_user_by_id(db, check.creator_id)
            if creator and creator.telegram_id:
                is_gift = not check.password and check.description and "Подарок" in check.description

                if is_gift:
                    notification_text = (
                        f"🎁 {user.display_name or user.first_name} получил(а) ваш подарок. "
                        f"Вы подарили 🪙 {check_amount} {check_currency}."
                    )

                    text = (
                        f"✅ <b>Подарок успешно получен!</b>\n\n"
                        f"🎁 Получено: {check_amount} {check_currency}\n"
                        f"👤 От: {creator.display_name or creator.first_name}\n\n"
                        f"💳 Средства зачислены на ваш баланс"
                    )
                else:
                    notification_text = (
                        f"@{user.username or user.first_name} активировал(а) ваш чек "
                        f"и получил(а) {check_amount} {check_currency}."
                    )

                    text = (
                        f"✅ <b>Чек успешно активирован!</b>\n\n"
                        f"🎫 ID: <code>{check_id}</code>\n"
                        f"💰 Получено: {check_amount} {check_currency}\n"
                        f"👤 Получатель: @{user.username or user.first_name}\n\n"
                        f"💳 Средства зачислены на ваш баланс"
                    )

                await callback.bot.send_message(
                    chat_id=creator.telegram_id,
                    text=notification_text
                )

                await callback.message.edit_text(text, parse_mode="HTML")

                if is_gift:
                    try:
                        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                        from app.config import settings
                        bot_username = settings.bot_username
                        start_url = f"https://t.me/{bot_username}?start=start"

                        updated_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text=f"✅ Получено {check_amount} {check_currency}",
                                    callback_data=f"gift_received_{activation_code}_{check_amount}_{check_currency}"
                                )
                            ]
                        ])


                    except Exception as e:
                        logger.error("Failed to update gift button", error=str(e))

        except Exception as e:
            logger.error(
                "Failed to send check activation notification",
                creator_id=check.creator_id,
                activator_id=user.id,
                error=str(e)
            )
            await callback.message.edit_text(
                f"✅ Чек активирован! Получено: {check_amount} {check_currency}",
                parse_mode="HTML"
            )
        await callback.answer("✅ Чек активирован!")

    except Exception as e:
        logger.error(
            "Activate check from link failed",
            user_id=callback.from_user.id,
            activation_code=activation_code if 'activation_code' in locals() else 'unknown',
            error=str(e),
            exc_info=True
        )
        await callback.answer("❌ Произошла ошибка при активации чека", show_alert=True)


async def start_quick_check_creation(callback: CallbackQuery, state: FSMContext, user, db: AsyncSession, currency: str):
    try:
        wallet = await wallet_service.get_user_wallet(db, user.id, currency)

        if wallet and float(wallet.available_balance) > 0:
            await state.update_data(currency=currency, check_type="one_time")
            await show_amount_input_screen(callback, state, currency)
            return

        else:
            text = (
                f"Недостаточно средств для создания чека в {currency}. "
                "Пожалуйста, пополните баланс."
            )
            await callback.answer(text, show_alert=True)
            return


    except Exception as e:
        logger.error("Quick check creation failed", error=str(e))
        await callback.answer("❌ Произошла ошибка", show_alert=True)


async def show_create_from_chat_info(callback: CallbackQuery, user, db: AsyncSession):
    try:
        bot_info = await callback.bot.get_me()
        bot_username = bot_info.username

        text = (
            "💬 **Создание чеков из чата**\n\n"
            "Вы можете создавать чеки прямо из любого чата, "
            "используя inline режим:\n\n"
            f"• Наберите `@{bot_username} 100 USDT`\n"
            f"• Наберите `@{bot_username} 0.001 BTC`\n"
            f"• Наберите `@{bot_username} 50 TON`\n\n"
            "Если у вас достаточно средств, будет создан чек.\n"
            "Если недостаточно - будет создан счет для пополнения.\n\n"
            "💡 **Попробуйте прямо сейчас:**\n"
            f"Наберите в этом чате: `@{bot_username} 10 USDT`"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="« Назад к чекам",
                    callback_data="check_menu"
                )
            ]
        ])

        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error("Show create from chat info failed", error=str(e))
        await callback.answer("❌ Произошла ошибка", show_alert=True)


async def handle_check_activation(message: Message, param: str, language_code: str):
    try:
        async for db in get_db():
            if param.startswith("check_"):
                activation_code = param[6:]
            else:
                activation_code = param

            user = await auth_service.get_user_by_telegram_id(db, message.from_user.id)
            if not user:
                await message.answer("❌ Пользователь не найден")
                return

            check = await check_service.get_check_by_activation_code(db, activation_code)
            if not check:
                await message.answer("❌ Чек не найден или недействителен")
                return

            text = (
                f"🦋 **Чек на {check.amount} {check.currency}**\n\n"
                f"💰 Сумма: **{check.amount} {check.currency}**\n"
                f"👤 От: {check.creator.display_name if check.creator else 'Неизвестно'}\n"
                f"📝 Описание: {check.description or 'Без описания'}\n\n"
            )

            if check.can_be_activated_by(user.id, user.username):
                text += "✅ Вы можете активировать этот чек"

                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Активировать чек",
                            callback_data=f"activate_check_{activation_code}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="❌ Отмена",
                            callback_data="main_menu"
                        )
                    ]
                ])
            else:
                if check.creator_id == user.id:
                    text += "❌ Вы не можете активировать собственный чек"
                elif check.status != "active":
                    text += f"❌ Чек неактивен (статус: {check.status})"
                elif check.is_expired:
                    text += "❌ Срок действия чека истек"
                else:
                    text += "❌ Чек нельзя активировать"

                from app.bot.keyboards.inline import get_back_keyboard
                keyboard = get_back_keyboard("main_menu", language_code)

            await message.answer(
                text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            break

    except Exception as e:
        logger.error("Handle check activation failed", error=str(e))
        await message.answer("❌ Произошла ошибка при обработке чека")


@router.callback_query(F.data == "check_list")
async def show_check_list_handler(callback: CallbackQuery, db: AsyncSession):
    try:
        user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        await show_check_list(callback, user, db)

    except Exception as e:
        logger.error(
            "Show check list handler failed",
            user_id=callback.from_user.id,
            error=str(e),
            exc_info=True
        )
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("delete_check_"))
async def delete_check(callback: CallbackQuery, db: AsyncSession):
    try:
        check_id = callback.data.split("_", 2)[2]

        user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        check = await check_service.cancel_check(db, check_id, user)

        text = (
            f"✅ <b>Чек удален</b>\n\n"
            f"🎫 ID: <code>{check.check_id}</code>\n"
            f"💰 Сумма: {check.amount} {check.currency}\n\n"
            f"Средства возвращены на ваш баланс."
        )

        from app.models.check import CheckStatus
        checks = await check_service.get_user_checks(
            db=db,
            user_id=user.id,
            status=CheckStatus.ACTIVE,
            limit=10
        )
        from app.bot.keyboards.check_keyboards import get_check_list_keyboard
        keyboard = get_check_list_keyboard(checks, callback.from_user.language_code)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer("✅ Чек удален")

    except CheckError as e:
        await callback.answer(str(e), show_alert=True)
    except Exception as e:
        logger.error(
            "Delete check failed",
            user_id=callback.from_user.id,
            check_id=check_id if 'check_id' in locals() else 'unknown',
            error=str(e),
            exc_info=True
        )
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("check_convert_gift_"))
async def convert_check_to_gift_callback(callback_query, state=None):
    try:
        check_id = callback_query.data.split("_", 3)[3]

        async with AsyncSessionLocal() as db:
            user = await auth_service.get_user_by_telegram_id(db, callback_query.from_user.id)
            if not user:
                await callback_query.answer("❌ Пользователь не найден", show_alert=True)
                return

            check = await check_service.get_check_by_id(db, check_id)
            if not check or check.creator_id != user.id:
                await callback_query.answer("❌ Чек не найден", show_alert=True)
                return

            await callback_query.answer("🎁 Функция конвертации в подарок будет добавлена в следующих версиях", show_alert=True)

    except Exception as e:
        logger.error(
            "Failed to convert check to gift",
            user_id=callback_query.from_user.id,
            callback_data=callback_query.data,
            error=str(e),
            exc_info=True
        )
        await callback_query.answer("❌ Ошибка при конвертации", show_alert=True)


@router.callback_query(F.data.startswith("check_share_"))
async def share_check_callback(callback_query, state=None):
    try:
        check_id = callback_query.data.split("_", 2)[2]

        async with AsyncSessionLocal() as db:
            user = await auth_service.get_user_by_telegram_id(db, callback_query.from_user.id)
            if not user:
                await callback_query.answer("❌ Пользователь не найден", show_alert=True)
                return

            check = await check_service.get_check_by_id(db, check_id)
            if not check or check.creator_id != user.id:
                await callback_query.answer("❌ Чек не найден", show_alert=True)
                return

            from app.config import settings
            bot_username = settings.bot_username
            check_url = f"https://t.me/{bot_username}?start=activate_check_{check.activation_code}"

            text = (
                f"📤 <b>Поделиться чеком</b>\n\n"
                f"💰 Сумма: {check.amount} {check.currency}\n"
                f"Скопируйте ссылку, чтобы поделиться чеком.\n"
                f"<span class=\"tg-spoiler\">{check_url}\n\n"
                f"⚠️ Никогда не делайте скриншот вашего чека и не отправляйте его никому! "
                f"Ссылку на чек могут использовать мошенники, чтобы получить доступ к вашим средствам."
                f"</span>"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 Скопировать ссылку",
                        url=check_url
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="« Назад к чеку",
                        callback_data=f"check_details_{check_id}"
                    )
                ]
            ])

            await callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            await callback_query.answer()

    except Exception as e:
        logger.error(
            "Failed to share check",
            user_id=callback_query.from_user.id,
            callback_data=callback_query.data,
            error=str(e),
            exc_info=True
        )
        await callback_query.answer("❌ Ошибка при получении ссылки", show_alert=True)


@router.callback_query(F.data.startswith("check_qr_"))
async def show_check_qr_callback(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    try:
        check_id = callback.data.split("_", 2)[2]

        user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            await state.clear()
            return

        check = await check_service.get_check_by_id(db, check_id)
        if not check or check.creator_id != user.id:
            await callback.answer("❌ Чек не найден", show_alert=True)
            await state.clear()
            return

        try:
            from app.config import settings
            bot_username = settings.bot_username
            check_url = f"https://t.me/{bot_username}?start=activate_check_{check.activation_code}"

            import qrcode
            from io import BytesIO

            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(check_url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            bio = BytesIO()
            img.save(bio, format='PNG')
            bio.seek(0)

            try:
                await callback.message.delete()
            except Exception as delete_error:
                logger.warning(f"Could not delete old QR message: {delete_error}")

            text = (
                f"📱 <b>QR-код чека</b>\n\n"
                f"💰 Сумма: {check.amount} {check.currency}\n"
                f"📱 Отсканируйте QR-код для активации чека"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="« Назад к чеку",
                        callback_data=f"check_details_{check_id}"
                    )
                ]
            ])

            await callback.message.answer_photo(
                photo=bio,
                caption=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await callback.answer()
            await state.clear()

        except Exception as e:
            logger.error(
                "QR code generation failed",
                error=str(e),
                exc_info=True
            )
            await callback.answer("❌ Ошибка при генерации QR-кода", show_alert=True)

    except Exception as e:
        logger.error(
            "Check QR callback failed",
            user_id=callback.from_user.id,
            callback_data=callback.data,
            error=str(e),
            exc_info=True
        )
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)
@router.callback_query(F.data.startswith("check_add_description_"))
async def add_check_description_callback(callback_query, state=None):
    try:
        check_id = callback_query.data.split("_", 3)[3]

        await callback_query.answer("📝 Функция добавления описания будет добавлена в следующих версиях", show_alert=True)

    except Exception as e:
        logger.error(
            "Failed to add check description",
            user_id=callback_query.from_user.id,
            callback_data=callback_query.data,
            error=str(e),
            exc_info=True
        )
        await callback_query.answer("❌ Ошибка при добавлении описания", show_alert=True)


@router.callback_query(F.data.startswith("check_add_image_"))
async def add_check_image_callback(callback_query, state=None):
    try:
        check_id = callback_query.data.split("_", 3)[3]

        await callback_query.answer("🖼️ Функция добавления картинки будет добавлена в следующих версиях", show_alert=True)

    except Exception as e:
        logger.error(
            "Failed to add check image",
            user_id=callback_query.from_user.id,
            callback_data=callback_query.data,
            error=str(e),
            exc_info=True
        )
        await callback_query.answer("❌ Ошибка при добавлении картинки", show_alert=True)


@router.callback_query(F.data.startswith("check_restrictions_"))
async def check_restrictions_callback(callback_query, state=None):
    try:
        check_id = callback_query.data.split("_", 2)[2]
        async with AsyncSessionLocal() as db:
            user = await auth_service.get_user_by_telegram_id(db, callback_query.from_user.id)
            if not user:
                await callback_query.answer("❌ Пользователь не найден", show_alert=True)
                return
            check = await check_service.get_check_by_id(db, check_id)
            if not check or check.creator_id != user.id:
                await callback_query.answer("❌ Чек не найден", show_alert=True)
                return

            r = _load_restrictions(check)
            text = (
                "Здесь вы можете настроить ограничения, которые будут действовать при активации чека. "
                "Только пользователи, подходящие по этим ограничениям, смогут активировать чек.\n\n"
                f"Пароль: {'установлен' if r.get('password_plain') else 'нет'}\n"
                f"Только для Telegram Premium: {'Да' if r.get('premium_only') else 'Нет'}\n"
                f"Только для новых пользователей: {'Да' if r.get('new_users_only') else 'Нет'}\n"
                f"Проверка подписки: {'Вкл' if r.get('subscription_chat_ids') else 'Выкл'}"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Добавить пароль", callback_data=f"check_restr_pwd_{check_id}")],
                [InlineKeyboardButton(text="Закрепить за пользователем", callback_data=f"check_restr_bind_{check_id}")],
                [InlineKeyboardButton(text=f"Только для Telegram Premium: {'Да' if r.get('premium_only') else 'Нет'}", callback_data=f"check_restr_premium_{check_id}")],
                [InlineKeyboardButton(text=f"Только для новых пользователей: {'Да' if r.get('new_users_only') else 'Нет'}", callback_data=f"check_restr_new_{check_id}")],
                [InlineKeyboardButton(text=f"Проверка подписки: {'Вкл' if r.get('subscription_chat_ids') else 'Выкл'}", callback_data=f"check_restr_sub_{check_id}")],
                [InlineKeyboardButton(text="« Назад к чеку", callback_data=f"check_details_{check_id}")]
            ])
            await callback_query.message.edit_text(text, reply_markup=kb)
            await callback_query.answer()
    except Exception as e:
        logger.error(
            "Failed to show check restrictions",
            user_id=callback_query.from_user.id,
            callback_data=callback_query.data,
            error=str(e),
            exc_info=True
        )
        await callback_query.answer("❌ Ошибка при добавлении картинки", show_alert=True)


@router.callback_query(F.data.startswith("check_restrictions_"))
async def show_check_restrictions_callback(callback_query, db=None):
    try:
        check_id = callback_query.data.split("_", 2)[2]

        async with AsyncSessionLocal() as db:
            user = await auth_service.get_user_by_telegram_id(db, callback_query.from_user.id)
            if not user:
                await callback_query.answer("❌ Пользователь не найден", show_alert=True)
                return

            check = await check_service.get_check_by_id(db, check_id)
            if not check or check.creator_id != user.id:
                await callback_query.answer("❌ Чек не найден", show_alert=True)
                return

            await show_check_restrictions(callback_query, db)

    except Exception as e:
        logger.error(
            "Failed to open check restrictions",
            user_id=callback_query.from_user.id,
            callback_data=callback_query.data,
            error=str(e),
            exc_info=True
        )
        await callback_query.answer("❌ Ошибка при открытии ограничений", show_alert=True)


@router.callback_query(F.data.startswith("gift_remove_description_"))
async def remove_gift_description(callback: CallbackQuery, db: AsyncSession):
    check_id = callback.data.split("_", 3)[3]

    check = await db.get(Check, check_id)
    if not check:
        await callback.answer("❌ Подарок не найден", show_alert=True)
        return

    restrictions = _load_restrictions(check)
    check.description = None
    restrictions["description"] = None
    await _save_restrictions(db, check, restrictions)

    await callback.answer("✅ Описание удалено", show_alert=True)

    user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
    await show_check_details(callback, user, db, check_id)


@router.callback_query(F.data.startswith("gift_unpin_user_"))
async def unpin_gift_user(callback: CallbackQuery, db: AsyncSession):
    check_id = callback.data.split("_", 3)[3]

    check = await db.get(Check, check_id)
    if not check:
        await callback.answer("❌ Подарок не найден", show_alert=True)
        return

    restrictions = _load_restrictions(check)
    check.target_user_id = None
    check.target_username = None
    check.type = CheckType.ONE_TIME.value

    restrictions.pop("bound_username", None)
    restrictions.pop("bound_user_id", None)

    await _save_restrictions(db, check, restrictions)

    await callback.answer("✅ Подарок откреплен от пользователя", show_alert=True)

    user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
    await show_check_details(callback, user, db, check_id)


@router.callback_query(F.data.startswith("check_remove_image:"))
async def remove_check_image(callback: CallbackQuery, db: AsyncSession):
    check_id = callback.data.split(":")[1]

    check = await db.get(Check, check_id)
    if not check:
        await callback.answer("❌ Чек не найден", show_alert=True)
        return

    restrictions = _load_restrictions(check)
    check.image_file_id = None
    restrictions["image_file_id"] = None
    restrictions["is_animation"] = False
    await _save_restrictions(db, check, restrictions)

    await callback.answer("✅ Картинка удалена", show_alert=True)

    from app.services.user import auth_service
    user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)

    text = await _format_check_info(check, getattr(callback.from_user, 'language_code', 'ru'), short_format=False)

    restrictions = _load_restrictions(check)
    has_image = bool(check.image_file_id or restrictions.get("image_file_id"))
    has_description = bool(restrictions.get("description"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Конвертировать в подарок", callback_data=f"check_convert_gift_{check.check_id}")],
        [InlineKeyboardButton(text="Поделиться чеком", callback_data=f"check_share_{check.check_id}")],
        [InlineKeyboardButton(text="Показать QR-код", callback_data=f"check_qr_{check.check_id}")],
        [InlineKeyboardButton(text="Удалить описание" if has_description else "Добавить описание", callback_data=f"check_remove_description:{check.check_id}" if has_description else f"check_add_description:{check.check_id}")],
        [InlineKeyboardButton(text="Удалить картинку" if has_image else "Добавить картинку", callback_data=f"check_remove_image:{check.check_id}" if has_image else f"check_add_image:{check.check_id}")],
        [InlineKeyboardButton(text="Ограничения", callback_data=f"check_restrictions:{check.check_id}")],
        [InlineKeyboardButton(text="Удалить чек", callback_data=f"check_delete:{check.check_id}")],
        [InlineKeyboardButton(text="‹ Назад к списку чеков", callback_data="check_list")]
    ])

    if has_image:
        if restrictions.get("is_animation"):
            await callback.message.edit_media(
                media=InputMediaAnimation(
                    media=check.image_file_id or restrictions.get("image_file_id"),
                    caption=text,
                    show_caption_above_media=True,
                    parse_mode="HTML"
                ),
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_media(
                media=InputMediaPhoto(
                    media=check.image_file_id or restrictions.get("image_file_id"),
                    caption=text,
                    show_caption_above_media=True,
                    parse_mode="HTML"
                ),
                reply_markup=keyboard
            )
    else:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("check_remove_description"))
async def remove_check_description(callback: CallbackQuery, db: AsyncSession):
    try:
        if ":" in callback.data:
            check_id = callback.data.split(":")[1]
        else:
            check_id = None
            if callback.message.reply_markup:
                for row in callback.message.reply_markup.inline_keyboard:
                    for button in row:
                        if button.callback_data and ("check_view:" in button.callback_data or "check_details_" in button.callback_data):
                            check_id = button.callback_data.split(":")[-1] if ":" in button.callback_data else button.callback_data.split("_")[-1]
                            break
                    if check_id:
                        break

        if not check_id:
            await callback.answer("❌ Не удалось определить ID чека", show_alert=True)
            return

        check = await db.get(Check, check_id)
        if not check:
            await callback.answer("❌ Чек не найден", show_alert=True)
            return

        restrictions = _load_restrictions(check)
        restrictions["description"] = None
        await _save_restrictions(db, check, restrictions)

        await callback.answer("✅ Описание удалено", show_alert=True)

        from app.services.user import auth_service
        user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)

        text = await _format_check_info(check, getattr(callback.from_user, 'language_code', 'ru'), short_format=False)

        restrictions = _load_restrictions(check)
        has_image = bool(check.image_file_id or restrictions.get("image_file_id"))
        has_description = bool(restrictions.get("description"))

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Конвертировать в подарок", callback_data=f"check_convert_gift_{check.check_id}")],
            [InlineKeyboardButton(text="Поделиться чеком", callback_data=f"check_share_{check.check_id}")],
            [InlineKeyboardButton(text="Показать QR-код", callback_data=f"check_qr_{check.check_id}")],
            [InlineKeyboardButton(text="Удалить описание" if has_description else "Добавить описание", callback_data=f"check_remove_description:{check.check_id}" if has_description else f"check_add_description:{check.check_id}")],
            [InlineKeyboardButton(text="Удалить картинку" if has_image else "Добавить картинку", callback_data=f"check_remove_image:{check.check_id}" if has_image else f"check_add_image:{check.check_id}")],
            [InlineKeyboardButton(text="Ограничения", callback_data=f"check_restrictions:{check.check_id}")],
            [InlineKeyboardButton(text="Удалить чек", callback_data=f"check_delete:{check.check_id}")],
            [InlineKeyboardButton(text="‹ Назад к списку чеков", callback_data="check_list")]
        ])

        if has_image:
            if restrictions.get("is_animation"):
                await callback.message.edit_media(
                    media=InputMediaAnimation(
                        media=check.image_file_id or restrictions.get("image_file_id"),
                        caption=text,
                        show_caption_above_media=True,
                        parse_mode="HTML"
                    ),
                    reply_markup=keyboard
                )
            else:
                await callback.message.edit_media(
                    media=InputMediaPhoto(
                        media=check.image_file_id or restrictions.get("image_file_id"),
                        caption=text,
                        show_caption_above_media=True,
                        parse_mode="HTML"
                    ),
                    reply_markup=keyboard
                )
        else:
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error removing check description: {e}")
        await callback.answer("❌ Ошибка при удалении описания", show_alert=True)


@router.callback_query(F.data.startswith("check_view_"))
async def view_check_details(callback: CallbackQuery, db: AsyncSession):
    try:
        check_id = callback.data.split("_", 2)[2]

        check = await db.get(Check, check_id)
        if not check:
            await callback.answer("❌ Чек не найден", show_alert=True)
            return

        from app.services.user import auth_service
        user = await auth_service.get_user_by_telegram_id(db, callback.from_user.id)
        if not user or check.creator_id != user.id:
            await callback.answer("❌ У вас нет доступа к этому чеку", show_alert=True)
            return

        text = await _format_check_info(check, getattr(callback.from_user, 'language_code', 'ru'), short_format=False)

        restrictions = _load_restrictions(check)
        has_image = bool(check.image_file_id or restrictions.get("image_file_id"))
        has_description = bool(restrictions.get("description"))

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Конвертировать в подарок", callback_data=f"check_convert_gift_{check.check_id}")],
            [InlineKeyboardButton(text="Поделиться чеком", callback_data=f"check_share_{check.check_id}")],
            [InlineKeyboardButton(text="Показать QR-код", callback_data=f"check_qr_{check.check_id}")],
            [InlineKeyboardButton(text="Удалить описание" if has_description else "Добавить описание", callback_data=f"check_remove_description:{check.check_id}" if has_description else f"check_add_description:{check.check_id}")],
            [InlineKeyboardButton(text="Удалить картинку" if has_image else "Добавить картинку", callback_data=f"check_remove_image:{check.check_id}" if has_image else f"check_add_image:{check.check_id}")],
            [InlineKeyboardButton(text="Ограничения", callback_data=f"check_restrictions:{check.check_id}")],
            [InlineKeyboardButton(text="Удалить чек", callback_data=f"check_delete:{check.check_id}")],
            [InlineKeyboardButton(text="‹ Назад к списку чеков", callback_data="check_list")]
        ])

        if has_image:
            if restrictions.get("is_animation"):
                await callback.message.edit_media(
                    media=InputMediaAnimation(
                        media=check.image_file_id or restrictions.get("image_file_id"),
                        caption=text,
                        show_caption_above_media=True,
                        parse_mode="HTML"
                    ),
                    reply_markup=keyboard
                )
            else:
                await callback.message.edit_media(
                    media=InputMediaPhoto(
                        media=check.image_file_id or restrictions.get("image_file_id"),
                        caption=text,
                        show_caption_above_media=True,
                        parse_mode="HTML"
                    ),
                    reply_markup=keyboard
                )
        else:
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error viewing check details: {e}")
        await callback.answer("❌ Ошибка при просмотре чека", show_alert=True)
