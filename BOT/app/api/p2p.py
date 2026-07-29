from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import structlog

from app.database import get_db
from app.services.auth import get_current_user
from app.services.p2p import p2p_service
from app.models.user import User
from app.models.p2p import P2POrderType, P2POrderStatus, P2PPaymentMethod
from app.schemas.p2p import (
    P2POrderCreateRequest,
    P2PTradeCreateRequest,
    P2POrderResponse,
    P2PTradeResponse,
    P2POrderListResponse,
    P2PTradeListResponse,
    P2PUserStatsResponse,
    P2PChatResponse,
    P2PChatMessageResponse,
    P2POrderFiltersRequest,
    P2PTradeActionRequest,
    P2PDisputeRequest,
    P2PRatingRequest,
    P2PChatMessageRequest,
    P2PMarketStatsResponse,
    P2PPriceStatsResponse,
    P2PErrorResponse
)
from app.utils.exceptions import (
    P2PError,
    InsufficientFundsError,
    ValidationError,
    NotFoundError,
    PermissionError
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/p2p", tags=["p2p"])


@router.post("/orders", response_model=P2POrderResponse)
async def create_order(
    order_data: P2POrderCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        order = await p2p_service.create_order(
            db=db,
            creator=current_user,
            order_type=order_data.type,
            crypto_currency=order_data.crypto_currency,
            crypto_amount=order_data.crypto_amount,
            fiat_currency=order_data.fiat_currency,
            price_per_unit=order_data.price_per_unit,
            payment_methods=order_data.payment_methods,
            min_amount=order_data.min_amount,
            max_amount=order_data.max_amount,
            payment_details=order_data.payment_details,
            terms=order_data.terms,
            auto_reply=order_data.auto_reply,
            payment_timeout_minutes=order_data.payment_timeout_minutes,
            expires_in_hours=order_data.expires_in_hours,
            min_trades=order_data.min_trades,
            min_completion_rate=order_data.min_completion_rate,
            country=order_data.country,
            city=order_data.city
        )

        order_response = P2POrderResponse.from_orm(order)
        order_response.is_active = order.is_active
        order_response.is_expired = order.is_expired

        return order_response

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except InsufficientFundsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    except P2PError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to create P2P order",
            user_id=current_user.id,
            type=order_data.type.value,
            crypto_currency=order_data.crypto_currency,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create P2P order"
        )


@router.get("/orders", response_model=P2POrderListResponse)
async def get_orders(
    type: Optional[P2POrderType] = Query(None, description="Тип ордера"),
    crypto_currency: Optional[str] = Query(None, description="Криптовалюта"),
    fiat_currency: Optional[str] = Query(None, description="Фиатная валюта"),
    payment_method: Optional[str] = Query(None, description="Способ оплаты"),
    country: Optional[str] = Query(None, description="Страна"),
    min_amount: Optional[str] = Query(None, description="Минимальная сумма"),
    max_amount: Optional[str] = Query(None, description="Максимальная сумма"),
    sort_by: str = Query("created_at", description="Поле для сортировки"),
    sort_order: str = Query("desc", description="Порядок сортировки"),
    limit: int = Query(50, ge=1, le=100, description="Количество записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    db: AsyncSession = Depends(get_db)
):
    try:
        orders = await p2p_service.get_orders(
            db=db,
            order_type=type,
            crypto_currency=crypto_currency,
            fiat_currency=fiat_currency,
            payment_method=payment_method,
            country=country,
            min_amount=min_amount,
            max_amount=max_amount,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset
        )

        order_responses = []
        for order in orders:
            order_response = P2POrderResponse.from_orm(order)
            order_response.is_active = order.is_active
            order_response.is_expired = order.is_expired
            order_responses.append(order_response)

        has_more = len(orders) == limit

        return P2POrderListResponse(
            orders=order_responses,
            total=len(orders),
            has_more=has_more
        )

    except Exception as e:
        logger.error(
            "Failed to get P2P orders",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get P2P orders"
        )


@router.get("/orders/{order_id}", response_model=P2POrderResponse)
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        order = await p2p_service.get_order_by_id(db, order_id)

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        order.views_count += 1
        await db.commit()

        order_response = P2POrderResponse.from_orm(order)
        order_response.is_active = order.is_active
        order_response.is_expired = order.is_expired

        return order_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get P2P order",
            order_id=order_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get P2P order"
        )


@router.post("/trades", response_model=P2PTradeResponse)
async def create_trade(
    trade_data: P2PTradeCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        trade = await p2p_service.match_order(
            db=db,
            order_id=trade_data.order_id,
            matcher=current_user,
            trade_amount=trade_data.trade_amount,
            payment_method=trade_data.payment_method,
            message=trade_data.message
        )

        trade_response = P2PTradeResponse.from_orm(trade)
        trade_response.is_payment_expired = trade.is_payment_expired

        return trade_response

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except P2PError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to create P2P trade",
            user_id=current_user.id,
            order_id=trade_data.order_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create P2P trade"
        )


@router.get("/trades", response_model=P2PTradeListResponse)
async def get_user_trades(
    status: Optional[P2POrderStatus] = Query(None, description="Статус сделки"),
    limit: int = Query(50, ge=1, le=100, description="Количество записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        trades = []

        trade_responses = []
        for trade in trades:
            trade_response = P2PTradeResponse.from_orm(trade)
            trade_response.is_payment_expired = trade.is_payment_expired
            trade_responses.append(trade_response)

        has_more = len(trades) == limit

        return P2PTradeListResponse(
            trades=trade_responses,
            total=len(trades),
            has_more=has_more
        )

    except Exception as e:
        logger.error(
            "Failed to get user trades",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user trades"
        )


@router.get("/trades/{trade_id}", response_model=P2PTradeResponse)
async def get_trade(
    trade_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        trade = await p2p_service.get_trade_by_id(db, trade_id)

        if not trade:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trade not found"
            )

        if trade.buyer_id != current_user.id and trade.seller_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        trade_response = P2PTradeResponse.from_orm(trade)
        trade_response.is_payment_expired = trade.is_payment_expired

        return trade_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get P2P trade",
            user_id=current_user.id,
            trade_id=trade_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get P2P trade"
        )


@router.post("/trades/{trade_id}/start", response_model=P2PTradeResponse)
async def start_trade(
    trade_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        trade = await p2p_service.start_trade(
            db=db,
            trade_id=trade_id,
            user=current_user
        )

        trade_response = P2PTradeResponse.from_orm(trade)
        trade_response.is_payment_expired = trade.is_payment_expired

        return trade_response

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except P2PError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to start P2P trade",
            user_id=current_user.id,
            trade_id=trade_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start P2P trade"
        )


@router.post("/trades/{trade_id}/confirm-payment", response_model=P2PTradeResponse)
async def confirm_payment(
    trade_id: str,
    is_buyer: bool = Query(..., description="Подтверждение от покупателя или продавца"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        trade = await p2p_service.confirm_payment(
            db=db,
            trade_id=trade_id,
            user=current_user,
            is_buyer=is_buyer
        )

        trade_response = P2PTradeResponse.from_orm(trade)
        trade_response.is_payment_expired = trade.is_payment_expired

        return trade_response

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except P2PError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to confirm payment",
            user_id=current_user.id,
            trade_id=trade_id,
            is_buyer=is_buyer,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm payment"
        )


@router.post("/trades/{trade_id}/cancel", response_model=P2PTradeResponse)
async def cancel_trade(
    trade_id: str,
    reason: Optional[str] = Query(None, description="Причина отмены"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        trade = await p2p_service.cancel_trade(
            db=db,
            trade_id=trade_id,
            user=current_user,
            reason=reason
        )

        trade_response = P2PTradeResponse.from_orm(trade)
        trade_response.is_payment_expired = trade.is_payment_expired

        return trade_response

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except P2PError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to cancel P2P trade",
            user_id=current_user.id,
            trade_id=trade_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel P2P trade"
        )


@router.post("/trades/{trade_id}/dispute", response_model=P2PTradeResponse)
async def create_dispute(
    trade_id: str,
    dispute_data: P2PDisputeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        trade = await p2p_service.create_dispute(
            db=db,
            trade_id=trade_id,
            user=current_user,
            reason=dispute_data.reason
        )

        trade_response = P2PTradeResponse.from_orm(trade)
        trade_response.is_payment_expired = trade.is_payment_expired

        return trade_response

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except P2PError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to create dispute",
            user_id=current_user.id,
            trade_id=trade_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create dispute"
        )


@router.get("/trades/{trade_id}/chat", response_model=P2PChatResponse)
async def get_trade_chat(
    trade_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        trade = await p2p_service.get_trade_by_id(db, trade_id, include_messages=True)

        if not trade:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trade not found"
            )

        if trade.buyer_id != current_user.id and trade.seller_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        messages = [P2PChatMessageResponse.from_orm(msg) for msg in trade.chat_messages]

        return P2PChatResponse(
            trade_id=trade.trade_id,
            messages=messages,
            total_messages=len(messages)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get trade chat",
            user_id=current_user.id,
            trade_id=trade_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trade chat"
        )


@router.get("/users/{user_id}/stats", response_model=P2PUserStatsResponse)
async def get_user_stats(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        stats = await p2p_service.get_user_stats(db, user_id)

        if not stats:
            from app.models.p2p import P2PUserStats
            stats = P2PUserStats(user_id=user_id)

        stats_response = P2PUserStatsResponse.from_orm(stats)
        stats_response.completion_rate = stats.completion_rate
        stats_response.dispute_rate = stats.dispute_rate

        return stats_response

    except Exception as e:
        logger.error(
            "Failed to get user stats",
            user_id=user_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user stats"
        )


@router.get("/payment-methods")
async def get_payment_methods():
    methods = []
    for method in P2PPaymentMethod:
        methods.append({
            "code": method.value,
            "name": method.value.replace("_", " ").title(),
            "description": f"Payment via {method.value.replace('_', ' ')}"
        })

    return {
        "payment_methods": methods
    }


@router.get("/currencies")
async def get_supported_currencies():
    crypto_currencies = [
        {"code": "BTC", "name": "Bitcoin", "type": "crypto"},
        {"code": "ETH", "name": "Ethereum", "type": "crypto"},
        {"code": "USDT", "name": "Tether USD", "type": "crypto"},
        {"code": "LTC", "name": "Litecoin", "type": "crypto"},
        {"code": "BNB", "name": "Binance Coin", "type": "crypto"},
        {"code": "TRX", "name": "TRON", "type": "crypto"},
        {"code": "TON", "name": "The Open Network", "type": "crypto"}
    ]

    fiat_currencies = [
        {"code": "USD", "name": "US Dollar", "type": "fiat"},
        {"code": "EUR", "name": "Euro", "type": "fiat"},
        {"code": "RUB", "name": "Russian Ruble", "type": "fiat"},
        {"code": "CNY", "name": "Chinese Yuan", "type": "fiat"},
        {"code": "KRW", "name": "South Korean Won", "type": "fiat"},
        {"code": "JPY", "name": "Japanese Yen", "type": "fiat"}
    ]

    return {
        "crypto_currencies": crypto_currencies,
        "fiat_currencies": fiat_currencies
    }


@router.get("/market/stats", response_model=P2PMarketStatsResponse)
async def get_market_stats(
    db: AsyncSession = Depends(get_db)
):
    try:
        return P2PMarketStatsResponse(
            total_orders=0,
            active_orders=0,
            total_trades=0,
            completed_trades=0,
            total_volume_usd="0",
            average_completion_time_minutes=0,
            popular_currencies=[],
            popular_payment_methods=[]
        )

    except Exception as e:
        logger.error(
            "Failed to get market stats",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get market stats"
        )
