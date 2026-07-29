import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import create_tables, check_db_connection, async_engine


async def init_database():
    print("🔧 Инициализация базы данных...")

    try:
        print("📡 Проверка подключения к базе данных...")
        db_ok = await check_db_connection()

        if not db_ok:
            print("❌ Не удалось подключиться к базе данных")
            return False

        print("✅ Подключение к базе данных установлено")

        print("🏗️ Создание таблиц...")
        await create_tables()

        print("✅ База данных инициализирована успешно!")
        print("\nСозданные таблицы:")
        print("- users (пользователи)")
        print("- user_settings (настройки пользователя)")
        print("- wallets (кошельки)")
        print("- transactions (транзакции)")
        print("- p2p_orders (P2P заказы)")
        print("- notifications (уведомления)")
        print("- и другие...")

        return True

    except Exception as e:
        print(f"❌ Ошибка при инициализации базы данных: {e}")
        return False
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(init_database())
    if success:
        print("\n🎉 База данных готова к работе!")
        sys.exit(0)
    else:
        print("\n💥 Ошибка инициализации базы данных")
        sys.exit(1)
