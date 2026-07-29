from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.base import Base, metadata
from typing import AsyncGenerator

from app.config import settings as config_settings

from app.models import (
    admin,
    api,
    blockchain,
    check,
    exchange,
    invoice,
    notification,
    p2p,
    settings,
    subscription,
    transaction,
    user,
    wallet,
)


if config_settings.database_url_sync.startswith("sqlite"):
    sync_engine = create_engine(
        config_settings.database_url_sync,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    sync_engine = create_engine(
        config_settings.database_url_sync,
        pool_size=config_settings.database_pool_size,
        max_overflow=config_settings.database_max_overflow,
        pool_pre_ping=True,
        echo=False,
    )

if config_settings.database_url_async.startswith("sqlite"):
    async_engine = create_async_engine(
        config_settings.database_url_async,
        echo=False,
        future=True
    )
else:
    async_engine = create_async_engine(
        config_settings.database_url_async,
        pool_size=config_settings.database_pool_size,
        max_overflow=config_settings.database_max_overflow,
        pool_pre_ping=True,
        echo=False,
        future=True
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


import importlib

async def create_tables():
    model_modules = [
        "app.models.admin",
        "app.models.api",
        "app.models.blockchain",
        "app.models.check",
        "app.models.exchange",
        "app.models.invoice",
        "app.models.notification",
        "app.models.p2p",
        "app.models.settings",
        "app.models.subscription",
        "app.models.transaction",
        "app.models.user",
        "app.models.wallet",
    ]
    for module in model_modules:
        importlib.import_module(module)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def check_db_connection() -> bool:
    try:
        from sqlalchemy import text
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


async def init_database():
    skip_db_check = config_settings.is_development or config_settings.testing

    try:
        db_ok = await check_db_connection()

        if not db_ok:
            if skip_db_check:
                print("⚠️ База данных недоступна, работаем без нее")
            else:
                raise Exception("Failed to connect to database")

        if db_ok:
            print("✅ Database connection initialized successfully")
        elif skip_db_check:
            print("⚠️ Запуск в режиме разработки без подключения к БД")

    except Exception as e:
        if skip_db_check:
            print(f"⚠️ Ошибка подключения к БД: {e}")
            print("⚠️ Продолжаем работу в режиме разработки")
        else:
            raise


async def close_database():
    await async_engine.dispose()

    print("✅ Database connections closed successfully")


class DatabaseTransaction:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.session.rollback()
        else:
            await self.session.commit()


def transaction(session: AsyncSession) -> DatabaseTransaction:
    return DatabaseTransaction(session)


def run_migrations():
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("✅ Database migrations completed")


def create_migration(message: str):
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config("alembic.ini")
    command.revision(alembic_cfg, autogenerate=True, message=message)
    print(f"✅ Migration '{message}' created")

engine = sync_engine

__all__ = [
    'sync_engine',
    'async_engine',
    'engine',
    'Base',
    'init_database',
    'create_tables',
    'get_db',
    'get_async_db',
    'close_database'
]
