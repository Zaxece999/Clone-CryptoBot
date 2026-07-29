from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
import structlog

from app.database import get_async_db
from app.services.auth import auth_service
from app.services.wallet import wallet_service
from app.services.p2p import p2p_service
from app.bot.keyboards.inline import get_main_menu_keyboard
from app.bot.utils.texts import get_text

logger = structlog.get_logger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, language_code: str = "ru"):
    start_param = None
    if message.text and len(message.text.split()) > 1:
        start_param = message.text.split()[1]
        logger.info("Start with parameter", user_id=message.from_user.id, param=start_param)

    if start_param:
        await handle_start_parameter(message, start_param, language_code)
        return

    welcome_text = (
    '🦋 <a href="https://t.me/CryptoBotRU/14">Мультивалютный криптокошелёк</a>. '
    'Покупайте, продавайте, храните, <a href="https://t.me/CryptoBotRU/228">отправляйте</a> '
    'и платите криптовалютой, когда хотите.\n\n'
    'Подписывайтесь на <a href="https://t.me/CryptoBotRU">наш канал</a> '
    'и вступайте в <a href="https://t.me/CryptoBotRussian">наш чат</a>.\n\n'
    )

    keyboard = get_main_menu_keyboard(language_code)

    await message.answer(
        welcome_text,
        reply_markup=keyboard
    )

    async def create_user_and_wallets():
        async for db in get_async_db():
            try:
                user = await auth_service.get_or_create_user_by_telegram(
                    db=db,
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    language_code=message.from_user.language_code
                )

                wallets = await wallet_service.get_user_wallets(db, user.id)

                p2p_stats = await p2p_service.get_user_stats(db, user.id)
                if not p2p_stats:
                    from app.models.p2p import P2PUserStats
                    p2p_stats = P2PUserStats(user_id=user.id)
                    db.add(p2p_stats)
                    logger.info("P2P stats created for user", user_id=user.id)

                if not wallets:
                    from app.config import settings
                    currencies = settings.supported_crypto_currencies

                    import asyncio

                    async def create_wallet_task(currency):
                        try:
                            logger.info(f"Создание кошелька {currency} для пользователя {user.id}")
                            wallet = await wallet_service.create_wallet(
                                db=db,
                                user=user,
                                currency=currency,
                                wallet_name=f"My {currency} Wallet"
                            )
                            logger.info(f"Кошелек {currency} создан: {wallet.address}")
                            return currency, wallet, None
                        except Exception as e:
                            logger.error(f"Failed to create {currency} wallet", error=str(e))
                            return currency, None, str(e)

                    tasks = [create_wallet_task(currency) for currency in currencies]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    wallets_to_add = []
                    for result in results:
                        if isinstance(result, Exception):
                            logger.error(f"Wallet creation task failed", error=str(result))
                        else:
                            currency, wallet, error = result
                            if error:
                                logger.error(f"Failed to create {currency} wallet", error=error)
                            elif wallet:
                                logger.info(f"Кошелек {currency} успешно создан")
                                wallets_to_add.append(wallet)

                    for wallet in wallets_to_add:
                        db.add(wallet)

                await db.commit()
                logger.info(f"User {user.id} processed")

                break

            except Exception as e:
                logger.error("Failed to create user/wallets", error=str(e))
                await db.rollback()
                break

    import asyncio
    asyncio.create_task(create_user_and_wallets())


@router.message(Command("help"))
async def cmd_help(message: Message, language_code: str = "ru"):
    help_text = get_text("help", language_code)
    keyboard = get_main_menu_keyboard(language_code)

    await message.answer(
        help_text,
        reply_markup=keyboard
    )


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, language_code: str = "ru"):
    main_menu_text = get_text("main_menu", language_code)
    keyboard = get_main_menu_keyboard(language_code)

    await callback.message.edit_text(
        main_menu_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "about")
async def callback_about(callback: CallbackQuery, language_code: str = "ru"):
    about_text = get_text("about", language_code)

    from app.bot.keyboards.inline import get_back_keyboard
    keyboard = get_back_keyboard("main_menu", language_code)

    await callback.message.edit_text(
        about_text,
        reply_markup=keyboard
    )
    await callback.answer()


async def handle_start_parameter(message: Message, param: str, language_code: str):
    logger.info("Handling start parameter", param=param, user_id=message.from_user.id)

    if param.startswith("CHK_"):
        from app.bot.handlers.check import handle_check_activation
        await handle_check_activation(message, param, language_code)
        return

    if param.startswith("INV_"):
        from app.bot.handlers.invoice import handle_invoice_payment
        await handle_invoice_payment(message, param, language_code)
        return

    if param.startswith("P2P_"):
        from app.bot.handlers.p2p import handle_p2p_order
        await handle_p2p_order(message, param, language_code)
        return

    if param.startswith("SUB_"):
        from app.bot.handlers.subscription import handle_subscription
        await handle_subscription(message, param, language_code)
        return

    logger.warning("Unknown start parameter", param=param, user_id=message.from_user.id)

    error_text = get_text("unknown_parameter", language_code)
    keyboard = get_main_menu_keyboard(language_code)

    await message.answer(
        error_text,
        reply_markup=keyboard
    )


@router.message(F.text.startswith("/"))
async def unknown_command(message: Message, language_code: str = "ru"):
    unknown_text = get_text("unknown_command", language_code)
    keyboard = get_main_menu_keyboard(language_code)

    await message.answer(
        unknown_text,
        reply_markup=keyboard
    )


@router.message(F.text)
async def ignore_plain_text(message: Message):
    return
