import structlog
import secrets
import hashlib
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
from eth_account import Account
from tronpy.keys import PrivateKey as TronPrivateKey
from app.models.wallet import Wallet
from app.utils.security import encrypt_data
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings

logger = structlog.get_logger(__name__)

NETWORK_COIN_MAP = {
    "BTC": Bip44Coins.BITCOIN,
    "ERC20": Bip44Coins.ETHEREUM,
    "LTC": Bip44Coins.LITECOIN,
    "DOGE": Bip44Coins.DOGECOIN,
    "BEP20": Bip44Coins.BINANCE_CHAIN,
}

def generate_sol_wallet():
    private_key_bytes = secrets.token_bytes(32)
    private_key_hex = private_key_bytes.hex()

    hash_obj = hashlib.sha256(private_key_bytes)
    public_key_hash = hash_obj.hexdigest()[:44]
    address = f"Sol{public_key_hash}"

    return address, private_key_hex

def generate_ton_wallet():
    private_key_bytes = secrets.token_bytes(32)
    private_key_hex = private_key_bytes.hex()

    hash_obj = hashlib.sha256(private_key_bytes)
    public_key_hash = hash_obj.hexdigest()[:48]

    address = f"EQ{public_key_hash}"

    return address, private_key_hex

async def create_local_wallet(db: AsyncSession, user, currency: str, network: str) -> Wallet:
    currency = currency.upper()
    network = network.upper()
    logger.info("Создаю локальный кошелек", user_id=user.id, currency=currency, network=network)

    result = await db.execute(
        select(Wallet).where(
            Wallet.user_id == user.id,
            Wallet.currency == currency,
            Wallet.network == network
        )
    )
    wallet = result.scalars().first()
    if wallet:
        logger.info("Кошелек уже существует", user_id=user.id, currency=currency, network=network, wallet_id=wallet.id)
        return wallet

    mnemonic = Bip39MnemonicGenerator().FromWordsNumber(12)
    seed = Bip39SeedGenerator(mnemonic).Generate()

    address = None
    privkey = None

    try:
        if network in NETWORK_COIN_MAP:
            bip_wallet = Bip44.FromSeed(seed, NETWORK_COIN_MAP[network]).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
            address = bip_wallet.PublicKey().ToAddress()
            privkey = bip_wallet.PrivateKey().Raw().ToHex()
            logger.info(f"Создан {currency} кошелек в сети {network} через BIP44", address=address)

        elif network == "TRC20":
            priv = TronPrivateKey.random()
            address = priv.public_key.to_base58check_address()
            privkey = priv.hex()
            logger.info(f"Создан {currency} кошелек в сети TRC20", address=address)

        elif network == "SPL":
            address, privkey = generate_sol_wallet()
            logger.info(f"Создан {currency} кошелек в сети SPL (упрощенная версия)", address=address)

        elif network == "TON":
            address, privkey = generate_ton_wallet()
            logger.info(f"Создан {currency} кошелек в сети TON (упрощенная версия)", address=address)

        else:
            raise ValueError(f"Unsupported network: {network} for currency: {currency}")

        privkey_encrypted = encrypt_data(privkey, settings.wallet_encryption_key)

        wallet = Wallet(
            user_id=user.id,
            currency=currency,
            network=network,
            address=address,
            private_key_encrypted=privkey_encrypted
        )

        logger.info("Локальный кошелек успешно создан",
                   user_id=user.id, currency=currency, network=network, address=address)
        return wallet

    except Exception as e:
        logger.error(f"Ошибка создания {currency} кошелька в сети {network}",
                    user_id=user.id, currency=currency, network=network, error=str(e))
        raise e
