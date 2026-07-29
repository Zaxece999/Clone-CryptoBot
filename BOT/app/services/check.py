from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload
import structlog
import uuid
import bcrypt

from app.config import settings
from app.models.user import User
from app.models.check import Check, CheckActivation, CheckStatus, CheckType
from app.models.transaction import Transaction, TransactionType, TransactionStatus, TransactionDirection
from app.services.wallet import wallet_service
from app.utils.exceptions import (
    CheckError,
    InsufficientFundsError,
    ValidationError,
    NotFoundError,
    PermissionError
)

logger = structlog.get_logger(__name__)


class CheckService:
    def __init__(self):
        self.max_check_amount = Decimal("1000000")
        self.min_check_amount = Decimal("0.01")
        self.default_expiry_hours = 24 * 7
        self.max_expiry_hours = 24 * 30

    async def create_check(
        self,
        db: AsyncSession,
        creator: User,
        currency: str,
        amount: str,
        check_type: CheckType = CheckType.ONE_TIME,
        password: str = None,
        target_user_id: int = None,
        target_username: str = None,
        max_activations: int = None,
        expires_in_hours: int = None,
        description: str = None,
        comment: str = None
    ) -> Check:

        try:
            amount_decimal = Decimal(amount)
            if amount_decimal < self.min_check_amount:
                raise ValidationError(f"Minimum check amount is {self.min_check_amount}")
            if amount_decimal > self.max_check_amount:
                raise ValidationError(f"Maximum check amount is {self.max_check_amount}")

            wallet = await wallet_service.get_user_wallet(db, creator.id, currency)
            if not wallet:
                raise CheckError(f"Wallet for {currency} not found")

            available_balance = Decimal(wallet.available_balance)
            if amount_decimal > available_balance:
                raise InsufficientFundsError(
                    f"Insufficient funds: available {available_balance}, required {amount_decimal}"
                )

            if check_type == CheckType.PERSONAL and not target_user_id and not target_username:
                raise ValidationError("Personal check requires target_user_id or target_username")

            if check_type != CheckType.MULTI_USE and max_activations and max_activations > 1:
                raise ValidationError("Only multi-use checks can have max_activations > 1")

            expires_at = None
            if expires_in_hours:
                if expires_in_hours > self.max_expiry_hours:
                    raise ValidationError(f"Maximum expiry time is {self.max_expiry_hours} hours")
                expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
            else:
                expires_at = datetime.utcnow() + timedelta(hours=self.default_expiry_hours)

            password_hash = None
            if password:
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            check_id = await self._generate_unique_check_id(db)
            activation_code = await self._generate_unique_activation_code(db)

            wallet.freeze_balance(amount)

            check = Check(
                id=str(uuid.uuid4()),
                check_id=check_id,
                activation_code=activation_code,
                creator_id=creator.id,
                currency=currency,
                amount=amount,
                password=password_hash,
                type=check_type.value,
                status=CheckStatus.ACTIVE.value,
                max_activations=max_activations,
                target_user_id=target_user_id,
                target_username=target_username,
                expires_at=expires_at,
                description=description,
                comment=comment
            )

            db.add(check)

            transaction = await wallet_service.create_transaction(
                db=db,
                user_id=creator.id,
                wallet_id=wallet.id,
                transaction_type=TransactionType.CHECK_CREATION,
                currency=currency,
                amount=amount,
                direction=TransactionDirection.OUTGOING,
                description=f"Check creation: {check_id}",
                related_object_type="check",
                related_object_id=check.id
            )

            await db.commit()
            await db.refresh(check)

            logger.info(
                "Check created",
                check_id=check.check_id,
                creator_id=creator.id,
                amount=amount,
                currency=currency,
                type=check_type.value
            )

            return check

        except Exception as e:
            await db.rollback()
            logger.error(
                "Check creation failed",
                creator_id=creator.id,
                currency=currency,
                amount=amount,
                error=str(e),
                exc_info=True
            )
            raise CheckError(f"Failed to create check: {str(e)}")

    async def activate_check(
        self,
        db: AsyncSession,
        check_id: str,
        activator: User,
        password: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> CheckActivation:

        try:
            check = await self.get_check_by_id(db, check_id)
            if not check:
                raise NotFoundError("Check not found")

            if not check.can_be_activated_by(activator.id, activator.username):
                if check.creator_id == activator.id:
                    raise CheckError("Cannot activate your own check")
                elif check.status != CheckStatus.ACTIVE:
                    raise CheckError(f"Check is {check.status}")
                elif check.is_expired:
                    raise CheckError("Check has expired")
                elif check.type == CheckType.PERSONAL and check.target_user_id != activator.id and check.target_username and check.target_username.lower() != activator.username.lower():
                    raise CheckError("This is a personal check for another user")
                else:
                    raise CheckError("Check cannot be activated")

            if check.password:
                if not password:
                    raise CheckError("Password required")
                if not bcrypt.checkpw(password.encode('utf-8'), check.password.encode('utf-8')):
                    raise CheckError("Invalid password")

            activator_wallet = await wallet_service.get_user_wallet(db, activator.id, check.currency)
            if not activator_wallet:
                activator_wallet = await wallet_service.create_wallet(
                    db=db,
                    user=activator,
                    currency=check.currency
                )

            creator_wallet = await wallet_service.get_user_wallet(db, check.creator_id, check.currency)
            if not creator_wallet:
                raise CheckError("Creator wallet not found")

            check.activate(activator.id)

            amount_decimal = Decimal(check.amount)

            creator_wallet.unfreeze_balance(check.amount)
            creator_wallet.subtract_balance(check.amount)

            activator_wallet.add_balance(check.amount)

            creator_transaction = await wallet_service.create_transaction(
                db=db,
                user_id=check.creator_id,
                wallet_id=creator_wallet.id,
                transaction_type=TransactionType.CHECK_ACTIVATION,
                currency=check.currency,
                amount=check.amount,
                direction=TransactionDirection.OUTGOING,
                description=f"Check activated: {check.check_id}",
                related_user_id=activator.id,
                related_object_type="check",
                related_object_id=check.id
            )

            activator_transaction = await wallet_service.create_transaction(
                db=db,
                user_id=activator.id,
                wallet_id=activator_wallet.id,
                transaction_type=TransactionType.CHECK_ACTIVATION,
                currency=check.currency,
                amount=check.amount,
                direction=TransactionDirection.INCOMING,
                description=f"Check received: {check.check_id}",
                related_user_id=check.creator_id,
                related_object_type="check",
                related_object_id=check.id
            )

            creator_transaction.mark_as_completed()
            activator_transaction.mark_as_completed()

            activation = CheckActivation(
                id=str(uuid.uuid4()),
                check_id=check.id,
                user_id=activator.id,
                amount_received=check.amount,
                transaction_id=activator_transaction.id,
                ip_address=ip_address,
                user_agent=user_agent
            )

            db.add(activation)
            await db.commit()
            await db.refresh(activation)

            logger.info(
                "Check activated",
                check_id=check.check_id,
                creator_id=check.creator_id,
                activator_id=activator.id,
                amount=check.amount,
                currency=check.currency
            )

            return activation

        except Exception as e:
            await db.rollback()
            logger.error(
                "Check activation failed",
                check_id=check_id,
                activator_id=activator.id,
                error=str(e),
                exc_info=True
            )
            raise CheckError(f"Failed to activate check: {str(e)}")

    async def cancel_check(
        self,
        db: AsyncSession,
        check_id: str,
        user: User
    ) -> Check:

        try:
            check = await self.get_check_by_id(db, check_id)
            if not check:
                raise NotFoundError("Check not found")

            if check.creator_id != user.id:
                raise PermissionError("Only creator can cancel check")

            if not check.cancel():
                raise CheckError(f"Cannot cancel check with status {check.status}")

            creator_wallet = await wallet_service.get_user_wallet(db, check.creator_id, check.currency)
            if creator_wallet:
                creator_wallet.unfreeze_balance(check.amount)

                transaction = await wallet_service.create_transaction(
                    db=db,
                    user_id=check.creator_id,
                    wallet_id=creator_wallet.id,
                    transaction_type=TransactionType.REFUND,
                    currency=check.currency,
                    amount=check.amount,
                    direction=TransactionDirection.INCOMING,
                    description=f"Check cancelled: {check.check_id}",
                    related_object_type="check",
                    related_object_id=check.id
                )
                transaction.mark_as_completed()

            await db.commit()
            await db.refresh(check)

            logger.info(
                "Check cancelled",
                check_id=check.check_id,
                creator_id=check.creator_id,
                amount=check.amount,
                currency=check.currency
            )

            return check

        except Exception as e:
            await db.rollback()
            logger.error(
                "Check cancellation failed",
                check_id=check_id,
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            raise CheckError(f"Failed to cancel check: {str(e)}")

    async def get_check_by_id(
        self,
        db: AsyncSession,
        check_id: str,
        include_activations: bool = False
    ) -> Optional[Check]:

        query = select(Check).where(Check.check_id == check_id)

        if include_activations:
            query = query.options(selectinload(Check.activations))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_check_by_activation_code(
        self,
        db: AsyncSession,
        activation_code: str,
        include_activations: bool = False
    ) -> Optional[Check]:

        logger.info("Searching check by activation_code",
                   activation_code=activation_code,
                   activation_code_type=type(activation_code))

        query = select(Check).where(Check.activation_code == activation_code)

        if include_activations:
            query = query.options(selectinload(Check.activations))

        query = query.options(selectinload(Check.creator))

        result = await db.execute(query)
        check = result.scalar_one_or_none()

        logger.info("Check search result",
                   activation_code=activation_code,
                   found=check is not None,
                   check_id=check.check_id if check else None)

        return check

    async def get_user_checks(
        self,
        db: AsyncSession,
        user_id: int,
        status: CheckStatus = None,
        check_type: CheckType = None,
        currency: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Check]:

        query = select(Check).where(Check.creator_id == user_id)

        if status:
            query = query.where(Check.status == status.value)

        if check_type:
            query = query.where(Check.type == check_type.value)

        if currency:
            query = query.where(Check.currency == currency)

        query = query.order_by(desc(Check.created_at)).limit(limit).offset(offset)

        result = await db.execute(query)
        return result.scalars().all()

    async def get_user_activations(
        self,
        db: AsyncSession,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[CheckActivation]:

        query = select(CheckActivation).where(CheckActivation.user_id == user_id)
        query = query.options(selectinload(CheckActivation.check))
        query = query.order_by(desc(CheckActivation.activated_at)).limit(limit).offset(offset)

        result = await db.execute(query)
        return result.scalars().all()

    async def expire_checks(self, db: AsyncSession) -> int:
        try:
            query = select(Check).where(
                and_(
                    Check.status == CheckStatus.ACTIVE,
                    Check.expires_at < datetime.utcnow()
                )
            )

            result = await db.execute(query)
            expired_checks = result.scalars().all()

            count = 0
            for check in expired_checks:
                check.expire()

                creator_wallet = await wallet_service.get_user_wallet(db, check.creator_id, check.currency)
                if creator_wallet:
                    creator_wallet.unfreeze_balance(check.amount)

                    transaction = await wallet_service.create_transaction(
                        db=db,
                        user_id=check.creator_id,
                        wallet_id=creator_wallet.id,
                        transaction_type=TransactionType.REFUND,
                        currency=check.currency,
                        amount=check.amount,
                        direction=TransactionDirection.INCOMING,
                        description=f"Check expired: {check.check_id}",
                        related_object_type="check",
                        related_object_id=check.id
                    )
                    transaction.mark_as_completed()

                count += 1

            await db.commit()

            if count > 0:
                logger.info(f"Expired {count} checks")

            return count

        except Exception as e:
            await db.rollback()
            logger.error(
                "Check expiration failed",
                error=str(e),
                exc_info=True
            )
            raise

    async def get_check_stats(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict[str, Any]:

        created_query = select(
            func.count(Check.id).label('total'),
            func.count(Check.id).filter(Check.status == CheckStatus.ACTIVE).label('active'),
            func.count(Check.id).filter(Check.status == CheckStatus.ACTIVATED).label('activated'),
            func.count(Check.id).filter(Check.status == CheckStatus.EXPIRED).label('expired'),
            func.count(Check.id).filter(Check.status == CheckStatus.CANCELLED).label('cancelled'),
            func.sum(Check.amount).label('total_amount')
        ).where(Check.creator_id == user_id)

        created_result = await db.execute(created_query)
        created_stats = created_result.first()

        activated_query = select(
            func.count(CheckActivation.id).label('total'),
            func.sum(CheckActivation.amount_received).label('total_received')
        ).where(CheckActivation.user_id == user_id)

        activated_result = await db.execute(activated_query)
        activated_stats = activated_result.first()

        return {
            "created": {
                "total": created_stats.total or 0,
                "active": created_stats.active or 0,
                "activated": created_stats.activated or 0,
                "expired": created_stats.expired or 0,
                "cancelled": created_stats.cancelled or 0,
                "total_amount": str(created_stats.total_amount or 0)
            },
            "activated": {
                "total": activated_stats.total or 0,
                "total_received": str(activated_stats.total_received or 0)
            }
        }

    async def _generate_unique_check_id(self, db: AsyncSession) -> str:
        max_attempts = 10

        for _ in range(max_attempts):
            check_id = Check.generate_check_id()

            result = await db.execute(
                select(Check.id).where(Check.check_id == check_id).limit(1)
            )

            if not result.scalar_one_or_none():
                return check_id

        raise CheckError("Failed to generate unique check ID")

    async def _generate_unique_activation_code(self, db: AsyncSession) -> str:
        max_attempts = 10

        for _ in range(max_attempts):
            activation_code = Check.generate_activation_code()

            result = await db.execute(
                select(Check.id).where(Check.activation_code == activation_code).limit(1)
            )

            if not result.scalar_one_or_none():
                return activation_code

        raise CheckError("Failed to generate unique activation code")


check_service = CheckService()
