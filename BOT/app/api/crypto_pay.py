from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from decimal import Decimal
import structlog

from app.database import get_db
from app.middleware.api_auth import get_current_api_key, require_api_scope
from app.models.api import ApiKey, ApiKeyScope
from app.services.wallet import wallet_service
from app.services.check import check_service
from app.services.invoice import invoice_service
from app.services.exchange import exchange_service
from app.services.user import user_service
from app.utils.exceptions import ValidationError, NotFoundError, InsufficientFundsError

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/crypto-pay/api", tags=["crypto-pay"])


class CryptoPayResponse(Dict[str, Any]):
    def __init__(self, ok: bool = True, result: Any = None, error: Optional[Dict] = None):
        super().__init__()
        self["ok"] = ok
        if result is not None:
            self["result"] = result
        if error is not None:
            self["error"] = error


@router.get("/getMe")
@require_api_scope(ApiKeyScope.READ)
async def get_me(
    request: Request,
    api_key: ApiKey = Depends(get_current_api_key)
):
    try:
        app_info = {
            "app_id": api_key.application.app_id,
            "name": api_key.application.name,
            "payment_processing_bot_username": "CryptoBotClone_bot",
            "supported_assets": [
                "BTC", "ETH", "USDT", "LTC", "BNB", "TRX", "TON"
            ]
        }

        return CryptoPayResponse(result=app_info)

    except Exception as e:
        logger.error("Failed to get app info", error=str(e), exc_info=True)
        return CryptoPayResponse(
            ok=False,
            error={"code": "INTERNAL_ERROR", "name": "InternalError"}
        )


@router.get("/getBalance")
@require_api_scope(ApiKeyScope.WALLET_READ)
async def get_balance(
    request: Request,
    api_key: ApiKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db)
):
    try:
        user = await user_service.get_user_by_id(db, api_key.user_id)
        if not user:
            return CryptoPayResponse(
                ok=False,
                error={"code": "USER_NOT_FOUND", "name": "UserNotFound"}
            )

        wallets = await wallet_service.get_user_wallets(db, user.id)

        balances = []
        for wallet in wallets:
            if wallet.balance > 0:
                balances.append({
                    "currency_code": wallet.currency,
                    "available": str(wallet.balance),
                    "on_hold": str(wallet.frozen_balance)
                })

        return CryptoPayResponse(result=balances)

    except Exception as e:
        logger.error("Failed to get balance", error=str(e), exc_info=True)
        return CryptoPayResponse(
            ok=False,
            error={"code": "INTERNAL_ERROR", "name": "InternalError"}
        )


