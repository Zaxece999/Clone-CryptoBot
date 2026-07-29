from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.user import User
from app.models.blockchain import BlockchainNetwork, TransactionStatus
from app.services.blockchain import blockchain_service
from app.services.user import user_service
from app.api.auth import get_current_user
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class DepositAddressResponse(BaseModel):
    currency: str
    network: str
    address: str
    memo: Optional[str] = None
    qr_code_url: Optional[str] = None

    class Config:
        from_attributes = True


class WithdrawalRequest(BaseModel):
    currency: str = Field(..., description="Валюта")
    network: str = Field(..., description="Блокчейн сеть")
    to_address: str = Field(..., description="Адрес получателя")
    amount: Decimal = Field(..., gt=0, description="Сумма")
    memo: Optional[str] = Field(None, description="Memo (если требуется)")


class WithdrawalResponse(BaseModel):
    id: int
    currency: str
    network: str
    amount: Decimal
    fee: Decimal
    to_address: str
    status: str
    tx_hash: Optional[str] = None
    requires_approval: bool
    created_at: str

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    id: int
    tx_hash: str
    network: str
    currency: str
    from_address: str
    to_address: str
    amount: Decimal
    fee: Optional[Decimal]
    status: str
    confirmations: int
    required_confirmations: int
    block_number: Optional[int]
    created_at: str
    confirmed_at: Optional[str]

    class Config:
        from_attributes = True


class NetworkInfoResponse(BaseModel):
    network: str
    name: str
    is_active: bool
    min_confirmations: int
    estimated_block_time: int
    current_block: Optional[int]


