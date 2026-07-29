import logging
from app.utils.russian_logger import get_russian_logger
import sys
from typing import Any, Dict
import structlog
from structlog.stdlib import LoggerFactory

from app.config import settings


def setup_logging() -> None:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer() if settings.is_production
            else structlog.dev.ConsoleRenderer(colors=True),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aioredis").setLevel(logging.WARNING)


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


class LoggerMixin:
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        return structlog.get_logger(self.__class__.__name__)


def log_function_call(func_name: str, args: tuple = None, kwargs: dict = None) -> Dict[str, Any]:
    context = {"function": func_name}

    if args:
        context["args"] = args

    if kwargs:
        context["kwargs"] = {k: v for k, v in kwargs.items() if not k.startswith('_')}

    return context


def log_api_call(method: str, endpoint: str, user_id: int = None, **kwargs) -> Dict[str, Any]:
    context = {
        "api_method": method,
        "api_endpoint": endpoint,
    }

    if user_id:
        context["user_id"] = user_id

    context.update(kwargs)
    return context


def log_blockchain_operation(
    currency: str,
    operation: str,
    tx_hash: str = None,
    amount: str = None,
    **kwargs
) -> Dict[str, Any]:
    context = {
        "blockchain_currency": currency,
        "blockchain_operation": operation,
    }

    if tx_hash:
        context["tx_hash"] = tx_hash

    if amount:
        context["amount"] = amount

    context.update(kwargs)
    return context


def log_user_action(
    user_id: int,
    action: str,
    details: dict = None,
    **kwargs
) -> Dict[str, Any]:
    context = {
        "user_id": user_id,
        "user_action": action,
    }

    if details:
        context["action_details"] = details

    context.update(kwargs)
    return context


def log_security_event(
    event_type: str,
    user_id: int = None,
    ip_address: str = None,
    details: dict = None,
    **kwargs
) -> Dict[str, Any]:
    context = {
        "security_event": event_type,
        "severity": "high",
    }

    if user_id:
        context["user_id"] = user_id

    if ip_address:
        context["ip_address"] = ip_address

    if details:
        context["event_details"] = details

    context.update(kwargs)
    return context


def log_performance_metric(
    metric_name: str,
    value: float,
    unit: str = "seconds",
    **kwargs
) -> Dict[str, Any]:
    context = {
        "performance_metric": metric_name,
        "metric_value": value,
        "metric_unit": unit,
    }

    context.update(kwargs)
    return context


def log_async_function(logger_name: str = None):
    def decorator(func):
        import functools
        import time

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)
            start_time = time.time()

            logger.info(
                "Function started",
                **log_function_call(func.__name__, args, kwargs)
            )

            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time

                logger.info(
                    "Function completed",
                    function=func.__name__,
                    execution_time=execution_time,
                )

                return result

            except Exception as e:
                execution_time = time.time() - start_time

                logger.error(
                    "Function failed",
                    function=func.__name__,
                    execution_time=execution_time,
                    error=str(e),
                    exc_info=True,
                )
                raise

        return wrapper
    return decorator


def log_function(logger_name: str = None):
    def decorator(func):
        import functools
        import time

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)
            start_time = time.time()

            logger.info(
                "Function started",
                **log_function_call(func.__name__, args, kwargs)
            )

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                logger.info(
                    "Function completed",
                    function=func.__name__,
                    execution_time=execution_time,
                )

                return result

            except Exception as e:
                execution_time = time.time() - start_time

                logger.error(
                    "Function failed",
                    function=func.__name__,
                    execution_time=execution_time,
                    error=str(e),
                    exc_info=True,
                )
                raise

        return wrapper
    return decorator
