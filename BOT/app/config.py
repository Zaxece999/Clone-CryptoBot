import os
from typing import List, Optional
from pydantic import field_validator, ConfigDict
from enum import Enum

try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings
    except ImportError:
        raise ImportError(
            "Не удалось импортировать BaseSettings. "
            "Установите pydantic-settings: pip install pydantic-settings"
        )


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class BlockchainNetwork(str, Enum):
    MAINNET = "mainnet"
    TESTNET = "testnet"


class SupportedCurrency(str, Enum):
    BTC = "BTC"
    ETH = "ETH"
    USDT_ERC20 = "USDT_ERC20"
    USDT_TRC20 = "USDT_TRC20"
    USDT_BEP20 = "USDT_BEP20"
    LTC = "LTC"
    BNB = "BNB"
    TRX = "TRX"
    TON = "TON"
    DOGE = "DOGE"
    SOL = "SOL"
    USDC = "USDC"
    NOT = "NOT"
    TRUMP = "TRUMP"
    MELANIA = "MELANIA"
    PEPE = "PEPE"
    WIF = "WIF"
    BONK = "BONK"
    MAJOR = "MAJOR"
    MY = "MY"
    DOGS = "DOGS"
    MEMHASH = "MEMHASH"
    HMSTR = "HMSTR"
    CATI = "CATI"


