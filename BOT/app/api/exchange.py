from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from decimal import Decimal
import structlog

from app.database import get_db
from app.services.auth import get_current_user
from app.services.exchange import exchange_service
from app.models.user import User
from app.schemas.exchange import (
    ExchangeRateRequest,
    ExchangeCalculateRequest,
    ExchangeCreateRequest,
    ExchangeProcessRequest,
    ExchangeCancelRequest,
    ExchangeListRequest,
    ExchangeRateResponse,
    ExchangeCalculationResponse,
    ExchangeResponse,
    ExchangeListResponse,
    ExchangeProviderResponse,
    ExchangeLimitResponse,
    ExchangeStatsResponse,
    SupportedPairsResponse,
    CurrencyListResponse,
    ExchangeStatusEnum,
    ExchangeErrorResponse
)
from app.utils.exceptions import (
    ValidationError,
    NotFoundError,
    InsufficientFundsError,
    ExchangeError
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/exchange", tags=["exchange"])


@router.get("/rates/{from_currency}/{to_currency}", response_model=ExchangeRateResponse)
async def get_exchange_rate(
    from_currency: str,
    to_currency: str,
    amount: Optional[Decimal] = Query(None, gt=0, description="Сумма для расчета"),
    db: AsyncSession = Depends(get_db)
):
    try:
        rate = await exchange_service.get_exchange_rate(
            db=db,
            from_currency=from_currency.upper(),
            to_currency=to_currency.upper()
        )

        if not rate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exchange rate not found for {from_currency}/{to_currency}"
            )

        return ExchangeRateResponse.from_orm(rate)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get exchange rate",
            from_currency=from_currency,
            to_currency=to_currency,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get exchange rate"
        )


@router.post("/calculate", response_model=ExchangeCalculationResponse)
async def calculate_exchange(
    request: ExchangeCalculateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        calculation = await exchange_service.calculate_exchange(
            db=db,
            from_currency=request.from_currency,
            to_currency=request.to_currency,
            from_amount=request.from_amount,
            user=current_user
        )

        return ExchangeCalculationResponse(**calculation)

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ExchangeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to calculate exchange",
            user_id=current_user.id,
            from_currency=request.from_currency,
            to_currency=request.to_currency,
            from_amount=str(request.from_amount),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate exchange"
        )


@router.post("/create", response_model=ExchangeResponse)
async def create_exchange(
    request: ExchangeCreateRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        ip_address = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("user-agent")

        exchange = await exchange_service.create_exchange(
            db=db,
            user=current_user,
            from_currency=request.from_currency,
            to_currency=request.to_currency,
            from_amount=request.from_amount,
            ip_address=ip_address,
            user_agent=user_agent
        )

        exchange_response = ExchangeResponse.from_orm(exchange)
        exchange_response.is_expired = exchange.is_expired
        exchange_response.is_pending = exchange.is_pending
        exchange_response.is_completed = exchange.is_completed
        exchange_response.is_failed = exchange.is_failed
        exchange_response.total_from_amount = str(exchange.total_from_amount)
        exchange_response.net_to_amount = str(exchange.net_to_amount)

        return exchange_response

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
    except ExchangeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to create exchange",
            user_id=current_user.id,
            from_currency=request.from_currency,
            to_currency=request.to_currency,
            from_amount=str(request.from_amount),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create exchange"
        )


@router.post("/process", response_model=ExchangeResponse)
async def process_exchange(
    request: ExchangeProcessRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        exchange = await exchange_service.process_exchange(
            db=db,
            exchange_id=request.exchange_id,
            user=current_user
        )

        exchange_response = ExchangeResponse.from_orm(exchange)
        exchange_response.is_expired = exchange.is_expired
        exchange_response.is_pending = exchange.is_pending
        exchange_response.is_completed = exchange.is_completed
        exchange_response.is_failed = exchange.is_failed
        exchange_response.total_from_amount = str(exchange.total_from_amount)
        exchange_response.net_to_amount = str(exchange.net_to_amount)

        return exchange_response

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
    except InsufficientFundsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    except ExchangeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to process exchange",
            user_id=current_user.id,
            exchange_id=request.exchange_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process exchange"
        )


