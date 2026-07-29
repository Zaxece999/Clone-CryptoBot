import logging
from typing import Any, Dict, Optional
from functools import wraps
from .russian_logs import translate_log, SERVICE_MESSAGES

class RussianLogger:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def _translate_kwargs(self, **kwargs) -> Dict[str, Any]:
        translated = {}
        for key, value in kwargs.items():
            if key == 'error':
                translated['ошибка'] = value
            elif key == 'user_id':
                translated['пользователь'] = value
            elif key == 'wallet_id':
                translated['кошелек'] = value
            elif key == 'currency':
                translated['валюта'] = value
            elif key == 'network':
                translated['сеть'] = value
            elif key == 'address':
                translated['адрес'] = value
            elif key == 'amount':
                translated['сумма'] = value
            elif key == 'status':
                translated['статус'] = value
            elif key == 'count':
                translated['количество'] = value
            else:
                translated[key] = value
        return translated

    def info(self, msg: str, **kwargs):
        translated_msg = translate_log(msg)
        if kwargs:
            translated_kwargs = self._translate_kwargs(**kwargs)
            self.logger.info(f"{translated_msg} | {translated_kwargs}")
        else:
            self.logger.info(translated_msg)

    def error(self, msg: str, **kwargs):
        translated_msg = translate_log(msg)
        if kwargs:
            translated_kwargs = self._translate_kwargs(**kwargs)
            self.logger.error(f"{translated_msg} | {translated_kwargs}")
        else:
            self.logger.error(translated_msg)

    def warning(self, msg: str, **kwargs):
        translated_msg = translate_log(msg)
        if kwargs:
            translated_kwargs = self._translate_kwargs(**kwargs)
            self.logger.warning(f"{translated_msg} | {translated_kwargs}")
        else:
            self.logger.warning(translated_msg)

    def debug(self, msg: str, **kwargs):
        translated_msg = translate_log(msg)
        if kwargs:
            translated_kwargs = self._translate_kwargs(**kwargs)
            self.logger.debug(f"{translated_msg} | {translated_kwargs}")
        else:
            self.logger.debug(translated_msg)

    def critical(self, msg: str, **kwargs):
        translated_msg = translate_log(msg)
        if kwargs:
            translated_kwargs = self._translate_kwargs(**kwargs)
            self.logger.critical(f"{translated_msg} | {translated_kwargs}")
        else:
            self.logger.critical(translated_msg)

def get_russian_logger(name: str) -> RussianLogger:
    logger = logging.getLogger(name)
    return RussianLogger(logger)