@router.get("/getExchangeRates")
async def get_exchange_rates(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        pairs = await exchange_service.get_supported_pairs(db)

        rates = []
        for pair in pairs:
            rates.append({
                "source": pair["from_currency"],
                "target": pair["to_currency"],
                "rate": pair["rate"]
            })

        return CryptoPayResponse(result=rates)

    except Exception as e:
        logger.error("Failed to get exchange rates", error=str(e), exc_info=True)
        return CryptoPayResponse(
            ok=False,
            error={"code": "INTERNAL_ERROR", "name": "InternalError"}
        )


@router.get("/getCurrencies")
async def get_currencies(request: Request):
    try:
        currencies = [
            {
                "code": "BTC",
                "name": "Bitcoin",
                "is_blockchain": True,
                "is_stablecoin": False,
                "url_code": "BTC",
                "decimals": 8
            },
            {
                "code": "ETH",
                "name": "Ethereum",
                "is_blockchain": True,
                "is_stablecoin": False,
                "url_code": "ETH",
                "decimals": 8
            },
            {
                "code": "USDT",
                "name": "Tether USD",
                "is_blockchain": True,
                "is_stablecoin": True,
                "url_code": "USDT",
                "decimals": 6
            },
            {
                "code": "LTC",
                "name": "Litecoin",
                "is_blockchain": True,
                "is_stablecoin": False,
                "url_code": "LTC",
                "decimals": 8
            },
            {
                "code": "BNB",
                "name": "Binance Coin",
                "is_blockchain": True,
                "is_stablecoin": False,
                "url_code": "BNB",
                "decimals": 8
            },
            {
                "code": "TRX",
                "name": "TRON",
                "is_blockchain": True,
                "is_stablecoin": False,
                "url_code": "TRX",
                "decimals": 6
            },
            {
                "code": "TON",
                "name": "The Open Network",
                "is_blockchain": True,
                "is_stablecoin": False,
                "url_code": "TON",
                "decimals": 9
            }
        ]

        return CryptoPayResponse(result=currencies)

    except Exception as e:
        logger.error("Failed to get currencies", error=str(e), exc_info=True)
        return CryptoPayResponse(
            ok=False,
            error={"code": "INTERNAL_ERROR", "name": "InternalError"}
        )


@router.post("/createInvoice")
@require_api_scope(ApiKeyScope.INVOICE_WRITE)
async def create_invoice(
    request: Request,
    api_key: ApiKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db)
):
    try:
        body = await request.json()

        if "asset" not in body:
            return CryptoPayResponse(
                ok=False,
                error={"code": "ASSET_REQUIRED", "name": "AssetRequired"}
            )

        if "amount" not in body:
            return CryptoPayResponse(
                ok=False,
                error={"code": "AMOUNT_REQUIRED", "name": "AmountRequired"}
            )

        user = await user_service.get_user_by_id(db, api_key.user_id)
        if not user:
            return CryptoPayResponse(
                ok=False,
                error={"code": "USER_NOT_FOUND", "name": "UserNotFound"}
            )

        invoice = await invoice_service.create_invoice(
            db=db,
            user=user,
            amount=Decimal(str(body["amount"])),
            currency=body["asset"],
            description=body.get("description"),
            expires_in_hours=body.get("expires_in", 24),
            payload=body.get("payload")
        )

        result = {
            "invoice_id": invoice.invoice_id,
            "status": invoice.status,
            "hash": invoice.invoice_id,
            "asset": invoice.currency,
            "amount": str(invoice.amount),
            "pay_url": invoice.invoice_url,
            "description": invoice.description,
            "created_at": invoice.created_at.isoformat(),
            "allow_comments": True,
            "allow_anonymous": True,
            "expiration_date": invoice.expires_at.isoformat() if invoice.expires_at else None,
            "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
            "paid_anonymously": False,
            "payload": invoice.payload
        }

        return CryptoPayResponse(result=result)

    except ValidationError as e:
        return CryptoPayResponse(
            ok=False,
            error={"code": "VALIDATION_ERROR", "name": "ValidationError", "message": str(e)}
        )
    except Exception as e:
        logger.error("Failed to create invoice", error=str(e), exc_info=True)
        return CryptoPayResponse(
            ok=False,
            error={"code": "INTERNAL_ERROR", "name": "InternalError"}
        )


@router.get("/getInvoices")
@require_api_scope(ApiKeyScope.INVOICE_READ)
async def get_invoices(
    request: Request,
    api_key: ApiKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db)
):
    try:
        asset = request.query_params.get("asset")
        invoice_ids = request.query_params.get("invoice_ids")
        status = request.query_params.get("status")
        offset = int(request.query_params.get("offset", 0))
        count = min(int(request.query_params.get("count", 100)), 1000)

        user = await user_service.get_user_by_id(db, api_key.user_id)
        if not user:
            return CryptoPayResponse(
                ok=False,
                error={"code": "USER_NOT_FOUND", "name": "UserNotFound"}
            )

        invoices = await invoice_service.get_user_invoices(
            db=db,
            user_id=user.id,
            currency=asset,
            status=status,
            limit=count,
            offset=offset
        )

        items = []
        for invoice in invoices:
            items.append({
                "invoice_id": invoice.invoice_id,
                "status": invoice.status,
                "hash": invoice.invoice_id,
                "asset": invoice.currency,
                "amount": str(invoice.amount),
                "pay_url": invoice.invoice_url,
                "description": invoice.description,
                "created_at": invoice.created_at.isoformat(),
                "allow_comments": True,
                "allow_anonymous": True,
                "expiration_date": invoice.expires_at.isoformat() if invoice.expires_at else None,
                "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
                "paid_anonymously": False,
                "payload": invoice.payload
            })

        result = {
            "items": items,
            "count": len(items)
        }

        return CryptoPayResponse(result=result)

    except Exception as e:
        logger.error("Failed to get invoices", error=str(e), exc_info=True)
        return CryptoPayResponse(
            ok=False,
            error={"code": "INTERNAL_ERROR", "name": "InternalError"}
        )