@router.post("/cancel", response_model=ExchangeResponse)
async def cancel_exchange(
    request: ExchangeCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        exchange = await exchange_service.cancel_exchange(
            db=db,
            exchange_id=request.exchange_id,
            user=current_user,
            reason=request.reason
        )

        exchange_response = ExchangeResponse.from_orm(exchange)
        exchange_response.is_expired = exchange.is_expired
        exchange_response.is_pending = exchange.is_pending
        exchange_response.is_completed = exchange.is_completed
        exchange_response.is_failed = exchange.is_failed
        exchange_response.total_from_amount = str(exchange.total_from_amount)
        exchange_response.net_to_amount = str(exchange.net_to_amount)

        return exchange_response

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
    except Exception as e:
        logger.error(
            "Failed to cancel exchange",
            user_id=current_user.id,
            exchange_id=request.exchange_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel exchange"
        )


@router.get("/exchanges", response_model=ExchangeListResponse)
async def get_user_exchanges(
    status: Optional[ExchangeStatusEnum] = Query(None, description="Фильтр по статусу"),
    from_currency: Optional[str] = Query(None, description="Фильтр по исходной валюте"),
    to_currency: Optional[str] = Query(None, description="Фильтр по целевой валюте"),
    limit: int = Query(50, ge=1, le=100, description="Количество записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        exchanges = await exchange_service.get_user_exchanges(
            db=db,
            user_id=current_user.id,
            status=status.value if status else None,
            limit=limit,
            offset=offset
        )

        exchange_responses = []
        for exchange in exchanges:
            exchange_response = ExchangeResponse.from_orm(exchange)
            exchange_response.is_expired = exchange.is_expired
            exchange_response.is_pending = exchange.is_pending
            exchange_response.is_completed = exchange.is_completed
            exchange_response.is_failed = exchange.is_failed
            exchange_response.total_from_amount = str(exchange.total_from_amount)
            exchange_response.net_to_amount = str(exchange.net_to_amount)
            exchange_responses.append(exchange_response)

        has_more = len(exchanges) == limit

        return ExchangeListResponse(
            exchanges=exchange_responses,
            total=len(exchanges),
            has_more=has_more
        )

    except Exception as e:
        logger.error(
            "Failed to get user exchanges",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user exchanges"
        )


@router.get("/exchanges/{exchange_id}", response_model=ExchangeResponse)
async def get_exchange(
    exchange_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        exchange = await exchange_service.get_exchange_by_id(db, exchange_id)

        if not exchange:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exchange not found"
            )

        if exchange.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        exchange_response = ExchangeResponse.from_orm(exchange)
        exchange_response.is_expired = exchange.is_expired
        exchange_response.is_pending = exchange.is_pending
        exchange_response.is_completed = exchange.is_completed
        exchange_response.is_failed = exchange.is_failed
        exchange_response.total_from_amount = str(exchange.total_from_amount)
        exchange_response.net_to_amount = str(exchange.net_to_amount)

        return exchange_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get exchange",
            user_id=current_user.id,
            exchange_id=exchange_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get exchange"
        )


@router.get("/limits", response_model=List[ExchangeLimitResponse])
async def get_user_limits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        return []

    except Exception as e:
        logger.error(
            "Failed to get user limits",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user limits"
        )


@router.get("/pairs", response_model=SupportedPairsResponse)
async def get_supported_pairs(db: AsyncSession = Depends(get_db)):
    try:
        pairs = await exchange_service.get_supported_pairs(db)

        return SupportedPairsResponse(pairs=pairs)

    except Exception as e:
        logger.error(
            "Failed to get supported pairs",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get supported pairs"
        )


@router.get("/currencies", response_model=CurrencyListResponse)
async def get_supported_currencies():
    crypto_currencies = [
        {"code": "BTC", "name": "Bitcoin"},
        {"code": "ETH", "name": "Ethereum"},
        {"code": "USDT", "name": "Tether USD"},
        {"code": "LTC", "name": "Litecoin"},
        {"code": "BNB", "name": "Binance Coin"},
        {"code": "TRX", "name": "TRON"},
        {"code": "TON", "name": "The Open Network"}
    ]

    fiat_currencies = [
        {"code": "USD", "name": "US Dollar"},
        {"code": "EUR", "name": "Euro"},
        {"code": "RUB", "name": "Russian Ruble"},
        {"code": "CNY", "name": "Chinese Yuan"},
        {"code": "KRW", "name": "Korean Won"},
        {"code": "JPY", "name": "Japanese Yen"}
    ]

    return CurrencyListResponse(
        crypto_currencies=crypto_currencies,
        fiat_currencies=fiat_currencies
    )


@router.get("/stats", response_model=ExchangeStatsResponse)
async def get_exchange_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        return ExchangeStatsResponse(
            total_exchanges=0,
            completed_exchanges=0,
            failed_exchanges=0,
            cancelled_exchanges=0,
            total_volume_usd="0",
            average_exchange_amount="0",
            popular_pairs=[],
            success_rate=0.0,
            average_processing_time_seconds=None
        )

    except Exception as e:
        logger.error(
            "Failed to get exchange stats",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get exchange stats"
        )


@router.post("/rates/update")
async def update_exchange_rates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        await exchange_service.update_exchange_rates(db)

        return {"message": "Exchange rates updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update exchange rates",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update exchange rates"
        )


@router.get("/getExchangeRates")
async def get_exchange_rates_legacy():
    return await get_supported_currencies()


@router.post("/createExchange")
async def create_exchange_legacy(
    request: ExchangeCreateRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await create_exchange(request, http_request, current_user, db)


@router.get("/getExchanges")
async def get_exchanges_legacy(
    status: Optional[ExchangeStatusEnum] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_user_exchanges(status, None, None, limit, offset, current_user, db)
