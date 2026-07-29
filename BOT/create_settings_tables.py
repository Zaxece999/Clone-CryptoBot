import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import async_engine
from app.models.base import Base
from app.models.settings import UserSettings, ReferralStats, NotificationPreferences
from app.models.user import User


async def create_settings_tables():
    print("Создание таблиц настроек...")

    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("✅ Таблицы настроек созданы успешно!")

        print("\nСозданные таблицы:")
        print("- user_settings (настройки пользователя)")
        print("- referral_stats (статистика рефералов)")
        print("- notification_preferences (настройки уведомлений)")

    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        raise
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_settings_tables())
