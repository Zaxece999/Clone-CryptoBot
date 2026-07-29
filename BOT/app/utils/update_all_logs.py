import os
import re
import ast
from pathlib import Path

LOG_PATTERNS = [
    r'logger\.info\(["\']([^"\']+)["\']',
    r'logger\.error\(["\']([^"\']+)["\']',
    r'logger\.warning\(["\']([^"\']+)["\']',
    r'logger\.debug\(["\']([^"\']+)["\']',
    r'logger\.critical\(["\']([^"\']+)["\']',
]

RUSSIAN_TRANSLATIONS = {
    "Starting Telegram bot...": "🚀 Запуск Telegram бота...",
    "Stopping Telegram bot...": "🛑 Остановка Telegram бота...",
    "Telegram bot stopped": "✅ Telegram бот остановлен",
    "Starting polling...": "▶️ Запуск polling...",
    "Bot commands set": "✅ Команды бота установлены",
    "Database connection successful": "✅ Подключение к базе данных успешно",
    "Database connection failed": "❌ Ошибка подключения к базе данных",
    "Database tables created/updated": "🗃️ Таблицы базы данных созданы/обновлены",
    "Database initialized successfully": "✅ База данных инициализирована успешно",
    "Database initialization failed": "❌ Ошибка при инициализации БД",
    "Bot running without database": "⚠️ Бот запущен без подключения к базе данных",
    "MemoryStorage for FSM": "🗄️ Используется MemoryStorage для FSM",
    "Received stop signal": "⚡ Получен сигнал остановки",
    "Shutting down bot": "🔄 Завершение работы бота",
    "Critical error": "💥 Критическая ошибка",

    "Failed to get deposit address": "❌ Не удалось получить адрес депозита",
    "Failed to get deposit addresses": "❌ Не удалось получить адреса депозита",
    "Failed to create withdrawal": "❌ Не удалось создать вывод",
    "Failed to get withdrawal history": "❌ Не удалось получить историю выводов",
    "Failed to get withdrawal details": "❌ Не удалось получить детали вывода",
    "Failed to get transactions": "❌ Не удалось получить транзакции",
    "Failed to get transaction details": "❌ Не удалось получить детали транзакции",
    "Failed to get networks": "❌ Не удалось получить список сетей",
    "Failed to get network info": "❌ Не удалось получить информацию о сети",
    "Failed to validate address": "❌ Не удалось валидировать адрес",
    "Failed to get network fees": "❌ Не удалось получить информацию о комиссиях",
    "Telegram auth failed": "❌ Ошибка Telegram авторизации",
    "Token refresh failed": "❌ Обновление токена не удалось",
    "User updated": "✅ Пользователь обновлен",
    "User update failed": "❌ Обновление пользователя не удалось",
    "PIN set failed": "❌ Установка PIN не удалась",
    "PIN verify failed": "❌ Проверка PIN не удалась",
    "User settings updated": "✅ Настройки пользователя обновлены",
    "Settings update failed": "❌ Обновление настроек не удалось",
    "User deactivated": "✅ Пользователь деактивирован",
    "User deletion failed": "❌ Удаление пользователя не удалось",

    "Exchange rate cache cleared": "🧹 Кэш курсов валют очищен",
    "Exchange rates updated": "🔄 Курсы валют обновлены",
    "Creating local wallet": "💳 Создаю локальный кошелек",
    "Wallet already exists": "💼 Кошелек уже существует",
    "Wallet created": "✅ Кошелек создан",
    "Wallet created successfully": "✅ Кошелек успешно создан",
    "No wallets found for user": "👛 Кошельки не найдены для пользователя",
    "Found wallets for user": "👛 Найдены кошельки для пользователя",
    "Found wallets for currency": "💰 Найдены кошельки для валюты",
    "No wallets found for currency": "❌ Кошельки не найдены для валюты",
    "Error getting user wallets": "❌ Ошибка получения кошельков пользователя",
    "Error getting user wallet": "❌ Ошибка получения кошелька пользователя",
    "Failed to get supported pairs": "❌ Не удалось получить поддерживаемые пары",
    "Failed to update exchange rates": "❌ Не удалось обновить курсы валют",

    "Event started": "🎯 Событие началось",
    "Bot user detected": "🤖 Обнаружен бот-пользователь",
    "Failed to toggle notifications": "❌ Не удалось изменить настройки уведомлений",
    "Failed to toggle notification type": "❌ Не удалось изменить тип уведомления",
    "Failed to toggle notification channel": "❌ Не удалось изменить канал уведомления",
    "Failed to update email": "❌ Не удалось обновить email",
    "Failed to update phone": "❌ Не удалось обновить телефон",
    "Failed to remove email": "❌ Не удалось удалить email",
    "Failed to remove phone": "❌ Не удалось удалить телефон",
    "Failed to create address book entry": "❌ Не удалось создать запись в адресной книге",
    "Failed to show deposit address": "❌ Не удалось показать адрес депозита",
    "Failed to create withdrawal": "❌ Не удалось создать вывод",
    "Failed to create application": "❌ Не удалось создать приложение",
    "Failed to create API key": "❌ Не удалось создать API ключ",
    "Failed to enable maintenance mode": "❌ Не удалось включить режим обслуживания",
    "Failed to disable maintenance mode": "❌ Не удалось отключить режим обслуживания",
}

def update_file_logs(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        for english, russian in RUSSIAN_TRANSLATIONS.items():
            english_escaped = english.replace('"', '\\"').replace("'", "\\'")
            russian_escaped = russian.replace('"', '\\"').replace("'", "\\'")

            patterns = [
                f'logger.info("{english_escaped}"',
                f"logger.info('{english_escaped}'",
                f'logger.error("{english_escaped}"',
                f"logger.error('{english_escaped}'",
                f'logger.warning("{english_escaped}"',
                f"logger.warning('{english_escaped}'",
                f'logger.debug("{english_escaped}"',
                f"logger.debug('{english_escaped}'",
                f'logger.critical("{english_escaped}"',
                f"logger.critical('{english_escaped}'",
            ]

            for pattern in patterns:
                content = content.replace(pattern, pattern.replace(english_escaped, russian_escaped))

        if 'from app.utils.russian_logger import get_russian_logger' not in content:
            if 'import logging' in content:
                content = content.replace(
                    'import logging',
                    'import logging\nfrom app.utils.russian_logger import get_russian_logger'
                )

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Обновлены логи в файле: {file_path}")
            return True

    except Exception as e:
        print(f"❌ Ошибка при обновлении файла {file_path}: {e}")

    return False

def update_all_logs():
    project_root = Path('/root/cryptobot')
    python_files = list(project_root.rglob('*.py'))

    updated_count = 0

    for file_path in python_files:
        if 'venv' not in str(file_path) and '__pycache__' not in str(file_path):
            if update_file_logs(file_path):
                updated_count += 1

    print(f"\n🎉 Обновлено файлов: {updated_count}")
    print("📋 Все логи теперь на русском языке с эмодзи!")

if __name__ == "__main__":
    print("🔄 Начинаю обновление всех логов на русский язык...")
    update_all_logs()
