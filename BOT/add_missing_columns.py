import asyncio
import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import async_engine


async def add_missing_columns():
    print("🔧 Добавление недостающих колонок в базу данных...")

    try:
        db_path = os.path.join(os.path.dirname(__file__), 'cryptobot.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        missing_columns = [
            {
                'table': 'user_verification',
                'column': 'documents_verified',
                'type': 'BOOLEAN DEFAULT FALSE',
                'description': 'Статус верификации документов администратором'
            },
            {
                'table': 'user_verification',
                'column': 'address_verification_pending',
                'type': 'BOOLEAN DEFAULT FALSE',
                'description': 'Статус ожидания верификации адреса'
            },
            {
                'table': 'user_verification',
                'column': 'phone_verification_pending',
                'type': 'BOOLEAN DEFAULT FALSE',
                'description': 'Статус ожидания верификации телефона'
            },
            {
                'table': 'user_verification',
                'column': 'verification_rejected',
                'type': 'BOOLEAN DEFAULT FALSE',
                'description': 'Статус отклонения верификации'
            },
            {
                'table': 'user_verification',
                'column': 'rejection_reason',
                'type': 'TEXT',
                'description': 'Причина отклонения верификации'
            },
            {
                'table': 'user_verification',
                'column': 'verification_notes',
                'type': 'TEXT',
                'description': 'Заметки администратора по верификации'
            }
        ]

        cursor.execute("PRAGMA table_info(user_verification)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        print(f"Существующие колонки в user_verification: {existing_columns}")

        for col in missing_columns:
            if col['column'] not in existing_columns:
                try:
                    alter_sql = f"ALTER TABLE {col['table']} ADD COLUMN {col['column']} {col['type']}"
                    print(f"Добавляем колонку: {col['column']} ({col['description']})")
                    cursor.execute(alter_sql)
                    print(f"✅ Колонка {col['column']} добавлена успешно")
                except sqlite3.Error as e:
                    print(f"❌ Ошибка при добавлении колонки {col['column']}: {e}")
            else:
                print(f"⏭️ Колонка {col['column']} уже существует")

        other_missing_columns = [
            {
                'table': 'users',
                'column': 'base_currency',
                'type': 'VARCHAR(10) DEFAULT "USD"',
                'description': 'Базовая валюта пользователя'
            },
            {
                'table': 'users',
                'column': 'sounds_enabled',
                'type': 'BOOLEAN DEFAULT TRUE',
                'description': 'Включены ли звуки у пользователя'
            }
        ]

        cursor.execute("PRAGMA table_info(users)")
        existing_users_columns = [row[1] for row in cursor.fetchall()]
        print(f"Существующие колонки в users: {existing_users_columns}")

        for col in other_missing_columns:
            if col['column'] not in existing_users_columns:
                try:
                    alter_sql = f"ALTER TABLE {col['table']} ADD COLUMN {col['column']} {col['type']}"
                    print(f"Добавляем колонку: {col['column']} ({col['description']})")
                    cursor.execute(alter_sql)
                    print(f"✅ Колонка {col['column']} добавлена успешно")
                except sqlite3.Error as e:
                    print(f"❌ Ошибка при добавлении колонки {col['column']}: {e}")
            else:
                print(f"⏭️ Колонка {col['column']} уже существует")

        conn.commit()
        print("✅ Все изменения сохранены в базе данных")

        print("\n📋 Финальная структура таблицы user_verification:")
        cursor.execute("PRAGMA table_info(user_verification)")
        for row in cursor.fetchall():
            print(f"  - {row[1]} ({row[2]})")

        return True

    except Exception as e:
        print(f"❌ Ошибка при добавлении колонок: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    success = asyncio.run(add_missing_columns())
    if success:
        print("\n🎉 Все недостающие колонки добавлены успешно!")
        sys.exit(0)
    else:
        print("\n💥 Ошибка при добавлении колонок")
        sys.exit(1)
