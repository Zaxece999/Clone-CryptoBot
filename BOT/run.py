import asyncio
import subprocess
import sys
import os
import signal
import time
from pathlib import Path


class CryptoBotRunner:
    def __init__(self):
        self.processes = []
        self.running = False

    def create_db_from_models(self):
        import asyncio
        from app.database import create_tables
        try:
            print("🗄️ Создание базы данных и таблиц из моделей...")
            asyncio.run(create_tables())
            print("✅ База данных и таблицы созданы (если их не было)")
        except Exception as e:
            print(f"❌ Ошибка создания базы данных: {e}")
            return False
        return True

    def check_dependencies(self):
        print("🔍 Проверка зависимостей...")

        if sys.version_info < (3, 9):
            print("❌ Требуется Python 3.9 или выше")
            return False

        if not Path(".env").exists():
            print("❌ Файл .env не найден. Скопируйте .env.example в .env и настройте его")
            return False

        if not Path("requirements.txt").exists():
            print("❌ Файл requirements.txt не найден")
            return False

        print("✅ Зависимости проверены")
        return True

    def install_requirements(self):
        print("📦 Установка зависимостей...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                         check=True, capture_output=True)
            print("✅ Зависимости установлены")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка установки зависимостей: {e}")
            return False

    def run_migrations(self):
        print("🗄️ Применение миграций...")
        try:
            env = os.environ.copy()
            env['SKIP_TOKEN_VALIDATION'] = 'true'

            subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                         check=True, capture_output=True, env=env)
            print("✅ Миграции применены")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка применения миграций: {e}")
            return False

    def start_api_server(self):
        print("🚀 Запуск API сервера...")
        try:
            process = subprocess.Popen([
                sys.executable, "-m", "app.main"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            self.processes.append(("API Server", process))
            print("✅ API сервер запущен")
            return True
        except Exception as e:
            print(f"❌ Ошибка запуска API сервера: {e}")
            return False

    def start_telegram_bot(self):
        print("🤖 Запуск Telegram бота...")
        try:
            process = subprocess.Popen([
                sys.executable, "-m", "app.bot.main"
            ], stdout=None, stderr=None)

            self.processes.append(("Telegram Bot", process))
            print("✅ Telegram бот запущен")
            return True
        except Exception as e:
            print(f"❌ Ошибка запуска Telegram бота: {e}")
            return False

    def stop_all(self):
        print("\n🛑 Остановка всех сервисов...")

        for name, process in self.processes:
            try:
                print(f"Остановка {name}...")
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ {name} остановлен")
            except subprocess.TimeoutExpired:
                print(f"⚠️ Принудительная остановка {name}...")
                process.kill()
                process.wait()
            except Exception as e:
                print(f"❌ Ошибка остановки {name}: {e}")

        self.processes.clear()
        self.running = False
        print("✅ Все сервисы остановлены")

    def monitor_processes(self):
        print("\n📊 Мониторинг процессов (Ctrl+C для остановки)...")
        print("=" * 50)

        try:
            while self.running:
                all_running = True

                for name, process in self.processes:
                    if process.poll() is None:
                        status = "🟢 Работает"
                    else:
                        status = "🔴 Остановлен"
                        all_running = False

                    print(f"{name}: {status}")

                if not all_running:
                    print("⚠️ Некоторые сервисы остановлены")
                    break

                print("-" * 30)
                time.sleep(10)

        except KeyboardInterrupt:
            print("\n⚠️ Получен сигнал остановки...")
        finally:
            self.stop_all()

    def run_full(self):
        print("🚀 Запуск CryptoBot Clone")
        print("=" * 50)

        if not self.check_dependencies():
            return False

        if not self.install_requirements():
            return False

        if not self.create_db_from_models():
            return False

        if not self.start_api_server():
            return False

        time.sleep(2)

        if not self.start_telegram_bot():
            return False

        self.running = True

        print("\n🎉 Все сервисы запущены успешно!")
        print("📖 API документация: http://localhost:8000/docs")
        print("🤖 Telegram бот готов к работе")

        self.monitor_processes()

        return True

    def run_api_only(self):
        print("🚀 Запуск только API сервера")
        print("=" * 50)

        if not self.check_dependencies():
            return False

        if not self.create_db_from_models():
            return False


        if not self.start_api_server():
            return False

        self.running = True

        print("\n🎉 API сервер запущен!")
        print("📖 Документация: http://localhost:8000/docs")

        self.monitor_processes()
        return True

    def run_bot_only(self):
        print("🚀 Запуск только Telegram бота")
        print("=" * 50)

        if not Path(".env").exists():
            print("❌ Файл .env не найден. Скопируйте .env.example в .env и настройте его")
            return False

        if not self.create_db_from_models():
            return False


        if not self.start_telegram_bot():
            return False

        self.running = True

        print("\n🎉 Telegram бот запущен!")
        print("🤖 Бот готов к работе")
        print("📋 Логи бота будут отображаться ниже...")
        print("⚠️ Для остановки используйте Ctrl+C")
        print("=" * 50)

        try:
            for name, process in self.processes:
                if name == "Telegram Bot":
                    process.wait()
                    break
        except KeyboardInterrupt:
            print("\n⚠️ Получен сигнал остановки...")
            self.stop_all()

        return True


def show_help():
    print("""
🤖 CryptoBot Clone - Скрипт запуска

Использование:
    python run.py [команда]

Команды:
    bot         Запустить только Telegram бота (по умолчанию)
    full        Запустить все сервисы
    api         Запустить только API сервер
    install     Только установить зависимости
    migrate     Только применить миграции
    help        Показать эту справку

Примеры:
    python run.py              # Запуск только Telegram бота
    python run.py bot           # Запуск только Telegram бота
    python run.py full          # Запуск всех сервисов
    python run.py api           # Только API сервер
    python run.py install       # Установка зависимостей
    python run.py migrate       # Применение миграций

Для остановки используйте Ctrl+C
    """)


def main():
    runner = CryptoBotRunner()

    def signal_handler(signum, frame):
        print("\n⚠️ Получен сигнал остановки...")
        runner.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    command = sys.argv[1] if len(sys.argv) > 1 else "bot"

    if command == "help":
        show_help()
    elif command == "install":
        runner.check_dependencies()
        runner.install_requirements()
    elif command == "migrate":
        runner.run_migrations()
    elif command == "api":
        runner.run_api_only()
    elif command == "bot":
        runner.run_bot_only()
    elif command == "full":
        runner.run_full()
    else:
        print(f"❌ Неизвестная команда: {command}")
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
