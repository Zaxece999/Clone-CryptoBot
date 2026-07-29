from typing import Any, Dict, Optional


class CryptoBotException(Exception):
    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(CryptoBotException):
    def __init__(self, message: str = "Ошибка аутентификации", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
            **kwargs
        )


class AuthorizationError(CryptoBotException):
    def __init__(self, message: str = "Недостаточно прав", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
            **kwargs
        )


class InvalidTokenError(AuthenticationError):
    def __init__(self, message: str = "Недействительный токен", **kwargs):
        super().__init__(
            message=message,
            error_code="INVALID_TOKEN",
            **kwargs
        )


class TokenExpiredError(AuthenticationError):
    def __init__(self, message: str = "Токен истек", **kwargs):
        super().__init__(
            message=message,
            error_code="TOKEN_EXPIRED",
            **kwargs
        )


class UserNotFoundError(CryptoBotException):
    def __init__(self, message: str = "Пользователь не найден", **kwargs):
        super().__init__(
            message=message,
            error_code="USER_NOT_FOUND",
            status_code=404,
            **kwargs
        )


class UserAlreadyExistsError(CryptoBotException):
    def __init__(self, message: str = "Пользователь уже существует", **kwargs):
        super().__init__(
            message=message,
            error_code="USER_ALREADY_EXISTS",
            status_code=409,
            **kwargs
        )


class UserBlockedError(CryptoBotException):
    def __init__(self, message: str = "Пользователь заблокирован", **kwargs):
        super().__init__(
            message=message,
            error_code="USER_BLOCKED",
            status_code=403,
            **kwargs
        )


class WalletError(CryptoBotException):
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="WALLET_ERROR",
            status_code=400,
            **kwargs
        )


class InsufficientFundsError(WalletError):
    def __init__(self, message: str = "Недостаточно средств", **kwargs):
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_FUNDS",
            **kwargs
        )


class InvalidAddressError(WalletError):
    def __init__(self, message: str = "Недействительный адрес", **kwargs):
        super().__init__(
            message=message,
            error_code="INVALID_ADDRESS",
            **kwargs
        )


class TransactionError(CryptoBotException):
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="TRANSACTION_ERROR",
            status_code=400,
            **kwargs
        )


class TransactionNotFoundError(TransactionError):
    def __init__(self, message: str = "Транзакция не найдена", **kwargs):
        super().__init__(
            message=message,
            error_code="TRANSACTION_NOT_FOUND",
            status_code=404,
            **kwargs
        )


class TransactionFailedError(TransactionError):
    def __init__(self, message: str = "Транзакция не удалась", **kwargs):
        super().__init__(
            message=message,
            error_code="TRANSACTION_FAILED",
            **kwargs
        )


class CheckError(CryptoBotException):
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="CHECK_ERROR",
            status_code=400,
            **kwargs
        )


class CheckNotFoundError(CheckError):
    def __init__(self, message: str = "Чек не найден", **kwargs):
        super().__init__(
            message=message,
            error_code="CHECK_NOT_FOUND",
            status_code=404,
            **kwargs
        )


class CheckAlreadyActivatedError(CheckError):
    def __init__(self, message: str = "Чек уже активирован", **kwargs):
        super().__init__(
            message=message,
            error_code="CHECK_ALREADY_ACTIVATED",
            **kwargs
        )


class CheckExpiredError(CheckError):
    def __init__(self, message: str = "Чек истек", **kwargs):
        super().__init__(
            message=message,
            error_code="CHECK_EXPIRED",
            **kwargs
        )


class InvalidCheckPasswordError(CheckError):
    def __init__(self, message: str = "Неверный пароль чека", **kwargs):
        super().__init__(
            message=message,
            error_code="INVALID_CHECK_PASSWORD",
            **kwargs
        )


class InvoiceError(CryptoBotException):
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="INVOICE_ERROR",
            status_code=400,
            **kwargs
        )


class InvoiceNotFoundError(InvoiceError):
    def __init__(self, message: str = "Инвойс не найден", **kwargs):
        super().__init__(
            message=message,
            error_code="INVOICE_NOT_FOUND",
            status_code=404,
            **kwargs
        )


class InvoiceAlreadyPaidError(InvoiceError):
    def __init__(self, message: str = "Инвойс уже оплачен", **kwargs):
        super().__init__(
            message=message,
            error_code="INVOICE_ALREADY_PAID",
            **kwargs
        )


class InvoiceExpiredError(InvoiceError):
    def __init__(self, message: str = "Инвойс истек", **kwargs):
        super().__init__(
            message=message,
            error_code="INVOICE_EXPIRED",
            **kwargs
        )


class P2PError(CryptoBotException):
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="P2P_ERROR",
            status_code=400,
            **kwargs
        )


class P2POrderNotFoundError(P2PError):
    def __init__(self, message: str = "P2P ордер не найден", **kwargs):
        super().__init__(
            message=message,
            error_code="P2P_ORDER_NOT_FOUND",
            status_code=404,
            **kwargs
        )


class P2PTradeNotFoundError(P2PError):
    def __init__(self, message: str = "P2P сделка не найдена", **kwargs):
        super().__init__(
            message=message,
            error_code="P2P_TRADE_NOT_FOUND",
            status_code=404,
            **kwargs
        )


