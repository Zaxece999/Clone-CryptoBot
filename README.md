# Clone-CryptoBot

Клон Telegram-бота CryptoBot: бот на aiogram 3 и веб-приложение (Telegram Mini App) на Flask.
Проект учебный, работает с тестовыми сетями и локальной базой SQLite.

## Возможности

- Кошельки для основных монет и токенов, история операций
- Переводы, чеки и инвойсы, ссылки для активации
- Обмен валют по курсам внешних API
- Разделы P2P и P2C
- Mini App: депозит, вывод, обмен, настройки, адресная книга, верификация
- Административные команды и статистика

## Структура

```
app.py               Flask-сервер Mini App и вспомогательного API
simple_bot_db.py     чтение балансов из базы бота
templates/           HTML-страницы Mini App
static/              CSS, JS, изображения, иконки, шрифты
BOT/
  run.py             запуск бота и API
  requirements.txt   зависимости
  app/config.py      настройки из переменных окружения
  app/bot/           хендлеры, клавиатуры, middleware
  app/api/           REST API
  app/models/        модели SQLAlchemy
  app/services/      бизнес-логика
  app/schemas/       схемы Pydantic
  docs/              описание Crypto Pay API
```

## Требования

- Python 3.11
- ngrok, если нужен внешний адрес для Mini App

## Установка

```bash
python -m venv env
env\Scripts\activate
pip install -r BOT/requirements.txt
```

## Настройка

Скопируйте примеры конфигов и заполните значения своими:

```bash
copy .env.example .env
copy BOT\.env.example BOT\.env
```

Минимум, что нужно указать:

- `TELEGRAM_BOT_TOKEN` — токен бота от BotFather
- `BOT_USERNAME` — имя бота без символа @
- `SECRET_KEY`, `ENCRYPTION_KEY` — свои случайные значения
- ключи ценовых API (`COINMARKETCAP_API_KEY`, `OPENEXCHANGERATES_APP_ID`), если нужны реальные курсы

Файлы `.env` и база `cryptobot.db` в репозиторий не попадают.

## Запуск

Веб-приложение вместе с ботом и туннелем ngrok:

```bash
python app.py
```

Быстрый старт только веб-части, без ngrok и бота:

```bash
LIGHT_START=1 python app.py
```

Веб-часть доступна на http://localhost:5000.

Только бот:

```bash
cd BOT
python run.py bot
```

Другие команды `run.py`: `api` — REST API, `full` — бот и API вместе, `migrate` — миграции,
`install` — установка зависимостей.

## База данных

По умолчанию SQLite (`BOT/cryptobot.db`). Таблицы создаются при первом запуске, вспомогательные
скрипты `init_database.py`, `create_settings_tables.py` и `add_missing_columns.py` лежат в каталоге `BOT`.

## Известные проблемы

`BOT/app/schemas/check.py` содержит синтаксическую ошибку в валидаторе суммы: лишняя закрывающая
скобка и потерянный декоратор. Модуль не импортируется без правки.
