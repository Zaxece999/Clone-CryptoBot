import logging
import locale
from app.utils.russian_logger import get_russian_logger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except:
    pass

main_logger = get_russian_logger('cryptobot')
bot_logger = get_russian_logger('telegram_bot')
api_logger = get_russian_logger('api')
service_logger = get_russian_logger('services')
handler_logger = get_russian_logger('handlers')
