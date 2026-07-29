import asyncio
import logging
from app.utils.russian_logger import get_russian_logger
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
import structlog

from app.config import settings
from app.database import init_database, close_database
from app.bot.handlers import start, wallet, check, invoice, p2p, exchange, subscription, settings as settings_handler, api, blockchain, notifications, admin, p2p_menu, address_book, fees_limits, inline, gift_callbacks
from app.bot.middlewares.auth import AuthMiddleware
from app.bot.middlewares.logging import LoggingMiddleware
from app.utils.logging import setup_logging

setup_logging()
logger = structlog.get_logger(__name__)


async def create_bot() -> Bot:
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN не установлен")

    bot = Bot(
        token=settings.telegram_bot_token,
        parse_mode=ParseMode.HTML
    )

    return bot


async def create_dispatcher() -> Dispatcher:
    storage = MemoryStorage()
    logger.info("Используется MemoryStorage для FSM")

    dp = Dispatcher(storage=storage)

    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.inline_query.middleware(AuthMiddleware())
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.inline_query.middleware(LoggingMiddleware())

    dp.include_router(address_book.router)
    dp.include_router(fees_limits.router)
    dp.include_router(wallet.router)
    dp.include_router(check.router)
    dp.include_router(invoice.router)
    dp.include_router(p2p.router)
    dp.include_router(p2p_menu.router)
    dp.include_router(exchange.router)
    dp.include_router(subscription.router)
    dp.include_router(blockchain.router)
    dp.include_router(notifications.router)
    dp.include_router(admin.router)
    dp.include_router(api.router)
    dp.include_router(settings_handler.router)
    dp.include_router(inline.router)
    dp.include_router(gift_callbacks.router)
    dp.include_router(start.router)

    return dp


async def on_startup(bot: Bot) -> None:
    logger.info("Запуск Telegram бота...")

    await init_database()

    bot_info = await bot.get_me()
    logger.info(
        "Бот запущен",
        bot_id=bot_info.id,
        bot_username=bot_info.username,
        bot_name=bot_info.first_name,
    )

    from aiogram.types import BotCommand

    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="wallet", description="💰 Кошелек"),
        BotCommand(command="deposit", description="📥 Пополнение"),
        BotCommand(command="withdraw", description="📤 Вывод средств"),
        BotCommand(command="check", description="🎫 Чеки"),
        BotCommand(command="invoice", description="🧾 Инвойсы"),
        BotCommand(command="p2p", description="🏪 P2P Market"),
        BotCommand(command="exchange", description="🔄 Обмен"),
        BotCommand(command="subscriptions", description="📺 Подписки"),
        BotCommand(command="notifications", description="🔔 Уведомления"),
        BotCommand(command="api", description="🔧 API для разработчиков"),
        BotCommand(command="admin", description="🛡️ Админ-панель"),
        BotCommand(command="settings", description="⚙️ Настройки"),
        BotCommand(command="help", description="ℹ️ Помощь"),
    ]

    await bot.set_my_commands(commands)
    logger.info("Команды бота установлены")


async def on_shutdown(bot: Bot) -> None:
    logger.info("Остановка Telegram бота...")

    await close_database()

    await bot.session.close()

    logger.info("Telegram бот остановлен")


async def main() -> None:
    try:
        bot = await create_bot()
        dp = await create_dispatcher()

        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        logger.info("Запуск polling...")

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )

    except Exception as e:
        logger.error("Ошибка при запуске бота", error=str(e), exc_info=True)
        raise
    finally:
        logger.info("Завершение работы бота")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error("Критическая ошибка", error=str(e), exc_info=True)
        exit(1)
