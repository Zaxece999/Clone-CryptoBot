import structlog
import asyncio
from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.wallet import Wallet
from app.services.wallet import wallet_service
from app.services.exchange_rates import exchange_rate_service
from app.config import settings

logger = structlog.get_logger(__name__)

async def get_wallet_balance_with_error_handling(db: AsyncSession, wallet: Wallet) -> Tuple[str, Optional[float]]:
    logger.info(
        "Getting wallet balance",
        wallet_id=wallet.id,
        user_id=wallet.user_id,
        currency=wallet.currency
    )

    try:
        balance = await wallet_service.get_wallet_total_balance(db, wallet, update_first=True)
        logger.info(
            "Wallet balance retrieved",
            wallet_id=wallet.id,
            user_id=wallet.user_id,
            currency=wallet.currency,
            balance=balance
        )

        try:
            rate = await exchange_rate_service.get_exchange_rate(wallet.currency, "USD")
            if rate and rate > 0:
                usd_value = float(balance) * rate
                logger.info(
                    "Exchange rate retrieved",
                    wallet_id=wallet.id,
                    currency=wallet.currency,
                    rate=rate,
                    usd_value=usd_value
                )
                return balance, usd_value
            else:
                logger.warning(
                    "No exchange rate found",
                    wallet_id=wallet.id,
                    currency=wallet.currency
                )
                return balance, None
        except Exception as e:
            logger.warning(f"Failed to get exchange rate for {wallet.currency}", error=str(e))
            return balance, None

    except Exception as e:
        logger.error(
            f"Failed to get balance for {wallet.currency} wallet",
            wallet_id=wallet.id,
            user_id=wallet.user_id,
            error=str(e)
        )
        return "ERROR", None

async def get_all_wallets_balances(db: AsyncSession, user_id: int) -> Dict[str, Tuple[str, Optional[float], str]]:
    logger.info("Getting all wallet balances", user_id=user_id)

    try:
        result = await db.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        wallets = result.scalars().all()

        logger.info("👛 Найдены кошельки для пользователя", user_id=user_id, wallet_count=len(wallets))

        if not wallets:
            logger.info("👛 Кошельки не найдены для пользователя", user_id=user_id)
            return {}

        tasks = [get_wallet_balance_with_error_handling(db, wallet) for wallet in wallets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        currency_balances = {}
        currency_usd_values = {}
        currency_frozen_balances = {}

        for wallet, result in zip(wallets, results):
            if isinstance(result, Exception):
                logger.error(
                    "Balance check failed for wallet",
                    user_id=user_id,
                    wallet_id=wallet.id,
                    currency=wallet.currency,
                    error=str(result)
                )
                currency_balances[wallet.currency] = "ERROR"
                currency_usd_values[wallet.currency] = None
                currency_frozen_balances[wallet.currency] = "0"
            else:
                balance, usd_value = result
                logger.info(
                    "Balance retrieved for wallet",
                    user_id=user_id,
                    wallet_id=wallet.id,
                    currency=wallet.currency,
                    network=wallet.network,
                    balance=balance,
                    usd_value=usd_value
                )

                if wallet.currency not in currency_balances or currency_balances[wallet.currency] == "ERROR":
                    if balance != "ERROR":
                        currency_balances[wallet.currency] = balance
                        currency_usd_values[wallet.currency] = usd_value or 0
                        currency_frozen_balances[wallet.currency] = wallet.frozen_balance
                else:
                    if balance != "ERROR":
                        try:
                            current_balance = Decimal(currency_balances[wallet.currency])
                            new_balance = Decimal(balance)
                            currency_balances[wallet.currency] = str(current_balance + new_balance)

                            if usd_value is not None:
                                current_usd = currency_usd_values[wallet.currency] or 0
                                currency_usd_values[wallet.currency] = current_usd + usd_value

                            current_frozen = Decimal(currency_frozen_balances[wallet.currency])
                            new_frozen = Decimal(wallet.frozen_balance)
                            currency_frozen_balances[wallet.currency] = str(current_frozen + new_frozen)
                        except Exception as e:
                            logger.error(f"Error summing balances for {wallet.currency}", error=str(e))

        balances = {}
        for currency in currency_balances:
            balance = currency_balances[currency]
            usd_value = currency_usd_values.get(currency)
            frozen_balance = currency_frozen_balances.get(currency, "0")
            balances[currency] = (balance, usd_value, frozen_balance)

        logger.info(
            "All wallet balances retrieved and grouped",
            user_id=user_id,
            currencies=list(balances.keys())
        )

        return balances

    except Exception as e:
        logger.error(
            "Failed to get wallets balances",
            user_id=user_id,
            error=str(e)
        )
        return {}

async def get_total_usd_balance(balances: Dict[str, Tuple[str, Optional[float], str]]) -> float:
    total_usd = 0.0

    for currency, (balance, usd_value, frozen_balance) in balances.items():
        if usd_value is not None and balance != "ERROR":
            total_usd += usd_value

    return total_usd

async def get_wallets_balances_by_network(db: AsyncSession, user_id: int, currency: str) -> Dict[str, Tuple[str, Optional[float], str]]:
    logger.info("Getting wallet balances by network", user_id=user_id, currency=currency)

    try:
        result = await db.execute(
            select(Wallet).where(
                Wallet.user_id == user_id,
                Wallet.currency == currency.upper()
            )
        )
        wallets = result.scalars().all()

        logger.info("💰 Найдены кошельки для валюты", user_id=user_id, currency=currency, wallet_count=len(wallets))

        if not wallets:
            logger.info("❌ Кошельки не найдены для валюты", user_id=user_id, currency=currency)
            return {}

        tasks = [get_wallet_balance_with_error_handling(db, wallet) for wallet in wallets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        network_balances = {}
        for wallet, result in zip(wallets, results):
            if isinstance(result, Exception):
                logger.error(
                    "Balance check failed for wallet",
                    user_id=user_id,
                    wallet_id=wallet.id,
                    currency=wallet.currency,
                    network=wallet.network,
                    error=str(result)
                )
                network_balances[wallet.network] = ("ERROR", None, "0")
            else:
                balance, usd_value = result
                logger.info(
                    "Balance retrieved for wallet network",
                    user_id=user_id,
                    wallet_id=wallet.id,
                    currency=wallet.currency,
                    network=wallet.network,
                    balance=balance,
                    usd_value=usd_value
                )
                network_balances[wallet.network] = (balance, usd_value, wallet.frozen_balance)

        logger.info(
            "All network balances retrieved",
            user_id=user_id,
            currency=currency,
            networks=list(network_balances.keys())
        )

        return network_balances

    except Exception as e:
        logger.error(
            "Failed to get network balances",
            user_id=user_id,
            currency=currency,
            error=str(e)
        )
        return {}

def format_balance_display(currency: str, balance: str, usd_value: Optional[float] = None, frozen_balance: str = "0") -> str:
    if balance == "ERROR":
        return f"🪙 {currency}: ERROR ❌"

    try:
        total_balance = Decimal(balance)
        frozen_amount = Decimal(frozen_balance)
        available_balance = total_balance - frozen_amount

        balance_text = f"🪙 {currency}: {available_balance} {currency}"

        if frozen_amount > 0:
            balance_text += f" ({frozen_balance} {currency} удержано)"

    except Exception as e:
        logger.error(f"Error calculating available balance for {currency}", error=str(e))
        balance_text = f"🪙 {currency}: {balance} {currency}"

    if usd_value is not None:
        balance_text += f"\n   💵 ≈ ${usd_value:.2f} USD"

    return balance_text
