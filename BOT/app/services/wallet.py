import structlog
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime
from decimal import Decimal
import asyncio

from app.models.user import User
from app.models.wallet import Wallet, WalletStatus
from app.models.transaction import Transaction, TransactionType, TransactionStatus, TransactionDirection
from app.utils.security import encrypt_data, decrypt_data
from app.config import settings

logger = structlog.get_logger(__name__)


class WalletService:
    def __init__(self):
        from app.config import settings
        self.supported_currencies = settings.supported_crypto_currencies
        self.supported_currency_networks = settings.supported_currency_networks

    async def create_wallet(
        self,
        db: AsyncSession,
        user: User,
        currency: str,
        network: Optional[str] = None,
        wallet_name: Optional[str] = None,
        set_as_default: bool = True
    ) -> Wallet:

        currency = currency.upper()

        if currency not in self.supported_currencies:
            raise ValueError(f"Unsupported currency: {currency}")

        if not network:
            if currency in self.supported_currency_networks:
                network = self.supported_currency_networks[currency][0]
            else:
                network = currency

        network = network.upper()

        if currency in self.supported_currency_networks:
            if network not in self.supported_currency_networks[currency]:
                raise ValueError(f"Unsupported network {network} for currency {currency}")

        existing_wallet = await self.get_user_wallet(db, user.id, currency, network)
        if existing_wallet and set_as_default:
            existing_wallet.is_default = "true"
            await db.commit()
            return existing_wallet

        try:
            from app.services.wallet_local import create_local_wallet
            wallet = await create_local_wallet(db=db, user=user, currency=currency, network=network)

            if set_as_default:
                await self._unset_default_wallets(db, user.id, currency, network)
                wallet.is_default = "true"

            db.add(wallet)

            logger.info(
                "Wallet created",
                user_id=user.id,
                wallet_id=wallet.id,
                currency=currency,
                network=network,
                is_default=set_as_default
            )

            return wallet

        except Exception as e:
            logger.error(
                "Failed to create wallet",
                user_id=user.id,
                currency=currency,
                network=network,
                error=str(e)
            )
            raise

    async def get_user_wallets(
        self,
        db: AsyncSession,
        user_id: int,
        currency: Optional[str] = None,
        include_addresses: bool = False
    ) -> List[Wallet]:

        try:
            query = select(Wallet).where(Wallet.user_id == user_id)

            if currency:
                query = query.where(Wallet.currency == currency.upper())

            query = query.order_by(
                Wallet.created_at.asc()
            )

            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error("❌ Ошибка получения кошельков пользователя", error=str(e))
            return []

    async def get_user_wallet(
        self,
        db: AsyncSession,
        user_id: int,
        currency: str,
        network: Optional[str] = None,
        default_only: bool = True
    ) -> Optional[Wallet]:

        try:
            query = select(Wallet).where(
                and_(
                    Wallet.user_id == user_id,
                    Wallet.currency == currency.upper()
                )
            )


            if default_only:
                query = query.where(Wallet.is_default == "true")

            query = query.order_by(Wallet.created_at.asc())

            result = await db.execute(query)
            return result.scalars().first()
        except Exception as e:
            logger.error("❌ Ошибка получения кошелька пользователя", error=str(e))
            return None

    async def update_balances(
        self,
        db: AsyncSession,
        wallet: Wallet
    ) -> Dict[str, str]:
        balances = {wallet.address: wallet.balance}
        return balances

    async def get_wallet_total_balance(
        self,
        db: AsyncSession,
        wallet: Wallet,
        update_first: bool = False
    ) -> str:

        logger.info(
            "Getting wallet total balance",
            wallet_id=wallet.id,
            currency=wallet.currency,
            current_balance=wallet.balance,
            update_first=update_first
        )

        if update_first:
            await self.update_balances(db, wallet)

        logger.info(
            "Wallet total balance retrieved",
            wallet_id=wallet.id,
            currency=wallet.currency,
            balance=wallet.balance
        )
        return wallet.balance

    async def _unset_default_wallets(
        self,
        db: AsyncSession,
        user_id: int,
        currency: str,
        network: str
    ):

        result = await db.execute(
            select(Wallet).where(
                and_(
                    Wallet.user_id == user_id,
                    Wallet.currency == currency,
                    Wallet.network == network,
                    Wallet.is_default == "true"
                )
            )
        )

        wallets = result.scalars().all()
        for wallet in wallets:
            wallet.is_default = "false"

    async def create_default_wallets(
        self,
        db: AsyncSession,
        user: User,
        currency_networks: Optional[List[tuple]] = None
    ) -> List[Wallet]:

        if not currency_networks:
            currency_networks = [
                ("BTC", "BTC"),
                ("ETH", "ERC20"),
                ("USDT", "TRC20"),
                ("TON", "TON"),
                ("TRX", "TRC20")
            ]

        created_wallets = []

        try:
            for currency, network in currency_networks:
                try:
                    existing_wallet = await self.get_user_wallet(db, user.id, currency, network)
                    if existing_wallet:
                        continue

                    wallet = await self.create_wallet(
                        db, user, currency, network,
                        set_as_default=True
                    )
                    created_wallets.append(wallet)

                except Exception as e:
                    logger.error(
                        "Failed to create default wallet",
                        user_id=user.id,
                        currency=currency,
                        network=network,
                        error=str(e)
                    )

            await db.commit()

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to create default wallets",
                user_id=user.id,
                error=str(e)
            )
            raise

        return created_wallets

    async def get_all_currency_network_wallets(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict[str, List[Wallet]]:

        wallets = await self.get_user_wallets(db, user_id)

        grouped_wallets = {}
        for wallet in wallets:
            if wallet.currency not in grouped_wallets:
                grouped_wallets[wallet.currency] = []
            grouped_wallets[wallet.currency].append(wallet)

        return grouped_wallets

    async def get_unused_address(self, db: AsyncSession, wallet: Wallet):
        return wallet

    async def get_wallet_addresses(self, db: AsyncSession, wallet_id: str):
        result = await db.execute(select(Wallet).where(Wallet.id == wallet_id))
        wallet = result.scalars().first()

        if not wallet:
            return []

        return [wallet]

    async def create_transaction(
        self,
        db: AsyncSession,
        user_id: int,
        wallet_id: str,
        transaction_type: TransactionType,
        currency: str,
        amount: str,
        direction: TransactionDirection = TransactionDirection.OUTGOING,
        description: Optional[str] = None,
        related_object_type: Optional[str] = None,
        related_object_id: Optional[str] = None,
        related_user_id: Optional[int] = None,
        fee: str = "0",
        network: Optional[str] = None
    ) -> Transaction:

        try:
            transaction = Transaction(
                user_id=user_id,
                wallet_id=wallet_id,
                type=transaction_type,
                status=TransactionStatus.PENDING,
                direction=direction,
                currency=currency.upper(),
                amount=amount,
                fee=fee,
                description=description,
                related_object_type=related_object_type,
                related_object_id=related_object_id,
                related_user_id=related_user_id,
                network=network
            )

            db.add(transaction)
            await db.flush()

            logger.info(
                "Transaction created",
                transaction_id=transaction.id,
                user_id=user_id,
                wallet_id=wallet_id,
                type=transaction_type.value,
                currency=currency,
                amount=amount
            )

            return transaction

        except Exception as e:
            logger.error(
                "Failed to create transaction",
                user_id=user_id,
                wallet_id=wallet_id,
                type=transaction_type.value if transaction_type else None,
                currency=currency,
                amount=amount,
                error=str(e)
            )
            raise


wallet_service = WalletService()