@router.get("/deposit/address/{currency}")
async def get_deposit_address(
    currency: str,
    network: str = Query(..., description="Блокчейн сеть"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DepositAddressResponse:
    try:
        try:
            blockchain_network = BlockchainNetwork(network.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail="Неподдерживаемая сеть")

        deposit_address = await blockchain_service.get_user_deposit_address(
            db, current_user.id, currency.upper(), blockchain_network
        )

        if not deposit_address:
            deposit_address = await blockchain_service.create_deposit_address(
                db, current_user, currency.upper(), blockchain_network
            )

        qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={deposit_address.address}"

        return DepositAddressResponse(
            currency=deposit_address.currency,
            network=deposit_address.network.value,
            address=deposit_address.address,
            memo=deposit_address.memo,
            qr_code_url=qr_code_url
        )

    except Exception as e:
        logger.error("❌ Не удалось получить адрес депозита", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Не удалось получить адрес")


@router.get("/deposit/addresses")
async def get_user_deposit_addresses(
    network: Optional[str] = Query(None, description="Фильтр по сети"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[DepositAddressResponse]:
    try:
        blockchain_network = None
        if network:
            try:
                blockchain_network = BlockchainNetwork(network.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail="Неподдерживаемая сеть")

        addresses = await blockchain_service.get_user_addresses(
            db, current_user.id, blockchain_network
        )

        return [
            DepositAddressResponse(
                currency=addr.currency,
                network=addr.network.value,
                address=addr.address,
                memo=addr.memo,
                qr_code_url=f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={addr.address}"
            )
            for addr in addresses
        ]

    except Exception as e:
        logger.error("❌ Не удалось получить адреса депозита", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Не удалось получить адреса")


@router.post("/withdrawal/create")
async def create_withdrawal(
    request: WithdrawalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> WithdrawalResponse:
    try:
        try:
            blockchain_network = BlockchainNetwork(request.network.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail="Неподдерживаемая сеть")

        withdrawal = await blockchain_service.create_withdrawal_request(
            db=db,
            user=current_user,
            currency=request.currency.upper(),
            network=blockchain_network,
            to_address=request.to_address,
            amount=request.amount,
            memo=request.memo
        )

        return WithdrawalResponse(
            id=withdrawal.id,
            currency=withdrawal.currency,
            network=withdrawal.network.value,
            amount=withdrawal.amount,
            fee=withdrawal.fee,
            to_address=withdrawal.to_address,
            status=withdrawal.status.value,
            tx_hash=withdrawal.tx_hash,
            requires_approval=withdrawal.requires_approval,
            created_at=withdrawal.created_at.isoformat()
        )

    except Exception as e:
        logger.error("❌ Не удалось создать вывод", error=str(e), exc_info=True)
        if "недостаточно" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail="Не удалось создать запрос на вывод")


@router.get("/withdrawal/history")
async def get_withdrawal_history(
    limit: int = Query(50, le=100, description="Количество записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[WithdrawalResponse]:
    try:
        return []

    except Exception as e:
        logger.error("❌ Не удалось получить историю выводов", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Не удалось получить историю")


@router.get("/withdrawal/{withdrawal_id}")
async def get_withdrawal_details(
    withdrawal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> WithdrawalResponse:
    try:
        raise HTTPException(status_code=404, detail="Запрос не найден")

    except Exception as e:
        logger.error("❌ Не удалось получить детали вывода", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Не удалось получить детали")


@router.get("/transactions")
async def get_transactions(
    limit: int = Query(50, le=100, description="Количество записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    currency: Optional[str] = Query(None, description="Фильтр по валюте"),
    network: Optional[str] = Query(None, description="Фильтр по сети"),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[TransactionResponse]:
    try:
        return []

    except Exception as e:
        logger.error("❌ Не удалось получить транзакции", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Не удалось получить транзакции")


@router.get("/transaction/{tx_hash}")
async def get_transaction_details(
    tx_hash: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TransactionResponse:
    try:
        raise HTTPException(status_code=404, detail="Транзакция не найдена")

    except Exception as e:
        logger.error("❌ Не удалось получить детали транзакции", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Не удалось получить детали")


@router.get("/networks")
async def get_supported_networks() -> List[NetworkInfoResponse]:
    try:
        networks = [
            NetworkInfoResponse(
                network="bitcoin",
                name="Bitcoin",
                is_active=True,
                min_confirmations=1,
                estimated_block_time=600,
                current_block=None
            ),
            NetworkInfoResponse(
                network="ethereum",
                name="Ethereum",
                is_active=True,
                min_confirmations=12,
                estimated_block_time=15,
                current_block=None
            ),
            NetworkInfoResponse(
                network="bsc",
                name="Binance Smart Chain",
                is_active=True,
                min_confirmations=15,
                estimated_block_time=3,
                current_block=None
            ),
            NetworkInfoResponse(
                network="tron",
                name="TRON",
                is_active=True,
                min_confirmations=19,
                estimated_block_time=3,
                current_block=None
            ),
            NetworkInfoResponse(
                network="polygon",
                name="Polygon",
                is_active=True,
                min_confirmations=128,
                estimated_block_time=2,
                current_block=None
            )
        ]

        return networks

    except Exception as e:
        logger.error("❌ Не удалось получить список сетей", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Не удалось получить список сетей")


@router.get("/network/{network}/info")
async def get_network_info(
    network: str,
    db: AsyncSession = Depends(get_db)
) -> NetworkInfoResponse:
    try:
        try:
            blockchain_network = BlockchainNetwork(network.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail="Неподдерживаемая сеть")

        network_info = {
            BlockchainNetwork.BITCOIN: {
                "name": "Bitcoin",
                "min_confirmations": 1,
                "estimated_block_time": 600
            },
            BlockchainNetwork.ETHEREUM: {
                "name": "Ethereum",
                "min_confirmations": 12,
                "estimated_block_time": 15
            },
            BlockchainNetwork.BINANCE_SMART_CHAIN: {
                "name": "Binance Smart Chain",
                "min_confirmations": 15,
                "estimated_block_time": 3
            },
            BlockchainNetwork.TRON: {
                "name": "TRON",
                "min_confirmations": 19,
                "estimated_block_time": 3
            },
            BlockchainNetwork.POLYGON: {
                "name": "Polygon",
                "min_confirmations": 128,
                "estimated_block_time": 2
            }
        }.get(blockchain_network, {
            "name": network.title(),
            "min_confirmations": 12,
            "estimated_block_time": 15
        })

        return NetworkInfoResponse(
            network=blockchain_network.value,
            name=network_info["name"],
            is_active=True,
            min_confirmations=network_info["min_confirmations"],
            estimated_block_time=network_info["estimated_block_time"],
            current_block=None
        )

    except Exception as e:
        logger.error("❌ Не удалось получить информацию о сети", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Не удалось получить информацию о сети")


@router.post("/validate/address")
async def validate_address(
    network: str,
    address: str,
    db: AsyncSession = Depends(get_db)
) -> dict:
    try:
        try:
            blockchain_network = BlockchainNetwork(network.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail="Неподдерживаемая сеть")

        is_valid = len(address) > 10

        return {
            "network": blockchain_network.value,
            "address": address,
            "is_valid": is_valid,
            "address_type": "unknown"
        }

    except Exception as e:
        logger.error("❌ Не удалось валидировать адрес", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Не удалось валидировать адрес")


@router.get("/fees/{network}")
async def get_network_fees(
    network: str,
    currency: Optional[str] = Query(None, description="Валюта"),
    db: AsyncSession = Depends(get_db)
) -> dict:
    try:
        try:
            blockchain_network = BlockchainNetwork(network.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail="Неподдерживаемая сеть")

        fees = {
            BlockchainNetwork.BITCOIN: {
                "withdrawal_fee": "0.0005",
                "min_withdrawal": "0.001",
                "network_fee_estimate": "0.0003"
            },
            BlockchainNetwork.ETHEREUM: {
                "withdrawal_fee": "0.005",
                "min_withdrawal": "0.01",
                "network_fee_estimate": "0.003"
            },
            BlockchainNetwork.TRON: {
                "withdrawal_fee": "1.0",
                "min_withdrawal": "10.0",
                "network_fee_estimate": "0.0"
            }
        }.get(blockchain_network, {
            "withdrawal_fee": "0.001",
            "min_withdrawal": "0.01",
            "network_fee_estimate": "0.001"
        })

        return {
            "network": blockchain_network.value,
            "currency": currency or "native",
            **fees
        }

    except Exception as e:
        logger.error("❌ Не удалось получить информацию о комиссиях", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Не удалось получить информацию о комиссиях")
