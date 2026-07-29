from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import asyncio
import hashlib
import secrets
from cryptography.fernet import Fernet
import structlog

from app.models.blockchain import (
    BlockchainAddress, BlockchainTransaction, BlockchainNode, TokenContract,
    BlockchainBlock, WithdrawalRequest, DepositAddress,
    BlockchainNetwork, TransactionStatus, AddressType
)
from app.models.user import User
from app.models.wallet import WalletBalance
from app.config import settings
from app.utils.exceptions import ValidationError, InsufficientFundsError

logger = structlog.get_logger(__name__)


class BlockchainService:
    def __init__(self):
        if settings.encryption_key and len(settings.encryption_key) >= 32:
            import base64
            key_bytes = settings.encryption_key[:32].encode('utf-8')
            key_bytes = key_bytes.ljust(32, b'0')
            self.encryption_key = base64.urlsafe_b64encode(key_bytes)
        else:
            self.encryption_key = Fernet.generate_key()

        self.cipher = Fernet(self.encryption_key)


    async def create_deposit_address(
        self,
        db: AsyncSession,
        user: User,
        currency: str,
        network: BlockchainNetwork
    ) -> DepositAddress:
        try:
            existing_address = await self.get_user_deposit_address(db, user.id, currency, network)
            if existing_address and existing_address.is_active:
                return existing_address

            address = await self._generate_address(network, currency)
            memo = await self._generate_memo(network) if self._requires_memo(network) else None

            deposit_address = DepositAddress(
                user_id=user.id,
                currency=currency,
                network=network,
                address=address,
                memo=memo,
                is_active=True
            )

            db.add(deposit_address)
            await db.commit()
            await db.refresh(deposit_address)

            logger.info(
                "Deposit address created",
                user_id=user.id,
                currency=currency,
                network=network.value,
                address=address[:10] + "..."
            )

            return deposit_address

        except Exception as e:
            await db.rollback()
            logger.error("Failed to create deposit address", error=str(e), exc_info=True)
            raise ValidationError("Не удалось создать адрес для депозита")

    async def get_user_deposit_address(
        self,
        db: AsyncSession,
        user_id: int,
        currency: str,
        network: BlockchainNetwork
    ) -> Optional[DepositAddress]:
        result = await db.execute(
            select(DepositAddress)
            .where(
                and_(
                    DepositAddress.user_id == user_id,
                    DepositAddress.currency == currency,
                    DepositAddress.network == network,
                    DepositAddress.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_user_addresses(
        self,
        db: AsyncSession,
        user_id: int,
        network: Optional[BlockchainNetwork] = None
    ) -> List[DepositAddress]:
        query = select(DepositAddress).where(DepositAddress.user_id == user_id)

        if network:
            query = query.where(DepositAddress.network == network)

        query = query.order_by(desc(DepositAddress.created_at))

        result = await db.execute(query)
        return result.scalars().all()


    async def create_withdrawal_request(
        self,
        db: AsyncSession,
        user: User,
        currency: str,
        network: BlockchainNetwork,
        to_address: str,
        amount: Decimal,
        memo: Optional[str] = None
    ) -> WithdrawalRequest:
        try:
            balance = await self._get_user_balance(db, user.id, currency)
            if balance < amount:
                raise InsufficientFundsError("Недостаточно средств для вывода")

            fee = await self._calculate_withdrawal_fee(network, currency, amount)
            total_amount = amount + fee

            if balance < total_amount:
                raise InsufficientFundsError("Недостаточно средств для покрытия комиссии")

            if not await self._validate_address(network, to_address):
                raise ValidationError("Неверный адрес получателя")

            withdrawal = WithdrawalRequest(
                user_id=user.id,
                currency=currency,
                network=network,
                amount=amount,
                fee=fee,
                to_address=to_address,
                memo=memo,
                status=TransactionStatus.PENDING,
                internal_id=self._generate_internal_id(),
                requires_approval=await self._requires_approval(amount, currency)
            )

            db.add(withdrawal)
            await db.commit()
            await db.refresh(withdrawal)

            await self._freeze_balance(db, user.id, currency, total_amount)

            logger.info(
                "Withdrawal request created",
                user_id=user.id,
                currency=currency,
                amount=str(amount),
                fee=str(fee),
                to_address=to_address[:10] + "..."
            )

            return withdrawal

        except Exception as e:
            await db.rollback()
            logger.error("Failed to create withdrawal request", error=str(e), exc_info=True)
            raise

    async def process_withdrawal_request(
        self,
        db: AsyncSession,
        withdrawal_id: int
    ) -> Optional[BlockchainTransaction]:
        try:
            withdrawal = await db.get(WithdrawalRequest, withdrawal_id)
            if not withdrawal or withdrawal.status != TransactionStatus.PENDING:
                return None

            if withdrawal.requires_approval and not withdrawal.approved_at:
                logger.info("Withdrawal requires approval", withdrawal_id=withdrawal_id)
                return None

            tx_hash = await self._send_transaction(
                network=withdrawal.network,
                currency=withdrawal.currency,
                to_address=withdrawal.to_address,
                amount=withdrawal.amount,
                memo=withdrawal.memo
            )

            withdrawal.status = TransactionStatus.CONFIRMING
            withdrawal.tx_hash = tx_hash
            withdrawal.processed_at = datetime.utcnow()

            transaction = BlockchainTransaction(
                user_id=withdrawal.user_id,
                address_id=None,
                tx_hash=tx_hash,
                network=withdrawal.network,
                currency=withdrawal.currency,
                from_address="",
                to_address=withdrawal.to_address,
                amount=withdrawal.amount,
                fee=withdrawal.fee,
                status=TransactionStatus.CONFIRMING,
                internal_id=withdrawal.internal_id,
                memo=withdrawal.memo
            )

            db.add(transaction)
            await db.commit()
            await db.refresh(transaction)

            logger.info(
                "Withdrawal processed",
                withdrawal_id=withdrawal_id,
                tx_hash=tx_hash
            )

            return transaction

        except Exception as e:
            await db.rollback()
            logger.error("Failed to process withdrawal", error=str(e), exc_info=True)
            withdrawal.status = TransactionStatus.FAILED
            withdrawal.error_message = str(e)
            await db.commit()
            return None

    async def update_transaction_status(
        self,
        db: AsyncSession,
        tx_hash: str,
        status: TransactionStatus,
        confirmations: int = 0,
        block_number: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> Optional[BlockchainTransaction]:
        try:
            result = await db.execute(
                select(BlockchainTransaction)
                .where(BlockchainTransaction.tx_hash == tx_hash)
            )
            transaction = result.scalar_one_or_none()

            if not transaction:
                return None

            transaction.status = status
            transaction.confirmations = confirmations
            transaction.updated_at = datetime.utcnow()

            if block_number:
                transaction.block_number = block_number

            if error_message:
                transaction.error_message = error_message

            if status == TransactionStatus.CONFIRMED:
                transaction.confirmed_at = datetime.utcnow()

                if transaction.to_address in await self._get_our_addresses(db, transaction.network):
                    await self._credit_balance(
                        db,
                        transaction.user_id,
                        transaction.currency,
                        transaction.amount
                    )

            await db.commit()
            await db.refresh(transaction)

            logger.info(
                "Transaction status updated",
                tx_hash=tx_hash,
                status=status.value,
                confirmations=confirmations
            )

            return transaction

        except Exception as e:
            await db.rollback()
            logger.error("Failed to update transaction status", error=str(e), exc_info=True)
            return None


    async def scan_blockchain_for_deposits(
        self,
        db: AsyncSession,
        network: BlockchainNetwork,
        from_block: Optional[int] = None
    ) -> List[BlockchainTransaction]:
        try:
            our_addresses = await self._get_our_addresses(db, network)
            if not our_addresses:
                return []

            if from_block is None:
                from_block = await self._get_last_processed_block(db, network)

            current_block = await self._get_current_block_number(network)
            new_transactions = []

            for block_num in range(from_block + 1, current_block + 1):
                block_transactions = await self._scan_block_for_deposits(
                    db, network, block_num, our_addresses
                )
                new_transactions.extend(block_transactions)

                await self._update_last_processed_block(db, network, block_num)

            logger.info(
                "Blockchain scan completed",
                network=network.value,
                from_block=from_block,
                to_block=current_block,
                new_deposits=len(new_transactions)
            )

            return new_transactions

        except Exception as e:
            logger.error("Failed to scan blockchain", error=str(e), exc_info=True)
            return []

    async def update_transaction_confirmations(
        self,
        db: AsyncSession,
        network: BlockchainNetwork
    ) -> int:
        try:
            result = await db.execute(
                select(BlockchainTransaction)
                .where(
                    and_(
                        BlockchainTransaction.network == network,
                        BlockchainTransaction.status.in_([
                            TransactionStatus.PENDING,
                            TransactionStatus.CONFIRMING
                        ])
                    )
                )
            )
            transactions = result.scalars().all()

            current_block = await self._get_current_block_number(network)
            updated_count = 0

            for tx in transactions:
                if tx.block_number:
                    confirmations = current_block - tx.block_number + 1

                    if confirmations != tx.confirmations:
                        tx.confirmations = confirmations

                        if confirmations >= tx.required_confirmations:
                            tx.status = TransactionStatus.CONFIRMED
                            tx.confirmed_at = datetime.utcnow()

                        updated_count += 1

            await db.commit()

            logger.info(
                "Transaction confirmations updated",
                network=network.value,
                updated_count=updated_count
            )

            return updated_count

        except Exception as e:
            await db.rollback()
            logger.error("Failed to update confirmations", error=str(e), exc_info=True)
            return 0


    async def get_active_node(
        self,
        db: AsyncSession,
        network: BlockchainNetwork
    ) -> Optional[BlockchainNode]:
        result = await db.execute(
            select(BlockchainNode)
            .where(
                and_(
                    BlockchainNode.network == network,
                    BlockchainNode.is_active == True
                )
            )
            .order_by(desc(BlockchainNode.is_primary), desc(BlockchainNode.priority))
        )
        return result.scalar_one_or_none()

    async def update_node_stats(
        self,
        db: AsyncSession,
        node_id: int,
        success: bool,
        error_message: Optional[str] = None
    ):
        try:
            node = await db.get(BlockchainNode, node_id)
            if not node:
                return

            node.total_requests += 1
            node.last_request_at = datetime.utcnow()

            if not success:
                node.failed_requests += 1
                node.last_error_at = datetime.utcnow()
                node.last_error_message = error_message

            await db.commit()

        except Exception as e:
            logger.error("Failed to update node stats", error=str(e), exc_info=True)


    async def _generate_address(self, network: BlockchainNetwork, currency: str) -> str:
        if network == BlockchainNetwork.BITCOIN:
            return f"bc1q{secrets.token_hex(20)}"
        elif network == BlockchainNetwork.ETHEREUM:
            return f"0x{secrets.token_hex(20)}"
        elif network == BlockchainNetwork.TRON:
            return f"T{secrets.token_hex(17)}"
        else:
            return f"{network.value}_{secrets.token_hex(16)}"

    async def _generate_memo(self, network: BlockchainNetwork) -> Optional[str]:
        if network in [BlockchainNetwork.TRON]:
            return str(secrets.randbelow(1000000000))
        return None

    def _requires_memo(self, network: BlockchainNetwork) -> bool:
        return network in [BlockchainNetwork.TRON]

    async def _validate_address(self, network: BlockchainNetwork, address: str) -> bool:
        if not address:
            return False

        if network == BlockchainNetwork.BITCOIN:
            return address.startswith(('1', '3', 'bc1'))
        elif network == BlockchainNetwork.ETHEREUM:
            return address.startswith('0x') and len(address) == 42
        elif network == BlockchainNetwork.TRON:
            return address.startswith('T') and len(address) == 34

        return len(address) > 10

    async def _calculate_withdrawal_fee(
        self,
        network: BlockchainNetwork,
        currency: str,
        amount: Decimal
    ) -> Decimal:
        base_fees = {
            BlockchainNetwork.BITCOIN: Decimal("0.0005"),
            BlockchainNetwork.ETHEREUM: Decimal("0.005"),
            BlockchainNetwork.TRON: Decimal("1.0"),
            BlockchainNetwork.BINANCE_SMART_CHAIN: Decimal("0.001"),
        }
        return base_fees.get(network, Decimal("0.001"))

    async def _requires_approval(self, amount: Decimal, currency: str) -> bool:
        approval_limits = {
            "BTC": Decimal("1.0"),
            "ETH": Decimal("10.0"),
            "USDT": Decimal("10000.0"),
        }
        limit = approval_limits.get(currency, Decimal("1000.0"))
        return amount > limit

    def _generate_internal_id(self) -> str:
        return f"WD_{int(datetime.utcnow().timestamp())}_{secrets.token_hex(8)}"

    async def _get_user_balance(self, db: AsyncSession, user_id: int, currency: str) -> Decimal:
        result = await db.execute(
            select(WalletBalance.balance)
            .where(
                and_(
                    WalletBalance.user_id == user_id,
                    WalletBalance.currency == currency
                )
            )
        )
        balance = result.scalar_one_or_none()
        return balance or Decimal("0")

    async def _freeze_balance(self, db: AsyncSession, user_id: int, currency: str, amount: Decimal):
        pass

    async def _credit_balance(self, db: AsyncSession, user_id: int, currency: str, amount: Decimal):
        pass

    async def _send_transaction(
        self,
        network: BlockchainNetwork,
        currency: str,
        to_address: str,
        amount: Decimal,
        memo: Optional[str] = None
    ) -> str:
        return f"0x{secrets.token_hex(32)}"

    async def _get_our_addresses(self, db: AsyncSession, network: BlockchainNetwork) -> List[str]:
        result = await db.execute(
            select(DepositAddress.address)
            .where(
                and_(
                    DepositAddress.network == network,
                    DepositAddress.is_active == True
                )
            )
        )
        return [addr[0] for addr in result.fetchall()]

    async def _get_last_processed_block(self, db: AsyncSession, network: BlockchainNetwork) -> int:
        result = await db.execute(
            select(func.max(BlockchainBlock.block_number))
            .where(
                and_(
                    BlockchainBlock.network == network,
                    BlockchainBlock.is_processed == True
                )
            )
        )
        last_block = result.scalar_one_or_none()
        return last_block or 0

    async def _get_current_block_number(self, network: BlockchainNetwork) -> int:
        return 1000000

    async def _scan_block_for_deposits(
        self,
        db: AsyncSession,
        network: BlockchainNetwork,
        block_number: int,
        our_addresses: List[str]
    ) -> List[BlockchainTransaction]:
        return []

    async def _update_last_processed_block(
        self,
        db: AsyncSession,
        network: BlockchainNetwork,
        block_number: int
    ):
        block = BlockchainBlock(
            network=network,
            block_number=block_number,
            block_hash=f"0x{secrets.token_hex(32)}",
            timestamp=datetime.utcnow(),
            is_processed=True,
            processed_at=datetime.utcnow()
        )
        db.add(block)
        await db.commit()


blockchain_service = BlockchainService()