class SupportedFiatCurrency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    RUB = "RUB"
    CNY = "CNY"


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    testing: bool = False

    secret_key: str = "your-super-secret-key-change-this-in-production"
    jwt_secret_key: str = "your-jwt-secret-key-change-this-too"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7


    database_url: str = "sqlite:///./cryptobot.db"
    test_database_url: str = "sqlite:///./cryptobot_test.db"
    database_pool_size: int = 20
    database_max_overflow: int = 30


    telegram_bot_token: str = ""
    telegram_webhook_url: Optional[str] = None
    telegram_webhook_secret: Optional[str] = None

    bot_name: str = "CryptoBot Clone"
    bot_username: str = "your_bot"
    bot_description: str = "Криптовалютный бот для работы с цифровыми активами"


    celery_broker_url: str = "memory://"
    celery_result_backend: str = "cache+memory://"
    celery_task_serializer: str = "json"
    celery_result_serializer: str = "json"
    celery_accept_content: List[str] = ["json"]
    celery_timezone: str = "UTC"
    celery_enable_utc: bool = True


    bitcoin_network: BlockchainNetwork = BlockchainNetwork.MAINNET
    bitcoin_rpc_url: str = ""
    bitcoin_rpc_user: str = ""
    bitcoin_rpc_password: str = ""

    ethereum_network: BlockchainNetwork = BlockchainNetwork.MAINNET
    ethereum_rpc_url: str = ""
    ethereum_private_key: str = ""

    bsc_network: BlockchainNetwork = BlockchainNetwork.MAINNET
    bsc_rpc_url: str = "https://bsc-dataseed.binance.org/"
    bsc_private_key: str = ""

    polygon_network: BlockchainNetwork = BlockchainNetwork.MAINNET
    polygon_rpc_url: str = "https://polygon-rpc.com/"
    polygon_private_key: str = ""

    tron_network: BlockchainNetwork = BlockchainNetwork.MAINNET
    tron_rpc_url: str = "https://api.trongrid.io"
    tron_api_key: str = ""
    tron_private_key: str = ""

    ton_network: BlockchainNetwork = BlockchainNetwork.MAINNET
    ton_rpc_url: str = "https://toncenter.com/api/v2/"
    ton_api_key: str = ""

    litecoin_network: BlockchainNetwork = BlockchainNetwork.MAINNET
    litecoin_rpc_url: str = ""
    litecoin_rpc_user: str = ""
    litecoin_rpc_password: str = ""


    coingecko_api_key: str = ""
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"

    coinmarketcap_api_key: str = ""
    coinmarketcap_base_url: str = "https://pro-api.coinmarketcap.com/v1"

    exchange_rates_api_key: str = ""
    exchange_rates_base_url: str = "https://api.exchangerate-api.com/v4"


    wallet_encryption_key: str = "your-wallet-encryption-key-32-chars"
    wallet_encryption_algorithm: str = "AES-256-GCM"

    rate_limit_requests_per_minute: int = 300
    rate_limit_burst: int = 50

    cors_origins: List[str] = ["http://localhost:3000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: List[str] = ["*"]


    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = True
    smtp_ssl: bool = False

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    firebase_project_id: str = ""
    firebase_private_key_id: str = ""
    firebase_private_key: str = ""
    firebase_client_email: str = ""
    firebase_client_id: str = ""


    log_level: str = "INFO"

    sentry_dsn: str = ""
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.1

    prometheus_enabled: bool = True
    prometheus_port: int = 8001


    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_reload: bool = True

    api_docs_url: str = "/docs"
    api_redoc_url: str = "/redoc"
    api_openapi_url: str = "/openapi.json"

    api_version: str = "v1"
    api_prefix: str = "/api/v1"


    upload_dir: str = "./uploads"
    max_upload_size: int = 10485760

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    aws_s3_bucket: str = ""


    transaction_fee_percent: float = 0.5
    p2p_fee_percent: float = 1.0
    exchange_fee_percent: float = 0.25
    withdrawal_fee_percent: float = 0.1

    min_transaction_amount: float = 1.0
    max_transaction_amount_unverified: float = 1000.0
    max_transaction_amount_verified: float = 50000.0
    daily_limit_unverified: float = 5000.0
    daily_limit_verified: float = 100000.0


    timezone: str = "UTC"

    supported_languages: List[str] = ["ru", "en", "zh", "es", "fr"]
    default_language: str = "ru"

    supported_crypto_currencies: List[str] = [
        "BTC", "ETH", "USDT", "LTC", "BNB", "TRX", "TON", "DOGE", "SOL", "USDC"
    ]

    supported_currency_networks: dict = {
        "USDT": ["TON", "TRC20", "SPL", "ERC20", "BEP20"],
        "USDC": ["ERC20", "SPL", "BEP20"],
        "BTC": ["BTC"],
        "ETH": ["ERC20"],
        "LTC": ["LTC"],
        "BNB": ["BEP20"],
        "TRX": ["TRC20"],
        "TON": ["TON"],
        "DOGE": ["DOGE"],
        "SOL": ["SPL"]
    }
    supported_fiat_currencies: List[str] = ["USD", "EUR", "RUB", "CNY"]

    price_update_interval: int = 60
    balance_check_interval: int = 300
    transaction_confirmation_interval: int = 30

    backup_enabled: bool = True
    backup_interval_hours: int = 24
    backup_retention_days: int = 30
    backup_s3_bucket: str = ""


    ssl_enabled: bool = False
    ssl_cert_path: str = "/path/to/cert.pem"
    ssl_key_path: str = "/path/to/key.pem"

    domain: str = "your-domain.com"
    subdomain_api: str = "api"
    subdomain_bot: str = "bot"
    webapp_url: str = "http://localhost:5000"

    worker_processes: int = 4
    worker_connections: int = 1000
    keepalive_timeout: int = 65

    cache_enabled: bool = True
    cache_default_ttl: int = 3600
    cache_max_entries: int = 10000


    @field_validator('telegram_bot_token')
    @classmethod
    def validate_telegram_token(cls, v, info):
        values = info.data if hasattr(info, 'data') else {}
        testing = values.get('testing', False)

        skip_validation = os.getenv('SKIP_TOKEN_VALIDATION', 'false').lower() == 'true'

        if not v and not testing and not skip_validation:
            raise ValueError('Telegram bot token is required')
        return v


    @field_validator('wallet_encryption_key')
    @classmethod
    def validate_encryption_key(cls, v):
        if len(v) < 32:
            raise ValueError('Wallet encryption key must be at least 32 characters')
        return v

    @field_validator('cors_origins')
    @classmethod
    def validate_cors_origins(cls, v):
        if not isinstance(v, list):
            return [v] if v else []
        return v


    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        return self.environment == Environment.TESTING

    @property
    def encryption_key(self) -> str:
        return self.wallet_encryption_key

    @property
    def database_url_sync(self) -> str:
        return self.database_url.replace('+asyncpg', '')

    @property
    def database_url_async(self) -> str:
        url = self.database_url
        if url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "sqlite+aiosqlite:///")
        if url.startswith("sqlite+aiosqlite:///"):
            return url
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            return url.replace("postgresql://", "postgresql+asyncpg://")
        return url

    def get_blockchain_config(self, currency: str) -> dict:
        currency_configs = {
            'BTC': {
                'network': self.bitcoin_network,
                'rpc_url': self.bitcoin_rpc_url,
                'rpc_user': self.bitcoin_rpc_user,
                'rpc_password': self.bitcoin_rpc_password,
            },
            'ETH': {
                'network': self.ethereum_network,
                'rpc_url': self.ethereum_rpc_url,
                'private_key': self.ethereum_private_key,
            },
            'USDT_ERC20': {
                'network': self.ethereum_network,
                'rpc_url': self.ethereum_rpc_url,
                'private_key': self.ethereum_private_key,
            },
            'BNB': {
                'network': self.bsc_network,
                'rpc_url': self.bsc_rpc_url,
                'private_key': self.bsc_private_key,
            },
            'USDT_BEP20': {
                'network': self.bsc_network,
                'rpc_url': self.bsc_rpc_url,
                'private_key': self.bsc_private_key,
            },
            'TRX': {
                'network': self.tron_network,
                'rpc_url': self.tron_rpc_url,
                'api_key': self.tron_api_key,
                'private_key': self.tron_private_key,
            },
            'USDT_TRC20': {
                'network': self.tron_network,
                'rpc_url': self.tron_rpc_url,
                'api_key': self.tron_api_key,
                'private_key': self.tron_private_key,
            },
            'TON': {
                'network': self.ton_network,
                'rpc_url': self.ton_rpc_url,
                'api_key': self.ton_api_key,
            },

            'LTC': {
                'network': self.litecoin_network,
                'rpc_url': self.litecoin_rpc_url,
                'rpc_user': self.litecoin_rpc_user,
                'rpc_password': self.litecoin_rpc_password,
            },
        }

        return currency_configs.get(currency, {})


settings = Settings()