@router.post("/createCheck")
@require_api_scope(ApiKeyScope.CHECK_WRITE)
async def create_check(
    request: Request,
    api_key: ApiKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db)
):
    try:
        body = await request.json()

        if "asset" not in body:
            return CryptoPayResponse(
                ok=False,
                error={"code": "ASSET_REQUIRED", "name": "AssetRequired"}
            )

        if "amount" not in body:
            return CryptoPayResponse(
                ok=False,
                error={"code": "AMOUNT_REQUIRED", "name": "AmountRequired"}
            )

        user = await user_service.get_user_by_id(db, api_key.user_id)
        if not user:
            return CryptoPayResponse(
                ok=False,
                error={"code": "USER_NOT_FOUND", "name": "UserNotFound"}
            )

        check = await check_service.create_check(
            db=db,
            user=user,
            amount=Decimal(str(body["amount"])),
            currency=body["asset"],
            description=body.get("description"),
            expires_in_hours=body.get("expires_in", 24)
        )

        result = {
            "check_id": check.check_id,
            "hash": check.check_id,
            "asset": check.currency,
            "amount": str(check.amount),
            "bot_check_url": check.check_url,
            "status": "active" if check.is_active else "activated",
            "created_at": check.created_at.isoformat(),
            "activates_count": check.activations_count,
            "description": check.description
        }

        return CryptoPayResponse(result=result)

    except ValidationError as e:
        return CryptoPayResponse(
            ok=False,
            error={"code": "VALIDATION_ERROR", "name": "ValidationError", "message": str(e)}
        )
    except InsufficientFundsError as e:
        return CryptoPayResponse(
            ok=False,
            error={"code": "INSUFFICIENT_FUNDS", "name": "InsufficientFunds", "message": str(e)}
        )
    except Exception as e:
        logger.error("Failed to create check", error=str(e), exc_info=True)
        return CryptoPayResponse(
            ok=False,
            error={"code": "INTERNAL_ERROR", "name": "InternalError"}
        )


@router.get("/getChecks")
@require_api_scope(ApiKeyScope.CHECK_READ)
async def get_checks(
    request: Request,
    api_key: ApiKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db)
):
    try:
        asset = request.query_params.get("asset")
        check_ids = request.query_params.get("check_ids")
        status = request.query_params.get("status")
        offset = int(request.query_params.get("offset", 0))
        count = min(int(request.query_params.get("count", 100)), 1000)

        user = await user_service.get_user_by_id(db, api_key.user_id)
        if not user:
            return CryptoPayResponse(
                ok=False,
                error={"code": "USER_NOT_FOUND", "name": "UserNotFound"}
            )

        checks = await check_service.get_user_checks(
            db=db,
            user_id=user.id,
            currency=asset,
            limit=count,
            offset=offset
        )

        items = []
        for check in checks:
            items.append({
                "check_id": check.check_id,
                "hash": check.check_id,
                "asset": check.currency,
                "amount": str(check.amount),
                "bot_check_url": check.check_url,
                "status": "active" if check.is_active else "activated",
                "created_at": check.created_at.isoformat(),
                "activates_count": check.activations_count,
                "description": check.description
            })

        result = {
            "items": items,
            "count": len(items)
        }

        return CryptoPayResponse(result=result)

    except Exception as e:
        logger.error("Failed to get checks", error=str(e), exc_info=True)
        return CryptoPayResponse(
            ok=False,
            error={"code": "INTERNAL_ERROR", "name": "InternalError"}
        )


