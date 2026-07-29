import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload
import structlog
import httpx

from app.models.exchange import (
    Exchange, ExchangeRate, ExchangeProvider, ExchangeLimit, ExchangeHistory,
    ExchangeStatus, ExchangeType
)
from app.models.user import User
from app.models.wallet import Wallet
from app.services.wallet import wallet_service
from app.services.transaction import transaction_service
from app.utils.exceptions import (
    ValidationError, InsufficientFundsError, NotFoundError, ExchangeError
)

logger = structlog.get_logger(__name__)


class ExchangeService:
    def __init__(self):
        self.default_fee_percentage = Decimal("0.005")
        self.min_fee_amount = Decimal("0.0001")
        self.exchange_timeout_minutes = 30
        self.rate_cache_seconds = 60
        self._rate_cache = {}
        self._cache_timestamps = {}

    async def get_exchange_rate(
        self,
        db: AsyncSession,
        from_currency: str,
        to_currency: str,
        amount: Optional[Decimal] = None,
        use_cache: bool = True
    ) -> Optional[ExchangeRate]:
        try:
            cache_key = f"{from_currency}_{to_currency}"
            if use_cache and cache_key in self._rate_cache:
                cache_time = self._cache_timestamps.get(cache_key, datetime.min)
                if (datetime.utcnow() - cache_time).seconds < self.rate_cache_seconds:
                    return self._rate_cache[cache_key]

            query = select(ExchangeRate).where(
                and_(
                    ExchangeRate.from_currency == from_currency,
                    ExchangeRate.to_currency == to_currency,
                    ExchangeRate.is_active == True
                )
            ).order_by(desc(ExchangeRate.updated_at))

            result = await db.execute(query)
            rate = result.scalar_one_or_none()

            if not rate:
                query = select(ExchangeRate).where(
                    and_(
                        ExchangeRate.from_currency == to_currency,
                        ExchangeRate.to_currency == from_currency,
                        ExchangeRate.is_active == True
                    )
                ).order_by(desc(ExchangeRate.updated_at))

                result = await db.execute(query)
                reverse_rate = result.scalar_one_or_none()

                if reverse_rate:
                    rate = ExchangeRate(
                        from_currency=from_currency,
                        to_currency=to_currency,
                        rate=1 / Decimal(str(reverse_rate.rate)),
                        buy_rate=1 / Decimal(str(reverse_rate.sell_rate)),
                        sell_rate=1 / Decimal(str(reverse_rate.buy_rate)),
                        spread_percentage=reverse_rate.spread_percentage,
                        source=reverse_rate.source
                    )

            if rate and use_cache:
                self._rate_cache[cache_key] = rate
                self._cache_timestamps[cache_key] = datetime.utcnow()

            return rate

        except Exception as e:
            logger.error(
                "Failed to get exchange rate",
                from_currency=from_currency,
                to_currency=to_currency,
                error=str(e),
                exc_info=True
            )
            return None

    async def calculate_exchange(
        self,
        db: AsyncSession,
        from_currency: str,
        to_currency: str,
        from_amount: Decimal,
        user: Optional[User] = None
    ) -> Dict[str, Any]:
        try:
            rate = await self.get_exchange_rate(db, from_currency, to_currency)
            if not rate:
                raise ExchangeError(f"Exchange rate not available for {from_currency}/{to_currency}")

            if rate.min_amount and from_amount < Decimal(str(rate.min_amount)):
                raise ValidationError(f"Minimum exchange amount is {rate.min_amount} {from_currency}")

            if rate.max_amount and from_amount > Decimal(str(rate.max_amount)):
                raise ValidationError(f"Maximum exchange amount is {rate.max_amount} {from_currency}")

            exchange_rate = Decimal(str(rate.sell_rate))
            to_amount = (from_amount * exchange_rate).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)

            fee_percentage = self.default_fee_percentage
            if user and user.is_premium:
                fee_percentage = fee_percentage * Decimal("0.5")

            fee_amount = (from_amount * fee_percentage).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
            if fee_amount < self.min_fee_amount:
                fee_amount = self.min_fee_amount

            if user:
                can_exchange = await self.check_user_limits(db, user.id, from_currency, from_amount)
                if not can_exchange:
                    raise ValidationError("Exchange amount exceeds user limits")

            return {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "from_amount": str(from_amount),
                "to_amount": str(to_amount),
                "exchange_rate": str(exchange_rate),
                "fee_amount": str(fee_amount),
                "fee_percentage": str(fee_percentage * 100),
                "fee_currency": from_currency,
                "total_from_amount": str(from_amount + fee_amount),
                "net_to_amount": str(to_amount),
                "rate_source": rate.source,
                "expires_in_minutes": self.exchange_timeout_minutes
            }

        except Exception as e:
            logger.error(
                "Failed to calculate exchange",
                from_currency=from_currency,
                to_currency=to_currency,
                from_amount=str(from_amount),
                error=str(e),
                exc_info=True
            )
            raise

    async def create_exchange(
        self,
        db: AsyncSession,
        user: User,
        from_currency: str,
        to_currency: str,
        from_amount: Decimal,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Exchange:
        try:
            calculation = await self.calculate_exchange(db, from_currency, to_currency, from_amount, user)

            from_wallet = await wallet_service.get_or_create_wallet(db, user.id, from_currency)
            total_amount = Decimal(calculation["total_from_amount"])

            if from_wallet.balance < total_amount:
                raise InsufficientFundsError(f"Insufficient {from_currency} balance")

            crypto_currencies = ["BTC", "ETH", "USDT", "LTC", "BNB", "TRX", "TON"]
            from_is_crypto = from_currency in crypto_currencies
            to_is_crypto = to_currency in crypto_currencies

            if from_is_crypto and to_is_crypto:
                exchange_type = ExchangeType.CRYPTO_TO_CRYPTO
            elif from_is_crypto and not to_is_crypto:
                exchange_type = ExchangeType.CRYPTO_TO_FIAT
            else:
                exchange_type = ExchangeType.FIAT_TO_CRYPTO

            exchange = Exchange(
                exchange_id=str(uuid.uuid4()).replace("-", ""),
                user_id=user.id,
                exchange_type=exchange_type.value,
                status=ExchangeStatus.PENDING.value,
                from_currency=from_currency,
                to_currency=to_currency,
                from_amount=from_amount,
                to_amount=Decimal(calculation["to_amount"]),
                exchange_rate=Decimal(calculation["exchange_rate"]),
                fee_amount=Decimal(calculation["fee_amount"]),
                fee_currency=from_currency,
                fee_percentage=Decimal(calculation["fee_percentage"]) / 100,
                expires_at=datetime.utcnow() + timedelta(minutes=self.exchange_timeout_minutes),
                ip_address=ip_address,
                user_agent=user_agent
            )

            db.add(exchange)
            await db.commit()
            await db.refresh(exchange)

            logger.info(
                "Exchange created",
                exchange_id=exchange.exchange_id,
                user_id=user.id,
                from_currency=from_currency,
                to_currency=to_currency,
                from_amount=str(from_amount)
            )

            return exchange

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to create exchange",
                user_id=user.id,
                from_currency=from_currency,
                to_currency=to_currency,
                from_amount=str(from_amount),
                error=str(e),
                exc_info=True
            )
            raise

    async def process_exchange(
        self,
        db: AsyncSession,
        exchange_id: str,
        user: User
    ) -> Exchange:
        try:
            exchange = await self.get_exchange_by_id(db, exchange_id)
            if not exchange:
                raise NotFoundError("Exchange not found")

            if exchange.user_id != user.id:
                raise ValidationError("Access denied")

            if exchange.status != ExchangeStatus.PENDING.value:
                raise ValidationError(f"Exchange is not pending (status: {exchange.status})")

            if exchange.is_expired:
                exchange.status = ExchangeStatus.EXPIRED.value
                await db.commit()
                raise ValidationError("Exchange has expired")

            exchange.status = ExchangeStatus.PROCESSING.value
            exchange.processed_at = datetime.utcnow()
            await db.commit()

            from_wallet = await wallet_service.get_or_create_wallet(db, user.id, exchange.from_currency)
            total_amount = exchange.total_from_amount

            if from_wallet.balance < total_amount:
                exchange.status = ExchangeStatus.FAILED.value
                exchange.failure_reason = "Insufficient funds"
                await db.commit()
                raise InsufficientFundsError(f"Insufficient {exchange.from_currency} balance")

            debit_tx = await transaction_service.create_transaction(
                db=db,
                user=user,
                transaction_type="exchange_debit",
                currency=exchange.from_currency,
                amount=-total_amount,
                description=f"Exchange {exchange.from_currency} to {exchange.to_currency}",
                reference_id=exchange.exchange_id
            )

            exchange.debit_transaction_id = debit_tx.transaction_id

            to_wallet = await wallet_service.get_or_create_wallet(db, user.id, exchange.to_currency)

            credit_tx = await transaction_service.create_transaction(
                db=db,
                user=user,
                transaction_type="exchange_credit",
                currency=exchange.to_currency,
                amount=exchange.net_to_amount,
                description=f"Exchange {exchange.from_currency} to {exchange.to_currency}",
                reference_id=exchange.exchange_id
            )

            exchange.credit_transaction_id = credit_tx.transaction_id

            exchange.status = ExchangeStatus.COMPLETED.value
            exchange.completed_at = datetime.utcnow()

            await self.update_user_limits(db, user.id, exchange.from_currency, total_amount)

            await db.commit()

            logger.info(
                "Exchange completed",
                exchange_id=exchange.exchange_id,
                user_id=user.id,
                from_amount=str(exchange.from_amount),
                to_amount=str(exchange.to_amount)
            )

            return exchange

        except Exception as e:
            await db.rollback()

            if 'exchange' in locals():
                try:
                    exchange.status = ExchangeStatus.FAILED.value
                    exchange.failure_reason = str(e)
                    await db.commit()
                except:
                    pass

            logger.error(
                "Failed to process exchange",
                exchange_id=exchange_id,
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            raise

    async def cancel_exchange(
        self,
        db: AsyncSession,
        exchange_id: str,
        user: User,
        reason: Optional[str] = None
    ) -> Exchange:
        try:
            exchange = await self.get_exchange_by_id(db, exchange_id)
            if not exchange:
                raise NotFoundError("Exchange not found")

            if exchange.user_id != user.id:
                raise ValidationError("Access denied")

            if exchange.status not in [ExchangeStatus.PENDING.value, ExchangeStatus.PROCESSING.value]:
                raise ValidationError(f"Cannot cancel exchange with status: {exchange.status}")

            exchange.status = ExchangeStatus.CANCELLED.value
            exchange.failure_reason = reason or "Cancelled by user"

            await db.commit()

            logger.info(
                "Exchange cancelled",
                exchange_id=exchange.exchange_id,
                user_id=user.id,
                reason=reason
            )

            return exchange

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to cancel exchange",
                exchange_id=exchange_id,
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            raise

    async def get_exchange_by_id(
        self,
        db: AsyncSession,
        exchange_id: str,
        include_user: bool = False
    ) -> Optional[Exchange]:
        try:
            query = select(Exchange).where(Exchange.exchange_id == exchange_id)

            if include_user:
                query = query.options(selectinload(Exchange.user))

            result = await db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "Failed to get exchange by ID",
                exchange_id=exchange_id,
                error=str(e),
                exc_info=True
            )
            return None

    async def get_user_exchanges(
        self,
        db: AsyncSession,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Exchange]:
        try:
            query = select(Exchange).where(Exchange.user_id == user_id)

            if status:
                query = query.where(Exchange.status == status)

            query = query.order_by(desc(Exchange.created_at)).limit(limit).offset(offset)

            result = await db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(
                "Failed to get user exchanges",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            return []

    async def check_user_limits(
        self,
        db: AsyncSession,
        user_id: int,
        currency: str,
        amount: Decimal
    ) -> bool:
        try:
            query = select(ExchangeLimit).where(
                and_(
                    ExchangeLimit.user_id == user_id,
                    ExchangeLimit.currency == currency
                )
            )

            result = await db.execute(query)
            limit = result.scalar_one_or_none()

            if not limit:
                limit = await self.create_default_limits(db, user_id, currency)

            await self.reset_limits_if_needed(db, limit)

            return limit.can_exchange(amount)

        except Exception as e:
            logger.error(
                "Failed to check user limits",
                user_id=user_id,
                currency=currency,
                amount=str(amount),
                error=str(e),
                exc_info=True
            )
            return False

    async def create_default_limits(
        self,
        db: AsyncSession,
        user_id: int,
        currency: str
    ) -> ExchangeLimit:
        now = datetime.utcnow()

        default_limits = {
            "daily_limit": Decimal("1000"),
            "monthly_limit": Decimal("10000"),
            "yearly_limit": Decimal("100000")
        }

        limit = ExchangeLimit(
            user_id=user_id,
            currency=currency,
            daily_limit=default_limits["daily_limit"],
            monthly_limit=default_limits["monthly_limit"],
            yearly_limit=default_limits["yearly_limit"],
            daily_reset_at=now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1),
            monthly_reset_at=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32),
            yearly_reset_at=now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=366)
        )

        db.add(limit)
        await db.commit()
        await db.refresh(limit)

        return limit

    async def reset_limits_if_needed(self, db: AsyncSession, limit: ExchangeLimit):
        now = datetime.utcnow()
        updated = False

        if now >= limit.daily_reset_at:
            limit.daily_used = Decimal("0")
            limit.daily_reset_at = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            updated = True

        if now >= limit.monthly_reset_at:
            limit.monthly_used = Decimal("0")
            limit.monthly_reset_at = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32)
            updated = True

        if now >= limit.yearly_reset_at:
            limit.yearly_used = Decimal("0")
            limit.yearly_reset_at = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=366)
            updated = True

        if updated:
            await db.commit()

    async def update_user_limits(
        self,
        db: AsyncSession,
        user_id: int,
        currency: str,
        amount: Decimal
    ):
        try:
            query = select(ExchangeLimit).where(
                and_(
                    ExchangeLimit.user_id == user_id,
                    ExchangeLimit.currency == currency
                )
            )

            result = await db.execute(query)
            limit = result.scalar_one_or_none()

            if limit:
                limit.daily_used += amount
                limit.monthly_used += amount
                limit.yearly_used += amount
                await db.commit()

        except Exception as e:
            logger.error(
                "Failed to update user limits",
                user_id=user_id,
                currency=currency,
                amount=str(amount),
                error=str(e),
                exc_info=True
            )

    async def get_supported_pairs(self, db: AsyncSession) -> List[Dict[str, Any]]:
        try:
            query = select(ExchangeRate).where(ExchangeRate.is_active == True)
            result = await db.execute(query)
            rates = result.scalars().all()

            pairs = []
            for rate in rates:
                pairs.append({
                    "from_currency": rate.from_currency,
                    "to_currency": rate.to_currency,
                    "rate": str(rate.rate),
                    "min_amount": str(rate.min_amount) if rate.min_amount else None,
                    "max_amount": str(rate.max_amount) if rate.max_amount else None,
                    "updated_at": rate.updated_at.isoformat()
                })

            return pairs

        except Exception as e:
            logger.error("❌ Не удалось получить поддерживаемые пары", error=str(e), exc_info=True)
            return []

    async def update_exchange_rates(self, db: AsyncSession):
        try:
            test_rates = [
                {"from": "BTC", "to": "USDT", "rate": "45000.00"},
                {"from": "ETH", "to": "USDT", "rate": "3000.00"},
                {"from": "USDT", "to": "USD", "rate": "1.00"},
                {"from": "BTC", "to": "ETH", "rate": "15.00"},
            ]

            for rate_data in test_rates:
                await self.upsert_exchange_rate(
                    db=db,
                    from_currency=rate_data["from"],
                    to_currency=rate_data["to"],
                    rate=Decimal(rate_data["rate"]),
                    source="test"
                )

            logger.info("🔄 Курсы валют обновлены")

        except Exception as e:
            logger.error("❌ Не удалось обновить курсы валют", error=str(e), exc_info=True)

    async def upsert_exchange_rate(
        self,
        db: AsyncSession,
        from_currency: str,
        to_currency: str,
        rate: Decimal,
        source: str,
        spread_percentage: Decimal = Decimal("0.001")
    ):
        try:
            spread_amount = rate * spread_percentage
            buy_rate = rate - spread_amount
            sell_rate = rate + spread_amount

            query = select(ExchangeRate).where(
                and_(
                    ExchangeRate.from_currency == from_currency,
                    ExchangeRate.to_currency == to_currency,
                    ExchangeRate.source == source
                )
            )

            result = await db.execute(query)
            existing_rate = result.scalar_one_or_none()

            if existing_rate:
                existing_rate.rate = rate
                existing_rate.buy_rate = buy_rate
                existing_rate.sell_rate = sell_rate
                existing_rate.spread_percentage = spread_percentage
                existing_rate.updated_at = datetime.utcnow()
            else:
                new_rate = ExchangeRate(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=rate,
                    buy_rate=buy_rate,
                    sell_rate=sell_rate,
                    spread_percentage=spread_percentage,
                    source=source
                )
                db.add(new_rate)

            await db.commit()

            cache_key = f"{from_currency}_{to_currency}"
            if cache_key in self._rate_cache:
                del self._rate_cache[cache_key]
                del self._cache_timestamps[cache_key]

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to upsert exchange rate",
                from_currency=from_currency,
                to_currency=to_currency,
                rate=str(rate),
                error=str(e),
                exc_info=True
            )


exchange_service = ExchangeService()
