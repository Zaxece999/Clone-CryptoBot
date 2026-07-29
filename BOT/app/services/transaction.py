from typing import List, Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload
import structlog
import uuid

from app.config import settings
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransactionType, TransactionStatus, TransactionDirection
from app.utils.exceptions import (
    TransactionError,
    TransactionNotFoundError,
    ValidationError,
    InsufficientFundsError,
)

logger = structlog.get_logger(__name__)


class TransactionService:
    def __init__(self):
        self.min_amount = Decimal("0.00000001")
        self.max_amount = Decimal("1000000")

    async def create_transaction(
        self,
        db: AsyncSession,
        user: User,
        wallet: Wallet,
        transaction_type: TransactionType,
        direction: TransactionDirection,
        amount: str,
        currency: str = None,
        to_address: str = None,
        from_address: str = None,
        description: str = None,
        related_user_id: int = None,
        related_object_type: str = None,
        related_object_id: str = None,
        network: str = None,
        fee: str = "0"
    ) -> Transaction:

        try:
            amount_decimal = Decimal(amount)
            if amount_decimal < self.min_amount:
                raise ValidationError(f"Amount too small: minimum {self.min_amount}")
            if amount_decimal > self.max_amount:
                raise ValidationError(f"Amount too large: maximum {self.max_amount}")

            transaction = Transaction(
                id=str(uuid.uuid4()),
                user_id=user.id,
                wallet_id=wallet.id,
                type=transaction_type,
                status=TransactionStatus.PENDING,
                direction=direction,
                currency=currency or wallet.currency,
                amount=amount,
                fee=fee,
                from_address=from_address or wallet.address,
                to_address=to_address,
                network=network,
                related_user_id=related_user_id,
                related_object_type=related_object_type,
                related_object_id=related_object_id,
                description=description
            )

            db.add(transaction)
            await db.commit()
            await db.refresh(transaction)

            logger.info(
                "Transaction created",
                transaction_id=transaction.id,
                user_id=user.id,
                wallet_id=wallet.id,
                type=transaction_type.value,
                amount=amount,
                currency=currency or wallet.currency
            )

            return transaction

        except Exception as e:
            await db.rollback()
            logger.error(
                "Transaction creation failed",
                user_id=user.id,
                wallet_id=wallet.id,
                error=str(e),
                exc_info=True
            )
            raise TransactionError(f"Failed to create transaction: {str(e)}")

    async def get_transaction_by_id(
        self,
        db: AsyncSession,
        transaction_id: str,
        user_id: int = None
    ) -> Optional[Transaction]:

        query = select(Transaction).where(Transaction.id == transaction_id)

        if user_id:
            query = query.where(Transaction.user_id == user_id)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_transactions(
        self,
        db: AsyncSession,
        user_id: int,
        transaction_type: TransactionType = None,
        status: TransactionStatus = None,
        currency: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Transaction]:

        query = select(Transaction).where(Transaction.user_id == user_id)

        if transaction_type:
            query = query.where(Transaction.type == transaction_type)

        if status:
            query = query.where(Transaction.status == status)

        if currency:
            query = query.where(Transaction.currency == currency)

        query = query.order_by(desc(Transaction.created_at)).limit(limit).offset(offset)

        result = await db.execute(query)
        return result.scalars().all()

    async def update_transaction_status(
        self,
        db: AsyncSession,
        transaction_id: str,
        status: TransactionStatus,
        tx_hash: str = None,
        block_number: int = None
    ) -> Transaction:

        transaction = await self.get_transaction_by_id(db, transaction_id)
        if not transaction:
            raise TransactionNotFoundError(f"Transaction {transaction_id} not found")

        transaction.status = status

        if tx_hash:
            transaction.tx_hash = tx_hash

        if block_number:
            transaction.block_number = block_number

        if status == TransactionStatus.PROCESSING:
            transaction.mark_as_processing()
        elif status == TransactionStatus.COMPLETED:
            transaction.mark_as_completed()
        elif status == TransactionStatus.FAILED:
            transaction.mark_as_failed()

        await db.commit()
        await db.refresh(transaction)

        logger.info(
            "Transaction status updated",
            transaction_id=transaction_id,
            status=status.value,
            tx_hash=tx_hash
        )

        return transaction

    async def get_transaction_stats(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict[str, Any]:

        total_query = select(
            func.count(Transaction.id).label('total'),
            func.count(Transaction.id).filter(Transaction.status == TransactionStatus.COMPLETED).label('completed'),
            func.count(Transaction.id).filter(Transaction.status == TransactionStatus.PENDING).label('pending'),
            func.count(Transaction.id).filter(Transaction.status == TransactionStatus.FAILED).label('failed'),
        ).where(Transaction.user_id == user_id)

        total_result = await db.execute(total_query)
        total_stats = total_result.first()

        type_query = select(
            Transaction.type,
            func.count(Transaction.id).label('count')
        ).where(Transaction.user_id == user_id).group_by(Transaction.type)

        type_result = await db.execute(type_query)
        type_stats = {row.type: row.count for row in type_result}

        currency_query = select(
            Transaction.currency,
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount).label('total_amount')
        ).where(Transaction.user_id == user_id).group_by(Transaction.currency)

        currency_result = await db.execute(currency_query)
        currency_stats = {
            row.currency: {
                'count': row.count,
                'total_amount': str(row.total_amount or 0)
            }
            for row in currency_result
        }

        return {
            "total": {
                "total": total_stats.total or 0,
                "completed": total_stats.completed or 0,
                "pending": total_stats.pending or 0,
                "failed": total_stats.failed or 0,
            },
            "by_type": type_stats,
            "by_currency": currency_stats
        }


transaction_service = TransactionService()
