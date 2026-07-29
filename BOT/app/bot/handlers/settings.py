from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.bot.keyboards.settings import (
    get_settings_main_keyboard,
    get_referrals_keyboard,
    get_notifications_main_keyboard,
    get_notifications_broadcasts_keyboard,
    get_notification_setting_keyboard,
    get_notifications_referrals_keyboard,
    get_notifications_crypto_pay_keyboard,
    get_notifications_p2p_market_keyboard,
    get_notifications_giveaways_keyboard,
    get_notifications_subscriptions_creator_keyboard,
    get_notifications_subscriptions_subscriber_keyboard,
    get_language_keyboard,
    get_currency_keyboard,
    get_back_to_settings_keyboard
)
from app.services.settings import settings_service
from app.services.user import user_service
from app.models.settings import ReferralPeriod, NotificationSubtype
from app.bot.utils.decorators import get_db_session

logger = structlog.get_logger(__name__)
router = Router()


@router.message(Command("settings"))
@get_db_session
async def cmd_settings(message: Message, db: AsyncSession, language_code: str = "ru"):
    await show_settings_menu(message, db, language_code)


@router.callback_query(F.data == "settings_menu")
@get_db_session
async def callback_settings_menu(callback: CallbackQuery, db: AsyncSession, language_code: str = "ru"):
    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        user = await user_service.create_user_from_telegram(db, callback.from_user)

    settings = await settings_service.get_or_create_user_settings(db, user.id)

    settings_text = f"""
👤 <b>{user.full_name}</b> (<a href="https://t.me/send/profile/{user.telegram_id}">профиль в P2P</a>)

Часовой пояс: {settings.timezone}
Локальная валюта: {settings.local_currency}
    """

    keyboard = get_settings_main_keyboard(
        user_timezone=settings.timezone,
        user_currency=settings.local_currency,
        language_code=language_code
    )

    await callback.message.edit_text(
        settings_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


async def show_settings_menu(message: Message, db: AsyncSession, language_code: str = "ru", edit: bool = False):
    from_user = getattr(message, 'from_user', None)
    if not from_user and hasattr(message, 'message') and message.message:
        from_user = message.message.from_user

    if not from_user:
        await message.answer("Не удалось определить пользователя")
        return

    user = await user_service.get_user_by_telegram_id(db, from_user.id)
    if not user:
        user = await user_service.create_user_from_telegram(db, from_user)

    settings = await settings_service.get_or_create_user_settings(db, user.id)

    referral_links = await settings_service.generate_referral_links(user)

    settings_text = f"""
👤 <b>{user.full_name}</b> (<a href="https://t.me/send/profile/{user.telegram_id}">профиль в P2P</a>)

Часовой пояс: {settings.timezone}
Локальная валюта: {settings.local_currency}
    """

    keyboard = get_settings_main_keyboard(
        user_timezone=settings.timezone,
        user_currency=settings.local_currency,
        language_code=language_code
    )

    if edit:
        await message.edit_text(
            settings_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await message.answer(
            settings_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )


@router.callback_query(F.data == "settings_referrals")
@get_db_session
async def callback_referrals_menu(callback: CallbackQuery, db: AsyncSession):
    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    referral_links = await settings_service.generate_referral_links(user)

    stats = await settings_service.get_referral_stats(db, user.id, ReferralPeriod.ALL_TIME)

    referrals_text = f"""
💰 Приглашайте активных пользователей в бот и зарабатывайте криптовалюту. <a href="https://youtu.be/KqXQcmsRgTA">Смотрите видеоинструкцию ›</a>

Вы можете получить следующие вознаграждения за приглашённых пользователей:
• 30% от комиссии их сделок в P2P Маркете, созданных ими в качестве тейкера.
• 15% от комиссии их любых заявок на обмен в Бирже.

Скопируйте одну из ссылок ниже, чтобы пригласить рефералов:
• {referral_links['basic']}
• {referral_links['market']} для перехода в P2P Маркет
• {referral_links['exchange']} для перехода в Биржу

Статистика за {stats['period'].replace('_', ' ')}:
Вы пригласили: {stats['invited_count']}
Активные пользователи: {stats['active_users_count']}

Ваш заработок: ${stats['earnings_usd']}
    """

    keyboard = get_referrals_keyboard(ReferralPeriod.ALL_TIME)

    await callback.message.edit_text(
        referrals_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("referrals_period_"))
@get_db_session
async def callback_referrals_period(callback: CallbackQuery, db: AsyncSession):
    period_str = callback.data.split("_")[-1]
    if period_str == "all_time":
        period = ReferralPeriod.ALL_TIME
    elif period_str == "yesterday":
        period = ReferralPeriod.YESTERDAY
    elif period_str == "week":
        period = ReferralPeriod.WEEK
    elif period_str == "month":
        period = ReferralPeriod.MONTH
    else:
        period = ReferralPeriod.ALL_TIME

    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    referral_links = await settings_service.generate_referral_links(user)

    stats = await settings_service.get_referral_stats(db, user.id, period)

    period_names = {
        "all_time": "всё время",
        "yesterday": "вчера",
        "week": "неделю",
        "month": "месяц"
    }

    referrals_text = f"""
💰 Приглашайте активных пользователей в бот и зарабатывайте криптовалюту. <a href="https://youtu.be/KqXQcmsRgTA">Смотрите видеоинструкцию ›</a>

Вы можете получить следующие вознаграждения за приглашённых пользователей:
• 30% от комиссии их сделок в P2P Маркете, созданных ими в качестве тейкера.
• 15% от комиссии их любых заявок на обмен в Бирже.

Скопируйте одну из ссылок ниже, чтобы пригласить рефералов:
• {referral_links['basic']}
• {referral_links['market']} для перехода в P2P Маркет
• {referral_links['exchange']} для перехода в Биржу

Статистика за {period_names.get(period_str, period_str)}:
Вы пригласили: {stats['invited_count']}
Активные пользователи: {stats['active_users_count']}

Ваш заработок: ${stats['earnings_usd']}
    """

    keyboard = get_referrals_keyboard(period)

    await callback.message.edit_text(
        referrals_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "settings_notifications")
async def callback_notifications_menu(callback: CallbackQuery):
    notifications_text = """
Выберите тип уведомлений, которые вы хотите настроить.
    """

    keyboard = get_notifications_main_keyboard()

    await callback.message.edit_text(
        notifications_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_broadcasts")
async def callback_notifications_broadcasts(callback: CallbackQuery):
    broadcasts_text = """
Здесь вы можете настроить получение рассылок от команды Crypto Bot.
    """

    keyboard = get_notifications_broadcasts_keyboard()

    await callback.message.edit_text(
        broadcasts_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "settings_language")
@get_db_session
async def callback_language_menu(callback: CallbackQuery, db: AsyncSession):
    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    settings = await settings_service.get_or_create_user_settings(db, user.id)

    language_text = """
Выберите язык бота.
    """

    keyboard = get_language_keyboard(settings.bot_language)

    await callback.message.edit_text(
        language_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "settings_currency")
@get_db_session
async def callback_currency_menu(callback: CallbackQuery, db: AsyncSession):
    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    settings = await settings_service.get_or_create_user_settings(db, user.id)

    keyboard = get_currency_keyboard(settings.local_currency)

    await callback.message.edit_text(
        "Выберите валюту бота:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("language_"))
@get_db_session
async def callback_language_select(callback: CallbackQuery, db: AsyncSession):
    language = callback.data.split("_")[1]

    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    await settings_service.update_user_settings(db, user.id, bot_language=language)

    await callback.answer(f"Язык изменен на {'Русский' if language == 'ru' else 'English'}")

    await show_settings_menu(callback.message, db, language, edit=True)


@router.callback_query(F.data.startswith("currency_"))
@get_db_session
async def callback_currency_select(callback: CallbackQuery, db: AsyncSession):
    currency = callback.data.split("_")[1]

    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    await settings_service.update_user_settings(db, user.id, local_currency=currency)

    await callback.answer(f"Валюта изменена на {currency}")

    await show_settings_menu(callback.message, db, "ru", edit=True)


@router.callback_query(F.data == "notifications_referrals")
async def callback_notifications_referrals(callback: CallbackQuery):
    referrals_text = """
Здесь вы можете настроить уведомления, связанные с рефералами.
    """

    keyboard = get_notifications_referrals_keyboard()

    await callback.message.edit_text(
        referrals_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_crypto_pay")
async def callback_notifications_crypto_pay(callback: CallbackQuery):
    crypto_pay_text = """
Здесь вы можете настроить уведомления, связанные с 🏝 Crypto Pay.
    """

    keyboard = get_notifications_crypto_pay_keyboard()

    await callback.message.edit_text(
        crypto_pay_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_p2p_market")
async def callback_notifications_p2p_market(callback: CallbackQuery):
    p2p_text = """
Здесь вы можете настроить уведомления, связанные с P2P Маркетом.
    """

    keyboard = get_notifications_p2p_market_keyboard()

    await callback.message.edit_text(
        p2p_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_giveaways")
async def callback_notifications_giveaways(callback: CallbackQuery):
    giveaways_text = """
Здесь вы можете настроить уведомления, связанные с розыгрышами.
    """

    keyboard = get_notifications_giveaways_keyboard()

    await callback.message.edit_text(
        giveaways_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_subscriptions_creator")
async def callback_notifications_subscriptions_creator(callback: CallbackQuery):
    creator_text = """
Здесь вы можете настроить уведомления, связанные с платными подписками на ваши подключённые каналы и группы.
    """

    keyboard = get_notifications_subscriptions_creator_keyboard()

    await callback.message.edit_text(
        creator_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_subscriptions_subscriber")
async def callback_notifications_subscriptions_subscriber(callback: CallbackQuery):
    subscriber_text = """
Здесь вы можете настроить уведомления, связанные с вашими платными подписками.
    """

    keyboard = get_notifications_subscriptions_subscriber_keyboard()

    await callback.message.edit_text(
        subscriber_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_news_broadcasts")
@get_db_session
async def callback_news_broadcasts(callback: CallbackQuery, db: AsyncSession):
    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    prefs = await settings_service.get_notification_preference(
        db, user.id, NotificationSubtype.NEWS_BROADCASTS
    )

    news_text = """
Подпишитесь или отпишитесь от новостных рассылок о новых функциях и других обновлениях бота.
    """

    keyboard = get_notification_setting_keyboard(
        NotificationSubtype.NEWS_BROADCASTS,
        enabled=prefs['enabled'],
        sound=prefs['sound'],
        show_sound=prefs['enabled']
    )

    await callback.message.edit_text(
        news_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_marketing_broadcasts")
@get_db_session
async def callback_marketing_broadcasts(callback: CallbackQuery, db: AsyncSession):
    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    prefs = await settings_service.get_notification_preference(
        db, user.id, NotificationSubtype.MARKETING_BROADCASTS
    )

    marketing_text = """
Подпишитесь или отпишитесь от маркетинговых рассылок о новых конкурсах и других активностях.
    """

    keyboard = get_notification_setting_keyboard(
        NotificationSubtype.MARKETING_BROADCASTS,
        enabled=prefs['enabled'],
        sound=prefs['sound'],
        show_sound=prefs['enabled']
    )

    await callback.message.edit_text(
        marketing_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_referral_rewards")
@get_db_session
async def callback_referral_rewards(callback: CallbackQuery, db: AsyncSession):
    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    prefs = await settings_service.get_notification_preference(
        db, user.id, NotificationSubtype.REFERRAL_REWARDS
    )

    referral_text = """
Включите или отключите уведомления о новых реферальных вознаграждениях.
    """

    keyboard = get_notification_setting_keyboard(
        NotificationSubtype.REFERRAL_REWARDS,
        enabled=prefs['enabled'],
        sound=prefs['sound'],
        show_sound=prefs['enabled']
    )

    await callback.message.edit_text(
        referral_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_payment_notifications")
@get_db_session
async def callback_payment_notifications(callback: CallbackQuery, db: AsyncSession):
    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    prefs = await settings_service.get_notification_preference(
        db, user.id, NotificationSubtype.PAYMENT_NOTIFICATIONS
    )

    payment_text = """
Включите или отключите уведомления об оплате счетов созданными приложением.
    """

    keyboard = get_notification_setting_keyboard(
        NotificationSubtype.PAYMENT_NOTIFICATIONS,
        enabled=prefs['enabled'],
        sound=prefs['sound'],
        show_sound=prefs['enabled']
    )

    await callback.message.edit_text(
        payment_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_new_review")
@get_db_session
async def callback_new_review(callback: CallbackQuery, db: AsyncSession):
    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    prefs = await settings_service.get_notification_preference(
        db, user.id, NotificationSubtype.NEW_REVIEW
    )

    review_text = """
Включите или отключите уведомления о новых отзывах.
    """

    keyboard = get_notification_setting_keyboard(
        NotificationSubtype.NEW_REVIEW,
        enabled=prefs['enabled'],
        sound=prefs['sound'],
        show_sound=prefs['enabled']
    )

    await callback.message.edit_text(
        review_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_invitation_participation")
@get_db_session
async def callback_invitation_participation(callback: CallbackQuery, db: AsyncSession):
    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    prefs = await settings_service.get_notification_preference(
        db, user.id, NotificationSubtype.INVITATION_PARTICIPATION
    )

    invitation_text = """
Включите или отключите уведомления о новых участниках по вашей реферальной ссылке.
    """

    keyboard = get_notification_setting_keyboard(
        NotificationSubtype.INVITATION_PARTICIPATION,
        enabled=prefs['enabled'],
        sound=prefs['sound'],
        show_sound=prefs['enabled']
    )

    await callback.message.edit_text(
        invitation_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_new_subscribers")
@get_db_session
async def callback_new_subscribers(callback: CallbackQuery, db: AsyncSession):
    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    prefs = await settings_service.get_notification_preference(
        db, user.id, NotificationSubtype.NEW_SUBSCRIBERS
    )

    subscribers_text = """
Включите или отключите уведомления о новых подписчиках в ваших подключённых каналах или группах.
    """

    keyboard = get_notification_setting_keyboard(
        NotificationSubtype.NEW_SUBSCRIBERS,
        enabled=prefs['enabled'],
        sound=prefs['sound'],
        show_sound=prefs['enabled']
    )

    await callback.message.edit_text(
        subscribers_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_subscription_renewals")
@get_db_session
async def callback_subscription_renewals(callback: CallbackQuery, db: AsyncSession):
    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    prefs = await settings_service.get_notification_preference(
        db, user.id, NotificationSubtype.SUBSCRIPTION_RENEWALS
    )

    renewals_text = """
Включите или отключите уведомления о продлении подписок на ваши подключённые каналы и группы.
    """

    keyboard = get_notification_setting_keyboard(
        NotificationSubtype.SUBSCRIPTION_RENEWALS,
        enabled=prefs['enabled'],
        sound=prefs['sound'],
        show_sound=prefs['enabled']
    )

    await callback.message.edit_text(
        renewals_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_subscription_cancellations")
@get_db_session
async def callback_subscription_cancellations(callback: CallbackQuery, db: AsyncSession):
    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    prefs = await settings_service.get_notification_preference(
        db, user.id, NotificationSubtype.SUBSCRIPTION_CANCELLATIONS
    )

    cancellations_text = """
Включите или отключите уведомления об отменах подписок на ваши подключённые каналы и группы.
    """

    keyboard = get_notification_setting_keyboard(
        NotificationSubtype.SUBSCRIPTION_CANCELLATIONS,
        enabled=prefs['enabled'],
        sound=prefs['sound'],
        show_sound=prefs['enabled']
    )

    await callback.message.edit_text(
        cancellations_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_renewal_notifications")
@get_db_session
async def callback_renewal_notifications(callback: CallbackQuery, db: AsyncSession):
    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    prefs = await settings_service.get_notification_preference(
        db, user.id, NotificationSubtype.RENEWAL_NOTIFICATIONS
    )

    renewal_text = """
Включите или отключите уведомления о продлении ваших платных подписок.
    """

    keyboard = get_notification_setting_keyboard(
        NotificationSubtype.RENEWAL_NOTIFICATIONS,
        enabled=prefs['enabled'],
        sound=prefs['sound'],
        show_sound=prefs['enabled']
    )

    await callback.message.edit_text(
        renewal_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_insufficient_balance")
@get_db_session
async def callback_insufficient_balance(callback: CallbackQuery, db: AsyncSession):
    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    prefs = await settings_service.get_notification_preference(
        db, user.id, NotificationSubtype.INSUFFICIENT_BALANCE
    )

    balance_text = """
Включите или отключите звук уведомлений о недостаточном балансе для продления ваших платных подписок.
    """

    keyboard = get_notification_setting_keyboard(
        NotificationSubtype.INSUFFICIENT_BALANCE,
        enabled=True,
        sound=prefs['sound'],
        show_sound=True
    )

    await callback.message.edit_text(
        balance_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "notifications_cancellation_notifications")
@get_db_session
async def callback_cancellation_notifications(callback: CallbackQuery, db: AsyncSession):
    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    prefs = await settings_service.get_notification_preference(
        db, user.id, NotificationSubtype.CANCELLATION_NOTIFICATIONS
    )

    cancellation_text = """
Включите или отключите уведомления об отмене ваших платных подписок.
    """

    keyboard = get_notification_setting_keyboard(
        NotificationSubtype.CANCELLATION_NOTIFICATIONS,
        enabled=prefs['enabled'],
        sound=prefs['sound'],
        show_sound=prefs['enabled']
    )

    await callback.message.edit_text(
        cancellation_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("notification_toggle_"))
@get_db_session
async def callback_notification_toggle(callback: CallbackQuery, db: AsyncSession):
    parts = callback.data.split("_")
    subtype_str = "_".join(parts[2:-1])
    setting_type = parts[-1]

    try:
        subtype = NotificationSubtype(subtype_str)
    except ValueError:
        await callback.answer("Неизвестный тип уведомления")
        return

    user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    current_prefs = await settings_service.get_notification_preference(db, user.id, subtype)

    if setting_type == "enabled":
        new_enabled = not current_prefs['enabled']
        await settings_service.update_notification_preference(
            db, user.id, subtype, enabled=new_enabled
        )
        await callback.answer(f"Уведомления {'включены' if new_enabled else 'выключены'}")
    elif setting_type == "sound":
        new_sound = not current_prefs['sound']
        await settings_service.update_notification_preference(
            db, user.id, subtype, sound=new_sound
        )
        await callback.answer(f"Звук {'включен' if new_sound else 'выключен'}")

    updated_prefs = await settings_service.get_notification_preference(db, user.id, subtype)

    keyboard = get_notification_setting_keyboard(
        subtype,
        enabled=updated_prefs['enabled'],
        sound=updated_prefs['sound'],
        show_sound=updated_prefs['enabled'] or subtype == NotificationSubtype.INSUFFICIENT_BALANCE
    )

    await callback.message.edit_reply_markup(reply_markup=keyboard)


@router.callback_query(F.data == "settings_fees_limits")
async def callback_fees_limits(callback: CallbackQuery):
    await callback.answer("Функция будет реализована позже")


@router.callback_query(F.data == "settings_contests")
async def callback_contests(callback: CallbackQuery):
    await callback.answer("Функция будет реализована позже")
