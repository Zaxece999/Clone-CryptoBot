import asyncio
import logging
from app.utils.russian_logger import get_russian_logger
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
import structlog

from app.config import settings
from app.database import init_database, close_database, engine
from app.bot.handlers import (
    start, wallet, check, invoice, p2p, exchange, subscription,
    settings as settings_handler, api, blockchain, notifications, admin
)
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
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True,
        )
    )

    return bot


async def create_dispatcher() -> Dispatcher:
    storage = MemoryStorage()
    logger.info("Используется MemoryStorage для FSM")

    dp = Dispatcher(storage=storage)

    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())

    dp.include_router(start.router)
    dp.include_router(wallet.router)
    dp.include_router(check.router)
    dp.include_router(invoice.router)
    dp.include_router(p2p.router)
    dp.include_router(exchange.router)
    dp.include_router(subscription.router)
    dp.include_router(blockchain.router)
    dp.include_router(notifications.router)
    dp.include_router(admin.router)
    dp.include_router(api.router)
    dp.include_router(settings_handler.router)

    return dp


async def check_database_connection() -> bool:
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            await result.fetchone()
        logger.info("Подключение к базе данных успешно")
        return True
    except Exception as e:
        logger.error("Ошибка подключения к базе данных", error=str(e))
        return False


async def create_tables_if_not_exist():
    try:
        from app.models import user, wallet, transaction, check, invoice, p2p, exchange, subscription, api_key
        from app.database import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Таблицы базы данных созданы/обновлены")

    except Exception as e:
        logger.error("Ошибка при создании таблиц", error=str(e))
        raise


async def on_startup(bot: Bot) -> None:
    logger.info("Запуск Telegram бота...")

    db_connected = await check_database_connection()

    if db_connected:
        try:
            await init_database()

            await create_tables_if_not_exist()

            logger.info("База данных инициализирована успешно")
        except Exception as e:
            logger.error("Ошибка при инициализации БД", error=str(e))
            logger.warning("Бот будет работать без подключения к БД")
    else:
        logger.warning("Бот запущен без подключения к базе данных")

    try:
        bot_info = await bot.get_me()
        logger.info(
            "Бот запущен",
            bot_id=bot_info.id,
            bot_username=bot_info.username,
            bot_name=bot_info.first_name,
        )
    except Exception as e:
        logger.error("Ошибка получения информации о боте", error=str(e))

    try:
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

    except Exception as e:
        logger.error("Ошибка установки команд бота", error=str(e))


async def on_shutdown(bot: Bot) -> None:
    logger.info("Остановка Telegram бота...")

    try:
        await close_database()
        logger.info("Подключения к БД закрыты")
    except Exception as e:
        logger.error("Ошибка при закрытии БД", error=str(e))

    try:
        await bot.session.close()
        logger.info("Сессия бота закрыта")
    except Exception as e:
        logger.error("Ошибка закрытия сессии бота", error=str(e))

    logger.info("Telegram бот остановлен")


async def main() -> None:
    bot = None
    dp = None

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
        if bot:
            try:
                await bot.session.close()
            except:
                pass

        logger.info("Завершение работы бота")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error("Критическая ошибка", error=str(e), exc_info=True)
        exit(1)
