import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload
import structlog

from app.models.subscription import (
    Subscription, SubscriptionPayment, SubscriptionPlan, SubscriptionInvite,
    SubscriptionStats, SubscriptionNotification,
    SubscriptionStatus, SubscriptionType, BillingPeriod
)
from app.models.user import User
from app.services.wallet import wallet_service
from app.services.transaction import transaction_service
from app.utils.exceptions import (
    ValidationError, InsufficientFundsError, NotFoundError, SubscriptionError
)

logger = structlog.get_logger(__name__)


class SubscriptionService:
    def __init__(self):
        self.default_trial_days = 7
        self.reminder_days = [7, 3, 1]

    async def create_subscription(
        self,
        db: AsyncSession,
        user: User,
        title: str,
        description: Optional[str],
        subscription_type: SubscriptionType,
        price: Decimal,
        currency: str,
        billing_period: BillingPeriod,
        chat_id: Optional[str] = None,
        chat_username: Optional[str] = None,
        chat_title: Optional[str] = None,
        trial_days: Optional[int] = None,
        auto_renew: bool = True
    ) -> Subscription:
        try:
            if price < 0:
                raise ValidationError("Price cannot be negative")

            if trial_days is None:
                trial_days = self.default_trial_days

            subscription = Subscription(
                subscription_id=str(uuid.uuid4()).replace("-", ""),
                user_id=user.id,
                title=title,
                description=description,
                subscription_type=subscription_type.value,
                status=SubscriptionStatus.PENDING.value,
                price=price,
                currency=currency,
                billing_period=billing_period.value,
                chat_id=chat_id,
                chat_username=chat_username,
                chat_title=chat_title,
                trial_days=trial_days,
                auto_renew=auto_renew
            )

            now = datetime.utcnow()
            subscription.starts_at = now

            if trial_days > 0:
                subscription.trial_ends_at = now + timedelta(days=trial_days)
                subscription.next_billing_at = subscription.trial_ends_at
            else:
                subscription.next_billing_at = self._calculate_next_billing_date(now, billing_period)

            subscription.expires_at = subscription.next_billing_at

            db.add(subscription)
            await db.commit()
            await db.refresh(subscription)

            logger.info(
                "Subscription created",
                subscription_id=subscription.subscription_id,
                user_id=user.id,
                title=title,
                price=str(price),
                currency=currency
            )

            return subscription

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to create subscription",
                user_id=user.id,
                title=title,
                error=str(e),
                exc_info=True
            )
            raise

    async def activate_subscription(
        self,
        db: AsyncSession,
        subscription_id: str,
        user: User
    ) -> Subscription:
        try:
            subscription = await self.get_subscription_by_id(db, subscription_id)
            if not subscription:
                raise NotFoundError("Subscription not found")

            if subscription.user_id != user.id:
                raise ValidationError("Access denied")

            if subscription.status != SubscriptionStatus.PENDING.value:
                raise ValidationError(f"Cannot activate subscription with status: {subscription.status}")

            subscription.status = SubscriptionStatus.ACTIVE.value
            subscription.activated_at = datetime.utcnow()

            await db.commit()

            logger.info(
                "Subscription activated",
                subscription_id=subscription.subscription_id,
                user_id=user.id
            )

            return subscription

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to activate subscription",
                subscription_id=subscription_id,
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            raise

    async def cancel_subscription(
        self,
        db: AsyncSession,
        subscription_id: str,
        user: User,
        reason: Optional[str] = None
    ) -> Subscription:
        try:
            subscription = await self.get_subscription_by_id(db, subscription_id)
            if not subscription:
                raise NotFoundError("Subscription not found")

            if subscription.user_id != user.id:
                raise ValidationError("Access denied")

            if subscription.status == SubscriptionStatus.CANCELLED.value:
                raise ValidationError("Subscription is already cancelled")

            subscription.status = SubscriptionStatus.CANCELLED.value
            subscription.cancelled_at = datetime.utcnow()
            subscription.auto_renew = False

            if reason:
                subscription.notes = f"Cancelled: {reason}"

            await db.commit()

            logger.info(
                "Subscription cancelled",
                subscription_id=subscription.subscription_id,
                user_id=user.id,
                reason=reason
            )

            return subscription

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to cancel subscription",
                subscription_id=subscription_id,
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            raise

    async def process_subscription_payment(
        self,
        db: AsyncSession,
        subscription_id: str,
        user: User
    ) -> SubscriptionPayment:
        try:
            subscription = await self.get_subscription_by_id(db, subscription_id)
            if not subscription:
                raise NotFoundError("Subscription not found")

            if subscription.user_id != user.id:
                raise ValidationError("Access denied")

            if not subscription.is_active:
                raise ValidationError("Subscription is not active")

            wallet = await wallet_service.get_or_create_wallet(db, user.id, subscription.currency)
            if wallet.balance < subscription.price:
                raise InsufficientFundsError(f"Insufficient {subscription.currency} balance")

            now = datetime.utcnow()
            billing_start = subscription.next_billing_at or now
            billing_end = self._calculate_next_billing_date(billing_start, BillingPeriod(subscription.billing_period))

            payment = SubscriptionPayment(
                payment_id=str(uuid.uuid4()).replace("-", ""),
                subscription_id=subscription.id,
                user_id=user.id,
                amount=subscription.price,
                currency=subscription.currency,
                status="pending",
                billing_period_start=billing_start,
                billing_period_end=billing_end
            )

            db.add(payment)

            transaction = await transaction_service.create_transaction(
                db=db,
                user=user,
                transaction_type="subscription_payment",
                currency=subscription.currency,
                amount=-subscription.price,
                description=f"Subscription payment: {subscription.title}",
                reference_id=subscription.subscription_id
            )

            payment.transaction_id = transaction.transaction_id
            payment.status = "completed"
            payment.paid_at = datetime.utcnow()

            subscription.next_billing_at = billing_end
            subscription.expires_at = billing_end
            subscription.total_payments += 1
            subscription.total_amount_paid += subscription.price

            await db.commit()

            logger.info(
                "Subscription payment processed",
                subscription_id=subscription.subscription_id,
                payment_id=payment.payment_id,
                amount=str(subscription.price),
                currency=subscription.currency
            )

            return payment

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to process subscription payment",
                subscription_id=subscription_id,
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            raise

    async def get_subscription_by_id(
        self,
        db: AsyncSession,
        subscription_id: str,
        include_payments: bool = False
    ) -> Optional[Subscription]:
        try:
            query = select(Subscription).where(Subscription.subscription_id == subscription_id)

            if include_payments:
                query = query.options(selectinload(Subscription.payments))

            result = await db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "Failed to get subscription by ID",
                subscription_id=subscription_id,
                error=str(e),
                exc_info=True
            )
            return None

    async def get_user_subscriptions(
        self,
        db: AsyncSession,
        user_id: int,
        status: Optional[str] = None,
        subscription_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Subscription]:
        try:
            query = select(Subscription).where(Subscription.user_id == user_id)

            if status:
                query = query.where(Subscription.status == status)

            if subscription_type:
                query = query.where(Subscription.subscription_type == subscription_type)

            query = query.order_by(desc(Subscription.created_at)).limit(limit).offset(offset)

            result = await db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(
                "Failed to get user subscriptions",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            return []

    async def get_expiring_subscriptions(
        self,
        db: AsyncSession,
        days_ahead: int = 7
    ) -> List[Subscription]:
        try:
            cutoff_date = datetime.utcnow() + timedelta(days=days_ahead)

            query = select(Subscription).where(
                and_(
                    Subscription.status == SubscriptionStatus.ACTIVE.value,
                    Subscription.expires_at <= cutoff_date,
                    Subscription.expires_at > datetime.utcnow()
                )
            ).order_by(Subscription.expires_at)

            result = await db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(
                "Failed to get expiring subscriptions",
                days_ahead=days_ahead,
                error=str(e),
                exc_info=True
            )
            return []

    async def renew_subscription(
        self,
        db: AsyncSession,
        subscription_id: str,
        user: User
    ) -> Subscription:
        try:
            subscription = await self.get_subscription_by_id(db, subscription_id)
            if not subscription:
                raise NotFoundError("Subscription not found")

            if subscription.user_id != user.id:
                raise ValidationError("Access denied")

            if subscription.status != SubscriptionStatus.ACTIVE.value:
                raise ValidationError("Can only renew active subscriptions")

            payment = await self.process_subscription_payment(db, subscription_id, user)

            logger.info(
                "Subscription renewed",
                subscription_id=subscription.subscription_id,
                user_id=user.id,
                new_expiry=subscription.expires_at.isoformat()
            )

            return subscription

        except Exception as e:
            logger.error(
                "Failed to renew subscription",
                subscription_id=subscription_id,
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            raise

    async def create_subscription_invite(
        self,
        db: AsyncSession,
        subscription_id: str,
        creator: User,
        max_uses: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        description: Optional[str] = None
    ) -> SubscriptionInvite:
        try:
            subscription = await self.get_subscription_by_id(db, subscription_id)
            if not subscription:
                raise NotFoundError("Subscription not found")

            if subscription.user_id != creator.id:
                raise ValidationError("Access denied")

            invite = SubscriptionInvite(
                invite_id=str(uuid.uuid4()).replace("-", ""),
                subscription_id=subscription.id,
                creator_id=creator.id,
                max_uses=max_uses,
                expires_at=expires_at,
                description=description
            )

            db.add(invite)
            await db.commit()
            await db.refresh(invite)

            logger.info(
                "Subscription invite created",
                invite_id=invite.invite_id,
                subscription_id=subscription.subscription_id,
                creator_id=creator.id
            )

            return invite

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to create subscription invite",
                subscription_id=subscription_id,
                creator_id=creator.id,
                error=str(e),
                exc_info=True
            )
            raise

    async def use_subscription_invite(
        self,
        db: AsyncSession,
        invite_id: str,
        user: User
    ) -> Subscription:
        try:
            query = select(SubscriptionInvite).where(SubscriptionInvite.invite_id == invite_id)
            result = await db.execute(query)
            invite = result.scalar_one_or_none()

            if not invite:
                raise NotFoundError("Invite not found")

            if not invite.is_valid:
                raise ValidationError("Invite is not valid")

            existing_subscription = await self.get_user_subscription_for_chat(
                db, user.id, invite.subscription.chat_id
            )

            if existing_subscription:
                raise ValidationError("User is already subscribed")

            invite.uses_count += 1

            subscription = await self.create_subscription(
                db=db,
                user=user,
                title=invite.subscription.title,
                description=invite.subscription.description,
                subscription_type=SubscriptionType(invite.subscription.subscription_type),
                price=invite.subscription.price,
                currency=invite.subscription.currency,
                billing_period=BillingPeriod(invite.subscription.billing_period),
                chat_id=invite.subscription.chat_id,
                chat_username=invite.subscription.chat_username,
                chat_title=invite.subscription.chat_title,
                trial_days=invite.subscription.trial_days
            )

            subscription = await self.activate_subscription(db, subscription.subscription_id, user)

            await db.commit()

            logger.info(
                "Subscription invite used",
                invite_id=invite.invite_id,
                user_id=user.id,
                subscription_id=subscription.subscription_id
            )

            return subscription

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to use subscription invite",
                invite_id=invite_id,
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            raise

    async def get_user_subscription_for_chat(
        self,
        db: AsyncSession,
        user_id: int,
        chat_id: str
    ) -> Optional[Subscription]:
        try:
            query = select(Subscription).where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.chat_id == chat_id,
                    Subscription.status.in_([
                        SubscriptionStatus.ACTIVE.value,
                        SubscriptionStatus.PENDING.value
                    ])
                )
            )

            result = await db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "Failed to get user subscription for chat",
                user_id=user_id,
                chat_id=chat_id,
                error=str(e),
                exc_info=True
            )
            return None

    async def process_expired_subscriptions(self, db: AsyncSession) -> int:
        try:
            query = select(Subscription).where(
                and_(
                    Subscription.status == SubscriptionStatus.ACTIVE.value,
                    Subscription.expires_at <= datetime.utcnow()
                )
            )

            result = await db.execute(query)
            expired_subscriptions = result.scalars().all()

            processed_count = 0

            for subscription in expired_subscriptions:
                if subscription.auto_renew:
                    try:
                        user = subscription.user
                        await self.process_subscription_payment(db, subscription.subscription_id, user)
                        processed_count += 1

                        logger.info(
                            "Subscription auto-renewed",
                            subscription_id=subscription.subscription_id,
                            user_id=subscription.user_id
                        )

                    except Exception as e:
                        subscription.status = SubscriptionStatus.EXPIRED.value
                        processed_count += 1

                        logger.warning(
                            "Failed to auto-renew subscription",
                            subscription_id=subscription.subscription_id,
                            user_id=subscription.user_id,
                            error=str(e)
                        )
                else:
                    subscription.status = SubscriptionStatus.EXPIRED.value
                    processed_count += 1

            await db.commit()

            logger.info(
                "Processed expired subscriptions",
                count=processed_count
            )

            return processed_count

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to process expired subscriptions",
                error=str(e),
                exc_info=True
            )
            return 0

    def _calculate_next_billing_date(self, current_date: datetime, billing_period: BillingPeriod) -> datetime:
        if billing_period == BillingPeriod.DAILY:
            return current_date + timedelta(days=1)
        elif billing_period == BillingPeriod.WEEKLY:
            return current_date + timedelta(weeks=1)
        elif billing_period == BillingPeriod.MONTHLY:
            return current_date + timedelta(days=30)
        elif billing_period == BillingPeriod.QUARTERLY:
            return current_date + timedelta(days=90)
        elif billing_period == BillingPeriod.YEARLY:
            return current_date + timedelta(days=365)
        else:
            return current_date + timedelta(days=30)

    async def get_subscription_stats(
        self,
        db: AsyncSession,
        subscription_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        try:
            subscription = await self.get_subscription_by_id(db, subscription_id)
            if not subscription:
                raise NotFoundError("Subscription not found")


            return {
                "subscription_id": subscription.subscription_id,
                "title": subscription.title,
                "status": subscription.status,
                "total_payments": subscription.total_payments,
                "total_revenue": str(subscription.total_amount_paid),
                "currency": subscription.currency,
                "created_at": subscription.created_at.isoformat(),
                "next_billing_at": subscription.next_billing_at.isoformat() if subscription.next_billing_at else None,
                "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None
            }

        except Exception as e:
            logger.error(
                "Failed to get subscription stats",
                subscription_id=subscription_id,
                error=str(e),
                exc_info=True
            )
            return {}


subscription_service = SubscriptionService()