class P2PInvalidAmountError(P2PError):
    def __init__(self, message: str = "Недопустимая сумма для P2P сделки", **kwargs):
        super().__init__(
            message=message,
            error_code="P2P_INVALID_AMOUNT",
            **kwargs
        )


class ExchangeError(CryptoBotException):
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="EXCHANGE_ERROR",
            status_code=400,
            **kwargs
        )


class UnsupportedCurrencyError(ExchangeError):
    def __init__(self, message: str = "Неподдерживаемая валюта", **kwargs):
        super().__init__(
            message=message,
            error_code="UNSUPPORTED_CURRENCY",
            **kwargs
        )


class ExchangeRateNotAvailableError(ExchangeError):
    def __init__(self, message: str = "Курс обмена недоступен", **kwargs):
        super().__init__(
            message=message,
            error_code="EXCHANGE_RATE_NOT_AVAILABLE",
            **kwargs
        )


class SubscriptionError(CryptoBotException):
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="SUBSCRIPTION_ERROR",
            status_code=400,
            **kwargs
        )


class SubscriptionNotFoundError(SubscriptionError):
    def __init__(self, message: str = "Подписка не найдена", **kwargs):
        super().__init__(
            message=message,
            error_code="SUBSCRIPTION_NOT_FOUND",
            status_code=404,
            **kwargs
        )


class SubscriptionExpiredError(SubscriptionError):
    def __init__(self, message: str = "Подписка истекла", **kwargs):
        super().__init__(
            message=message,
            error_code="SUBSCRIPTION_EXPIRED",
            **kwargs
        )


class BlockchainError(CryptoBotException):
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="BLOCKCHAIN_ERROR",
            status_code=500,
            **kwargs
        )


class BlockchainConnectionError(BlockchainError):
    def __init__(self, message: str = "Ошибка подключения к блокчейну", **kwargs):
        super().__init__(
            message=message,
            error_code="BLOCKCHAIN_CONNECTION_ERROR",
            **kwargs
        )


class InsufficientGasError(BlockchainError):
    def __init__(self, message: str = "Недостаточно газа для транзакции", **kwargs):
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_GAS",
            **kwargs
        )


class ValidationError(CryptoBotException):
    def __init__(self, message: str, field: str = None, **kwargs):
        details = kwargs.get('details', {})
        if field:
            details['field'] = field

        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details,
            **kwargs
        )


class InvalidAmountError(ValidationError):
    def __init__(self, message: str = "Недопустимая сумма", **kwargs):
        super().__init__(
            message=message,
            error_code="INVALID_AMOUNT",
            **kwargs
        )


class AmountTooSmallError(ValidationError):
    def __init__(self, message: str = "Сумма слишком мала", min_amount: float = None, **kwargs):
        details = kwargs.get('details', {})
        if min_amount:
            details['min_amount'] = min_amount

        super().__init__(
            message=message,
            error_code="AMOUNT_TOO_SMALL",
            details=details,
            **kwargs
        )


class AmountTooLargeError(ValidationError):
    def __init__(self, message: str = "Сумма слишком велика", max_amount: float = None, **kwargs):
        details = kwargs.get('details', {})
        if max_amount:
            details['max_amount'] = max_amount

        super().__init__(
            message=message,
            error_code="AMOUNT_TOO_LARGE",
            details=details,
            **kwargs
        )


class RateLimitError(CryptoBotException):
    def __init__(self, message: str = "Превышен лимит запросов", retry_after: int = None, **kwargs):
        details = kwargs.get('details', {})
        if retry_after:
            details['retry_after'] = retry_after

        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details,
            **kwargs
        )


class ExternalServiceError(CryptoBotException):
    def __init__(self, message: str, service_name: str = None, **kwargs):
        details = kwargs.get('details', {})
        if service_name:
            details['service'] = service_name

        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details=details,
            **kwargs
        )


class ExternalServiceUnavailableError(ExternalServiceError):
    def __init__(self, message: str = "Внешний сервис недоступен", **kwargs):
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_UNAVAILABLE",
            status_code=503,
            **kwargs
        )


class ApiError(CryptoBotException):
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="API_ERROR",
            status_code=400,
            **kwargs
        )


class ApiKeyNotFoundError(ApiError):
    def __init__(self, message: str = "API ключ не найден", **kwargs):
        super().__init__(
            message=message,
            error_code="API_KEY_NOT_FOUND",
            status_code=404,
            **kwargs
        )


class ApiKeyExpiredError(ApiError):
    def __init__(self, message: str = "API ключ истек", **kwargs):
        super().__init__(
            message=message,
            error_code="API_KEY_EXPIRED",
            status_code=401,
            **kwargs
        )


class ApiRateLimitError(ApiError):
    def __init__(self, message: str = "Превышен лимит запросов API", **kwargs):
        super().__init__(
            message=message,
            error_code="API_RATE_LIMIT",
            status_code=429,
            **kwargs
        )


class NotFoundError(CryptoBotException):
    def __init__(self, message: str = "Объект не найден", **kwargs):
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=404,
            **kwargs
        )


class PermissionError(CryptoBotException):
    def __init__(self, message: str = "Недостаточно прав доступа", **kwargs):
        super().__init__(
            message=message,
            error_code="PERMISSION_DENIED",
            status_code=403,
            **kwargs
        )
