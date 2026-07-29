from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import structlog

from app.database import get_db
from app.services.auth import get_current_user
from app.services.wallet import wallet_service
from app.models.user import User
from app.models.wallet import WalletStatus
from app.models.transaction import TransactionType, TransactionStatus
from app.schemas.wallet import (
    WalletCreate,
    WalletResponse,
    WalletListResponse,
    UserBalanceResponse,
    SendCryptoRequest,
    TransactionResponse,
    TransactionListResponse,
    TransactionHistoryRequest,
    AddressValidationRequest,
    AddressValidationResponse,
    FeeEstimateRequest,
    FeeEstimateResponse,
    WalletStatsResponse,
    SupportedCurrenciesResponse,
    WalletErrorResponse
)
from app.utils.exceptions import (
    WalletError,
    InsufficientFundsError,
    InvalidAddressError,
    TransactionError,
    ValidationError
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("/", response_model=WalletListResponse)
async def get_wallets(
    currency: Optional[str] = Query(None, description="Фильтр по валюте"),
    status: Optional[WalletStatus] = Query(None, description="Фильтр по статусу"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        wallets = await wallet_service.get_user_wallets(
            db=db,
            user_id=current_user.id,
            currency=currency,
            status=status
        )

        return WalletListResponse(
            wallets=[WalletResponse.from_orm(wallet) for wallet in wallets],
            total=len(wallets)
        )

    except Exception as e:
        logger.error(
            "Failed to get wallets",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get wallets"
        )


@router.post("/create", response_model=WalletResponse)
async def create_wallet(
    wallet_data: WalletCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        wallet = await wallet_service.create_wallet(
            db=db,
            user=current_user,
            currency=wallet_data.currency,
            network=wallet_data.network
        )

        return WalletResponse.from_orm(wallet)

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except WalletError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to create wallet",
            user_id=current_user.id,
            currency=wallet_data.currency,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create wallet"
        )


@router.get("/balance", response_model=UserBalanceResponse)
async def get_balance(
    currency: Optional[str] = Query(None, description="Конкретная валюта"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        balances = await wallet_service.get_user_balance(
            db=db,
            user_id=current_user.id,
            currency=currency
        )

        return UserBalanceResponse(balances=balances)

    except Exception as e:
        logger.error(
            "Failed to get balance",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get balance"
        )


@router.post("/send", response_model=TransactionResponse)
async def send_crypto(
    send_data: SendCryptoRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        transaction = await wallet_service.send_crypto(
            db=db,
            user=current_user,
            currency=send_data.currency,
            to_address=send_data.to_address,
            amount=send_data.amount,
            network=send_data.network,
            description=send_data.description
        )

        return TransactionResponse.from_orm(transaction)

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except WalletError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InsufficientFundsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    except InvalidAddressError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except TransactionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to send crypto",
            user_id=current_user.id,
            currency=send_data.currency,
            amount=send_data.amount,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send crypto"
        )


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    currency: Optional[str] = Query(None, description="Фильтр по валюте"),
    transaction_type: Optional[TransactionType] = Query(None, description="Фильтр по типу"),
    status: Optional[TransactionStatus] = Query(None, description="Фильтр по статусу"),
    limit: int = Query(50, ge=1, le=100, description="Количество записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        transactions = await wallet_service.get_transaction_history(
            db=db,
            user_id=current_user.id,
            currency=currency,
            transaction_type=transaction_type,
            status=status,
            limit=limit,
            offset=offset
        )

        has_more = len(transactions) == limit

        return TransactionListResponse(
            transactions=[TransactionResponse.from_orm(tx) for tx in transactions],
            total=len(transactions),
            has_more=has_more
        )

    except Exception as e:
        logger.error(
            "Failed to get transactions",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get transactions"
        )


@router.get("/{wallet_id}", response_model=WalletResponse)
async def get_wallet(
    wallet_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        wallet = await wallet_service.get_wallet_by_id(
            db=db,
            wallet_id=wallet_id,
            user_id=current_user.id
        )

        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )

        return WalletResponse.from_orm(wallet)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get wallet",
            user_id=current_user.id,
            wallet_id=wallet_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get wallet"
        )


@router.post("/validate-address", response_model=AddressValidationResponse)
async def validate_address(
    validation_data: AddressValidationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        is_valid = await wallet_service._validate_address(
            address=validation_data.address,
            currency=validation_data.currency,
            network=validation_data.network
        )

        return AddressValidationResponse(
            is_valid=is_valid,
            address=validation_data.address,
            currency=validation_data.currency,
            network=validation_data.network
        )

    except Exception as e:
        logger.error(
            "Failed to validate address",
            user_id=current_user.id,
            address=validation_data.address,
            currency=validation_data.currency,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate address"
        )


@router.post("/estimate-fee", response_model=FeeEstimateResponse)
async def estimate_fee(
    fee_data: FeeEstimateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        fee = await wallet_service._calculate_fee(
            currency=fee_data.currency,
            amount=fee_data.amount,
            network=fee_data.network
        )

        return FeeEstimateResponse(
            currency=fee_data.currency,
            network=fee_data.network,
            fee=fee,
            fee_currency=fee_data.currency,
            priority=fee_data.priority,
            estimated_time="5-10 minutes"
        )

    except Exception as e:
        logger.error(
            "Failed to estimate fee",
            user_id=current_user.id,
            currency=fee_data.currency,
            amount=fee_data.amount,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to estimate fee"
        )


@router.get("/currencies/supported", response_model=SupportedCurrenciesResponse)
async def get_supported_currencies():
    currencies = [
        {
            "code": "BTC",
            "name": "Bitcoin",
            "decimals": 8,
            "networks": ["bitcoin"],
            "min_withdrawal": "0.001"
        },
        {
            "code": "ETH",
            "name": "Ethereum",
            "decimals": 18,
            "networks": ["ethereum"],
            "min_withdrawal": "0.01"
        },
        {
            "code": "USDT",
            "name": "Tether USD",
            "decimals": 6,
            "networks": ["ethereum", "tron", "bsc"],
            "min_withdrawal": "1.0"
        },
        {
            "code": "LTC",
            "name": "Litecoin",
            "decimals": 8,
            "networks": ["litecoin"],
            "min_withdrawal": "0.01"
        },
        {
            "code": "BNB",
            "name": "Binance Coin",
            "decimals": 18,
            "networks": ["bsc"],
            "min_withdrawal": "0.01"
        },
        {
            "code": "TRX",
            "name": "TRON",
            "decimals": 6,
            "networks": ["tron"],
            "min_withdrawal": "10.0"
        },
        {
            "code": "TON",
            "name": "The Open Network",
            "decimals": 9,
            "networks": ["ton"],
            "min_withdrawal": "0.1"
        }
    ]

    return SupportedCurrenciesResponse(currencies=currencies)


@router.get("/getBalance")
async def get_balance_legacy(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        balances = await wallet_service.get_user_balance(
            db=db,
            user_id=current_user.id
        )

        result = []
        for currency, balance_data in balances.items():
            result.append({
                "currency_code": currency,
                "available": balance_data["available"],
                "onhold": balance_data["frozen"]
            })

        return {
            "ok": True,
            "result": result,
            "error": None
        }

    except Exception as e:
        logger.error(
            "Failed to get balance (legacy)",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        return {
            "ok": False,
            "result": None,
            "error": {
                "code": "INTERNAL_ERROR",
                "name": "Internal Server Error"
            }
        }
