from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, asc
from sqlalchemy.orm import selectinload
import structlog
import uuid
import json

from app.config import settings
from app.models.user import User
from app.models.p2p import (
    P2POrder, P2PTrade, P2PChatMessage, P2PUserStats,
    P2POrderType, P2POrderStatus, P2PPaymentMethod
)
from app.models.transaction import Transaction, TransactionType, TransactionStatus, TransactionDirection
from app.services.wallet import wallet_service
from app.utils.exceptions import (
    P2PError,
    InsufficientFundsError,
    ValidationError,
    NotFoundError,
    PermissionError
)

logger = structlog.get_logger(__name__)


class P2PService:
    def __init__(self):
        self.max_order_amount = Decimal("1000000")
        self.min_order_amount = Decimal("1")
        self.default_expiry_hours = 24 * 7
        self.max_expiry_hours = 24 * 30
        self.escrow_fee_percent = Decimal("0.5")
        self.supported_fiat_currencies = [
            "RUB","USD","EUR","GBP","CNY","KZT","UZS","GEL","TRY","AMD",
            "THB","INR","BRL","IDR","AZN","AED","PLN","ILS","KGS","TJS",
            "BYN","UAH","JPY","KRW"
        ]
        self.supported_crypto_currencies = ["BTC", "ETH", "USDT", "LTC", "BNB", "TRX", "TON"]

    async def create_order(
        self,
        db: AsyncSession,
        creator: User,
        order_type: P2POrderType,
        crypto_currency: str,
        crypto_amount: str,
        fiat_currency: str,
        price_per_unit: str,
        payment_methods: List[str],
        min_amount: str = None,
        max_amount: str = None,
        payment_details: str = None,
        terms: str = None,
        auto_reply: str = None,
        payment_timeout_minutes: int = 30,
        expires_in_hours: int = None,
        min_trades: int = 0,
        min_completion_rate: float = 0,
        country: str = None,
        city: str = None
    ) -> P2POrder:

        creator_id = creator.id

        try:
            await self._validate_order_params(
                order_type, crypto_currency, crypto_amount, fiat_currency,
                price_per_unit, payment_methods, min_amount, max_amount
            )

            if order_type == P2POrderType.SELL:
                await self._check_seller_balance(db, creator, crypto_currency, crypto_amount)

            crypto_decimal = Decimal(crypto_amount)
            price_decimal = Decimal(price_per_unit)
            fiat_amount = str(crypto_decimal * price_decimal)

            expires_at = None
            if expires_in_hours:
                if expires_in_hours > self.max_expiry_hours:
                    raise ValidationError(f"Maximum expiry time is {self.max_expiry_hours} hours")
                expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
            else:
                expires_at = datetime.utcnow() + timedelta(hours=self.default_expiry_hours)

            order_id = await self._generate_unique_order_id(db)

            order = P2POrder(
                id=str(uuid.uuid4()),
                order_id=order_id,
                creator_id=creator_id,
                type=order_type.value,
                crypto_currency=crypto_currency,
                crypto_amount=crypto_amount,
                fiat_currency=fiat_currency,
                fiat_amount=fiat_amount,
                price_per_unit=price_per_unit,
                min_amount=min_amount,
                max_amount=max_amount,
                payment_methods=json.dumps(payment_methods),
                payment_details=payment_details,
                terms=terms,
                auto_reply=auto_reply,
                payment_timeout_minutes=payment_timeout_minutes,
                expires_at=expires_at,
                min_trades=min_trades,
                min_completion_rate=min_completion_rate,
                country=country,
                city=city
            )

            db.add(order)

            if order_type == P2POrderType.SELL:
                await self._freeze_crypto_for_sell_order(db, creator, crypto_currency, crypto_amount, order.id)

            await db.commit()
            await db.refresh(order)

            logger.info(
                "P2P order created",
                order_id=order.order_id,
                creator_id=creator_id,
                type=order_type.value,
                crypto_currency=crypto_currency,
                crypto_amount=crypto_amount,
                fiat_currency=fiat_currency,
                fiat_amount=fiat_amount
            )

            return order

        except Exception as e:
            await db.rollback()
            logger.error(
                "P2P order creation failed",
                creator_id=creator_id,
                type=order_type.value,
                crypto_currency=crypto_currency,
                error=str(e),
                exc_info=True
            )
            raise P2PError(f"Failed to create P2P order: {str(e)}")

    async def match_order(
        self,
        db: AsyncSession,
        order_id: str,
        matcher: User,
        trade_amount: str,
        payment_method: str,
        message: str = None
    ) -> P2PTrade:

        try:
            order = await self.get_order_by_id(db, order_id)
            if not order:
                raise NotFoundError("Order not found")

            user_stats = await self.get_user_stats(db, matcher.id)
            if not order.can_match_with_user(matcher.id, {
                "trades_count": user_stats.total_trades if user_stats else 0,
                "completion_rate": user_stats.completion_rate if user_stats else 0
            }):
                raise P2PError("Cannot match with this order")

            trade_amount_decimal = Decimal(trade_amount)
            if order.min_amount and trade_amount_decimal < Decimal(order.min_amount):
                raise ValidationError(f"Trade amount below minimum: {order.min_amount}")
            if order.max_amount and trade_amount_decimal > Decimal(order.max_amount):
                raise ValidationError(f"Trade amount above maximum: {order.max_amount}")

            available_methods = order.get_payment_methods_list()
            if payment_method not in available_methods:
                raise ValidationError(f"Payment method {payment_method} not supported")

            crypto_amount = order.calculate_crypto_amount(trade_amount)

            if order.type == P2POrderType.SELL:
                buyer_id = matcher.id
                seller_id = order.creator_id
            else:
                buyer_id = order.creator_id
                seller_id = matcher.id

            if order.type == P2POrderType.BUY:
                await self._check_buyer_balance(db, matcher, order.crypto_currency, crypto_amount)

            trade_id = await self._generate_unique_trade_id(db)

            trade = P2PTrade(
                id=str(uuid.uuid4()),
                trade_id=trade_id,
                order_id=order.id,
                buyer_id=buyer_id,
                seller_id=seller_id,
                crypto_currency=order.crypto_currency,
                crypto_amount=crypto_amount,
                fiat_currency=order.fiat_currency,
                fiat_amount=trade_amount,
                price_per_unit=order.price_per_unit,
                payment_method=payment_method,
                payment_details=order.payment_details
            )

            db.add(trade)

            order.matches_count += 1

            if order.type == P2POrderType.BUY:
                await self._freeze_crypto_for_trade(db, matcher, order.crypto_currency, crypto_amount, trade.id)

            if message:
                await self._add_chat_message(db, trade.id, matcher.id, message, is_system=False)

            await self._add_chat_message(
                db, trade.id, None,
                f"Trade created. Amount: {crypto_amount} {order.crypto_currency} for {trade_amount} {order.fiat_currency}",
                is_system=True
            )

            await db.commit()
            await db.refresh(trade)

            logger.info(
                "P2P trade created",
                trade_id=trade.trade_id,
                order_id=order.order_id,
                buyer_id=buyer_id,
                seller_id=seller_id,
                crypto_amount=crypto_amount,
                fiat_amount=trade_amount
            )

            return trade

        except Exception as e:
            await db.rollback()
            logger.error(
                "P2P trade creation failed",
                order_id=order_id,
                matcher_id=matcher.id,
                error=str(e),
                exc_info=True
            )
            raise P2PError(f"Failed to create P2P trade: {str(e)}")

    async def start_trade(
        self,
        db: AsyncSession,
        trade_id: str,
        user: User
    ) -> P2PTrade:

        try:
            trade = await self.get_trade_by_id(db, trade_id)
            if not trade:
                raise NotFoundError("Trade not found")

            if trade.buyer_id != user.id and trade.seller_id != user.id:
                raise PermissionError("Access denied")

            if trade.status != P2POrderStatus.MATCHED:
                raise P2PError(f"Cannot start trade with status {trade.status}")

            trade.start_trade()

            await self._add_chat_message(
                db, trade.id, None,
                f"Trade started. Payment timeout: {trade.payment_timeout_at}",
                is_system=True
            )

            await db.commit()
            await db.refresh(trade)

            logger.info(
                "P2P trade started",
                trade_id=trade.trade_id,
                user_id=user.id
            )

            return trade

        except Exception as e:
            await db.rollback()
            logger.error(
                "P2P trade start failed",
                trade_id=trade_id,
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            raise P2PError(f"Failed to start P2P trade: {str(e)}")

    async def confirm_payment(
        self,
        db: AsyncSession,
        trade_id: str,
        user: User,
        is_buyer: bool
    ) -> P2PTrade:

        try:
            trade = await self.get_trade_by_id(db, trade_id)
            if not trade:
                raise NotFoundError("Trade not found")

            if is_buyer and trade.buyer_id != user.id:
                raise PermissionError("Only buyer can confirm payment")
            if not is_buyer and trade.seller_id != user.id:
                raise PermissionError("Only seller can confirm payment receipt")

            if trade.status != P2POrderStatus.IN_PROGRESS:
                raise P2PError(f"Cannot confirm payment for trade with status {trade.status}")

            if is_buyer:
                trade.confirm_payment_by_buyer()
                message = "Payment confirmed by buyer"
            else:
                trade.confirm_payment_by_seller()
                message = "Payment receipt confirmed by seller"

            await self._add_chat_message(db, trade.id, user.id, message, is_system=True)

            if trade.payment_confirmed_by_buyer and trade.payment_confirmed_by_seller:
                await self._release_crypto_to_buyer(db, trade)
                await self._add_chat_message(
                    db, trade.id, None,
                    f"Crypto released to buyer. Trade completed!",
                    is_system=True
                )

            await db.commit()
            await db.refresh(trade)

            logger.info(
                "P2P payment confirmed",
                trade_id=trade.trade_id,
                user_id=user.id,
                is_buyer=is_buyer
            )

            return trade

        except Exception as e:
            await db.rollback()
            logger.error(
                "P2P payment confirmation failed",
                trade_id=trade_id,
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            raise P2PError(f"Failed to confirm payment: {str(e)}")

    async def cancel_trade(
        self,
        db: AsyncSession,
        trade_id: str,
        user: User,
        reason: str = None
    ) -> P2PTrade:

        try:
            trade = await self.get_trade_by_id(db, trade_id)
            if not trade:
                raise NotFoundError("Trade not found")

            if trade.buyer_id != user.id and trade.seller_id != user.id:
                raise PermissionError("Access denied")

            if trade.status not in [P2POrderStatus.MATCHED, P2POrderStatus.IN_PROGRESS]:
                raise P2PError(f"Cannot cancel trade with status {trade.status}")

            trade.cancel_trade(reason)

            await self._unfreeze_crypto_for_cancelled_trade(db, trade)

            await self._add_chat_message(
                db, trade.id, user.id,
                f"Trade cancelled. Reason: {reason or 'No reason provided'}",
                is_system=True
            )

            await db.commit()
            await db.refresh(trade)

            logger.info(
                "P2P trade cancelled",
                trade_id=trade.trade_id,
                user_id=user.id,
                reason=reason
            )

            return trade

        except Exception as e:
            await db.rollback()
            logger.error(
                "P2P trade cancellation failed",
                trade_id=trade_id,
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            raise P2PError(f"Failed to cancel trade: {str(e)}")

    async def create_dispute(
        self,
        db: AsyncSession,
        trade_id: str,
        user: User,
        reason: str
    ) -> P2PTrade:

        try:
            trade = await self.get_trade_by_id(db, trade_id)
            if not trade:
                raise NotFoundError("Trade not found")

            if trade.buyer_id != user.id and trade.seller_id != user.id:
                raise PermissionError("Access denied")

            if trade.status != P2POrderStatus.IN_PROGRESS:
                raise P2PError(f"Cannot create dispute for trade with status {trade.status}")

            trade.create_dispute(reason)

            await self._add_chat_message(
                db, trade.id, user.id,
                f"Dispute created. Reason: {reason}",
                is_system=True
            )

            await db.commit()
            await db.refresh(trade)

            logger.info(
                "P2P dispute created",
                trade_id=trade.trade_id,
                user_id=user.id,
                reason=reason
            )

            return trade

        except Exception as e:
            await db.rollback()
            logger.error(
                "P2P dispute creation failed",
                trade_id=trade_id,
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            raise P2PError(f"Failed to create dispute: {str(e)}")

    async def get_orders(
        self,
        db: AsyncSession,
        order_type: P2POrderType = None,
        crypto_currency: str = None,
        fiat_currency: str = None,
        payment_method: str = None,
        country: str = None,
        min_amount: str = None,
        max_amount: str = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> List[P2POrder]:

        query = select(P2POrder).where(P2POrder.status == P2POrderStatus.ACTIVE)

        if order_type:
            query = query.where(P2POrder.type == order_type.value)

        if crypto_currency:
            query = query.where(P2POrder.crypto_currency == crypto_currency)

        if fiat_currency:
            query = query.where(P2POrder.fiat_currency == fiat_currency)

        if payment_method:
            query = query.where(P2POrder.payment_methods.contains(payment_method))

        if country:
            query = query.where(P2POrder.country == country)

        if min_amount:
            query = query.where(
                or_(
                    P2POrder.min_amount.is_(None),
                    P2POrder.min_amount <= min_amount
                )
            )

        if max_amount:
            query = query.where(
                or_(
                    P2POrder.max_amount.is_(None),
                    P2POrder.max_amount >= max_amount
                )
            )

        if sort_by == "price" and sort_order == "asc":
            query = query.order_by(asc(P2POrder.price_per_unit))
        elif sort_by == "price" and sort_order == "desc":
            query = query.order_by(desc(P2POrder.price_per_unit))
        elif sort_order == "asc":
            query = query.order_by(asc(getattr(P2POrder, sort_by, P2POrder.created_at)))
        else:
            query = query.order_by(desc(getattr(P2POrder, sort_by, P2POrder.created_at)))

        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        return result.scalars().all()

    async def get_order_by_id(
        self,
        db: AsyncSession,
        order_id: str
    ) -> Optional[P2POrder]:
        result = await db.execute(
            select(P2POrder).where(P2POrder.order_id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_trade_by_id(
        self,
        db: AsyncSession,
        trade_id: str,
        include_messages: bool = False
    ) -> Optional[P2PTrade]:
        query = select(P2PTrade).where(P2PTrade.trade_id == trade_id)

        if include_messages:
            query = query.options(selectinload(P2PTrade.chat_messages))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_stats(
        self,
        db: AsyncSession,
        user_id: int,
        days: int = None
    ) -> Optional[P2PUserStats]:
        query = select(P2PUserStats).where(P2PUserStats.user_id == user_id)

        if days:
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.where(P2PUserStats.updated_at >= cutoff_date)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _validate_order_params(
        self,
        order_type: P2POrderType,
        crypto_currency: str,
        crypto_amount: str,
        fiat_currency: str,
        price_per_unit: str,
        payment_methods: List[str],
        min_amount: str = None,
        max_amount: str = None
    ):

        if crypto_currency not in self.supported_crypto_currencies:
            raise ValidationError(f"Unsupported crypto currency: {crypto_currency}")

        if fiat_currency not in self.supported_fiat_currencies:
            raise ValidationError(f"Unsupported fiat currency: {fiat_currency}")

        crypto_decimal = Decimal(crypto_amount)
        if crypto_decimal <= 0:
            raise ValidationError("Crypto amount must be positive")

        price_decimal = Decimal(price_per_unit)
        if price_decimal <= 0:
            raise ValidationError("Price must be positive")

        fiat_amount = crypto_decimal * price_decimal
        if fiat_amount < self.min_order_amount:
            raise ValidationError(f"Order amount below minimum: {self.min_order_amount}")
        if fiat_amount > self.max_order_amount:
            raise ValidationError(f"Order amount above maximum: {self.max_order_amount}")

        if min_amount and max_amount:
            if Decimal(min_amount) > Decimal(max_amount):
                raise ValidationError("Min amount cannot be greater than max amount")

        if not payment_methods:
            raise ValidationError("At least one payment method is required")

        valid_methods = [method.value for method in P2PPaymentMethod]
        for method in payment_methods:
            if method not in valid_methods:
                raise ValidationError(f"Invalid payment method: {method}")

    async def _check_seller_balance(
        self,
        db: AsyncSession,
        user: User,
        crypto_currency: str,
        crypto_amount: str
    ):
        wallet = await wallet_service.get_user_wallet(db, user.id, crypto_currency)
        if not wallet:
            raise P2PError(f"No {crypto_currency} wallet found")

        available_balance = Decimal(wallet.available_balance)
        required_amount = Decimal(crypto_amount)

        if available_balance < required_amount:
            raise InsufficientFundsError(
                f"Insufficient {crypto_currency}: available {available_balance}, required {required_amount}"
            )

    async def _check_buyer_balance(
        self,
        db: AsyncSession,
        user: User,
        crypto_currency: str,
        crypto_amount: str
    ):
        await self._check_seller_balance(db, user, crypto_currency, crypto_amount)

    async def _freeze_crypto_for_sell_order(
        self,
        db: AsyncSession,
        user: User,
        crypto_currency: str,
        crypto_amount: str,
        order_id: str
    ):
        wallet = await wallet_service.get_user_wallet(db, user.id, crypto_currency)
        wallet.freeze_balance(crypto_amount)

        await wallet_service.create_transaction(
            db=db,
            user_id=user.id,
            wallet_id=wallet.id,
            transaction_type=TransactionType.P2P,
            currency=crypto_currency,
            amount=crypto_amount,
            direction=TransactionDirection.OUTGOING,
            description=f"P2P order freeze: {order_id}",
            related_object_type="p2p_order",
            related_object_id=order_id
        )

    async def _freeze_crypto_for_trade(
        self,
        db: AsyncSession,
        user: User,
        crypto_currency: str,
        crypto_amount: str,
        trade_id: str
    ):
        wallet = await wallet_service.get_user_wallet(db, user.id, crypto_currency)
        wallet.freeze_balance(crypto_amount)

        await wallet_service.create_transaction(
            db=db,
            user_id=user.id,
            wallet_id=wallet.id,
            transaction_type=TransactionType.P2P,
            currency=crypto_currency,
            amount=crypto_amount,
            direction=TransactionDirection.OUTGOING,
            description=f"P2P trade freeze: {trade_id}",
            related_object_type="p2p_trade",
            related_object_id=trade_id
        )

    async def _release_crypto_to_buyer(
        self,
        db: AsyncSession,
        trade: P2PTrade
    ):
        seller_wallet = await wallet_service.get_user_wallet(db, trade.seller_id, trade.crypto_currency)
        buyer_wallet = await wallet_service.get_user_wallet(db, trade.buyer_id, trade.crypto_currency)

        if not buyer_wallet:
            buyer = await db.get(User, trade.buyer_id)
            buyer_wallet = await wallet_service.create_wallet(
                db=db,
                user=buyer,
                currency=trade.crypto_currency
            )

        seller_wallet.unfreeze_balance(trade.crypto_amount)
        seller_wallet.subtract_balance(trade.crypto_amount)
        buyer_wallet.add_balance(trade.crypto_amount)

        seller_transaction = await wallet_service.create_transaction(
            db=db,
            user_id=trade.seller_id,
            wallet_id=seller_wallet.id,
            transaction_type=TransactionType.P2P,
            currency=trade.crypto_currency,
            amount=trade.crypto_amount,
            direction=TransactionDirection.OUTGOING,
            description=f"P2P trade completed: {trade.trade_id}",
            related_user_id=trade.buyer_id,
            related_object_type="p2p_trade",
            related_object_id=trade.id
        )

        buyer_transaction = await wallet_service.create_transaction(
            db=db,
            user_id=trade.buyer_id,
            wallet_id=buyer_wallet.id,
            transaction_type=TransactionType.P2P,
            currency=trade.crypto_currency,
            amount=trade.crypto_amount,
            direction=TransactionDirection.INCOMING,
            description=f"P2P trade received: {trade.trade_id}",
            related_user_id=trade.seller_id,
            related_object_type="p2p_trade",
            related_object_id=trade.id
        )

        seller_transaction.mark_as_completed()
        buyer_transaction.mark_as_completed()

        trade.release_crypto()

        await self._update_user_stats_after_trade(db, trade)

    async def _unfreeze_crypto_for_cancelled_trade(
        self,
        db: AsyncSession,
        trade: P2PTrade
    ):
        if trade.order.type == P2POrderType.SELL:
            wallet = await wallet_service.get_user_wallet(db, trade.seller_id, trade.crypto_currency)
        else:
            wallet = await wallet_service.get_user_wallet(db, trade.buyer_id, trade.crypto_currency)

        if wallet:
            wallet.unfreeze_balance(trade.crypto_amount)

            user_id = trade.seller_id if trade.order.type == P2POrderType.SELL else trade.buyer_id
            await wallet_service.create_transaction(
                db=db,
                user_id=user_id,
                wallet_id=wallet.id,
                transaction_type=TransactionType.REFUND,
                currency=trade.crypto_currency,
                amount=trade.crypto_amount,
                direction=TransactionDirection.INCOMING,
                description=f"P2P trade cancelled: {trade.trade_id}",
                related_object_type="p2p_trade",
                related_object_id=trade.id
            )

    async def _add_chat_message(
        self,
        db: AsyncSession,
        trade_id: str,
        sender_id: int,
        content: str,
        is_system: bool = False
    ):
        message = P2PChatMessage(
            id=str(uuid.uuid4()),
            trade_id=trade_id,
            sender_id=sender_id,
            content=content,
            is_system=is_system
        )
        db.add(message)

    async def _update_user_stats_after_trade(
        self,
        db: AsyncSession,
        trade: P2PTrade
    ):
        buyer_stats = await self.get_user_stats(db, trade.buyer_id)
        if not buyer_stats:
            buyer_stats = P2PUserStats(user_id=trade.buyer_id)
            db.add(buyer_stats)

        buyer_stats.update_stats_after_trade(trade, is_buyer=True)

        seller_stats = await self.get_user_stats(db, trade.seller_id)
        if not seller_stats:
            seller_stats = P2PUserStats(user_id=trade.seller_id)
            db.add(seller_stats)

        seller_stats.update_stats_after_trade(trade, is_buyer=False)

    async def _generate_unique_order_id(self, db: AsyncSession) -> str:
        max_attempts = 10

        for _ in range(max_attempts):
            order_id = P2POrder.generate_order_id()

            result = await db.execute(
                select(P2POrder.id).where(P2POrder.order_id == order_id).limit(1)
            )

            if not result.scalar_one_or_none():
                return order_id

        raise P2PError("Failed to generate unique order ID")

    async def _generate_unique_trade_id(self, db: AsyncSession) -> str:
        max_attempts = 10

        for _ in range(max_attempts):
            trade_id = P2PTrade.generate_trade_id()

            result = await db.execute(
                select(P2PTrade.id).where(P2PTrade.trade_id == trade_id).limit(1)
            )

            if not result.scalar_one_or_none():
                return trade_id

        raise P2PError("Failed to generate unique trade ID")


p2p_service = P2PService()