@router.delete("/deleteCheck")
@require_api_scope(ApiKeyScope.CHECK_WRITE)
async def delete_check(
    request: Request,
    api_key: ApiKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db)
):
    try:
        body = await request.json()

        if "check_id" not in body:
            return CryptoPayResponse(
                ok=False,
                error={"code": "CHECK_ID_REQUIRED", "name": "CheckIdRequired"}
            )

        user = await user_service.get_user_by_id(db, api_key.user_id)
        if not user:
            return CryptoPayResponse(
                ok=False,
                error={"code": "USER_NOT_FOUND", "name": "UserNotFound"}
            )

        success = await check_service.delete_check(
            db=db,
            check_id=body["check_id"],
            user=user
        )

        if not success:
            return CryptoPayResponse(
                ok=False,
                error={"code": "CHECK_NOT_FOUND", "name": "CheckNotFound"}
            )

        return CryptoPayResponse(result=True)

    except Exception as e:
        logger.error("Failed to delete check", error=str(e), exc_info=True)
        return CryptoPayResponse(
            ok=False,
            error={"code": "INTERNAL_ERROR", "name": "InternalError"}
        )


@router.post("/transfer")
@require_api_scope(ApiKeyScope.WALLET_WRITE)
async def transfer(
    request: Request,
    api_key: ApiKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db)
):
    try:
        body = await request.json()

        required_fields = ["user_id", "asset", "amount"]
        for field in required_fields:
            if field not in body:
                return CryptoPayResponse(
                    ok=False,
                    error={"code": f"{field.upper()}_REQUIRED", "name": f"{field.title()}Required"}
                )

        user = await user_service.get_user_by_id(db, api_key.user_id)
        if not user:
            return CryptoPayResponse(
                ok=False,
                error={"code": "USER_NOT_FOUND", "name": "UserNotFound"}
            )

        recipient = await user_service.get_user_by_telegram_id(db, body["user_id"])
        if not recipient:
            return CryptoPayResponse(
                ok=False,
                error={"code": "RECIPIENT_NOT_FOUND", "name": "RecipientNotFound"}
            )

        transfer_result = await wallet_service.transfer_funds(
            db=db,
            from_user=user,
            to_user=recipient,
            currency=body["asset"],
            amount=Decimal(str(body["amount"])),
            description=body.get("comment", "API Transfer")
        )

        result = {
            "transfer_id": transfer_result["transaction_id"],
            "user_id": body["user_id"],
            "asset": body["asset"],
            "amount": str(body["amount"]),
            "status": "completed",
            "completed_at": transfer_result["created_at"].isoformat(),
            "comment": body.get("comment")
        }

        return CryptoPayResponse(result=result)

    except ValidationError as e:
        return CryptoPayResponse(
            ok=False,
            error={"code": "VALIDATION_ERROR", "name": "ValidationError", "message": str(e)}
        )
    except InsufficientFundsError as e:
        return CryptoPayResponse(
            ok=False,
            error={"code": "INSUFFICIENT_FUNDS", "name": "InsufficientFunds", "message": str(e)}
        )
    except Exception as e:
        logger.error("Failed to transfer", error=str(e), exc_info=True)
        return CryptoPayResponse(
            ok=False,
            error={"code": "INTERNAL_ERROR", "name": "InternalError"}
        )


@router.get("/getWebhookUpdates")
@require_api_scope(ApiKeyScope.READ)
async def get_webhook_updates(
    request: Request,
    api_key: ApiKey = Depends(get_current_api_key)
):
    try:
        result = {
            "updates": []
        }

        return CryptoPayResponse(result=result)

    except Exception as e:
        logger.error("Failed to get webhook updates", error=str(e), exc_info=True)
        return CryptoPayResponse(
            ok=False,
            error={"code": "INTERNAL_ERROR", "name": "InternalError"}
        )
