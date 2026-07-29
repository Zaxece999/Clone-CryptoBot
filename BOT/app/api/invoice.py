from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import structlog

from app.database import get_db
from app.services.auth import get_current_user
from app.services.invoice import invoice_service
from app.models.user import User
from app.models.invoice import InvoiceStatus, InvoiceType
from app.schemas.invoice import (
    InvoiceCreateRequest,
    InvoicePayRequest,
    InvoiceResponse,
    InvoiceListResponse,
    InvoicePaymentResponse,
    InvoicePaymentListResponse,
    InvoiceStatsResponse,
    InvoiceHistoryRequest,
    InvoiceInfoResponse,
    InvoiceUrlResponse,
    InvoiceValidationResponse,
    InvoiceErrorResponse,
    LegacyInvoiceCreateRequest,
    LegacyInvoiceResponse
)
from app.utils.exceptions import (
    InvoiceError,
    InsufficientFundsError,
    ValidationError,
    NotFoundError,
    PermissionError
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/invoice", tags=["invoice"])


@router.post("/create", response_model=InvoiceResponse)
async def create_invoice(
    invoice_data: InvoiceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        invoice = await invoice_service.create_invoice(
            db=db,
            creator=current_user,
            currency=invoice_data.currency,
            amount=invoice_data.amount,
            description=invoice_data.description,
            payload=invoice_data.payload,
            expires_in_hours=invoice_data.expires_in_hours,
            return_url=str(invoice_data.return_url) if invoice_data.return_url else None,
            success_url=str(invoice_data.success_url) if invoice_data.success_url else None,
            cancel_url=str(invoice_data.cancel_url) if invoice_data.cancel_url else None,
            webhook_url=str(invoice_data.webhook_url) if invoice_data.webhook_url else None,
            notify_on_payment=invoice_data.notify_on_payment,
            invoice_type=invoice_data.type,
            recurring_interval_days=invoice_data.recurring_interval_days,
            recurring_count=invoice_data.recurring_count
        )

        invoice_response = InvoiceResponse.from_orm(invoice)
        invoice_response.is_active = invoice.is_active
        invoice_response.is_expired = invoice.is_expired
        invoice_response.can_be_paid = invoice.can_be_paid
        invoice_response.expiry_info = invoice.get_expiry_info()
        invoice_response.payment_url = invoice.get_payment_url("CryptoBotClone_bot")

        return invoice_response

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except InvoiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to create invoice",
            user_id=current_user.id,
            currency=invoice_data.currency,
            amount=invoice_data.amount,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invoice"
        )


@router.post("/pay", response_model=InvoicePaymentResponse)
async def pay_invoice(
    payment_data: InvoicePayRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        payment = await invoice_service.pay_invoice(
            db=db,
            invoice_id=payment_data.invoice_id,
            payer=current_user,
            payment_method="wallet",
            payment_source="api",
            ip_address=ip_address,
            user_agent=user_agent
        )

        return InvoicePaymentResponse.from_orm(payment)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InsufficientFundsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    except InvoiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to pay invoice",
            user_id=current_user.id,
            invoice_id=payment_data.invoice_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pay invoice"
        )


@router.delete("/{invoice_id}", response_model=InvoiceResponse)
async def cancel_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        invoice = await invoice_service.cancel_invoice(
            db=db,
            invoice_id=invoice_id,
            user=current_user
        )

        invoice_response = InvoiceResponse.from_orm(invoice)
        invoice_response.is_active = invoice.is_active
        invoice_response.is_expired = invoice.is_expired
        invoice_response.can_be_paid = invoice.can_be_paid
        invoice_response.expiry_info = invoice.get_expiry_info()
        invoice_response.payment_url = invoice.get_payment_url("CryptoBotClone_bot")

        return invoice_response

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
    except InvoiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to cancel invoice",
            user_id=current_user.id,
            invoice_id=invoice_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel invoice"
        )


@router.get("/", response_model=InvoiceListResponse)
async def get_invoices(
    status: Optional[InvoiceStatus] = Query(None, description="Фильтр по статусу"),
    invoice_type: Optional[InvoiceType] = Query(None, description="Фильтр по типу"),
    currency: Optional[str] = Query(None, description="Фильтр по валюте"),
    limit: int = Query(50, ge=1, le=100, description="Количество записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        invoices = await invoice_service.get_user_invoices(
            db=db,
            user_id=current_user.id,
            status=status,
            invoice_type=invoice_type,
            currency=currency,
            limit=limit,
            offset=offset
        )

        invoice_responses = []
        for invoice in invoices:
            invoice_response = InvoiceResponse.from_orm(invoice)
            invoice_response.is_active = invoice.is_active
            invoice_response.is_expired = invoice.is_expired
            invoice_response.can_be_paid = invoice.can_be_paid
            invoice_response.expiry_info = invoice.get_expiry_info()
            invoice_response.payment_url = invoice.get_payment_url("CryptoBotClone_bot")
            invoice_responses.append(invoice_response)

        has_more = len(invoices) == limit

        return InvoiceListResponse(
            invoices=invoice_responses,
            total=len(invoices),
            has_more=has_more
        )

    except Exception as e:
        logger.error(
            "Failed to get invoices",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get invoices"
        )


@router.get("/payments", response_model=InvoicePaymentListResponse)
async def get_payments(
    limit: int = Query(50, ge=1, le=100, description="Количество записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        payments = await invoice_service.get_user_payments(
            db=db,
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )

        has_more = len(payments) == limit

        return InvoicePaymentListResponse(
            payments=[InvoicePaymentResponse.from_orm(payment) for payment in payments],
            total=len(payments),
            has_more=has_more
        )

    except Exception as e:
        logger.error(
            "Failed to get payments",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get payments"
        )


@router.get("/stats", response_model=InvoiceStatsResponse)
async def get_invoice_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        stats = await invoice_service.get_invoice_stats(db, current_user.id)
        return InvoiceStatsResponse(**stats)

    except Exception as e:
        logger.error(
            "Failed to get invoice stats",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get invoice stats"
        )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        invoice = await invoice_service.get_invoice_by_id(db, invoice_id, include_payments=True)

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )

        if invoice.creator_id != current_user.id:
            return InvoiceInfoResponse(
                invoice_id=invoice.invoice_id,
                currency=invoice.currency,
                amount=invoice.amount,
                type=InvoiceType(invoice.type),
                status=InvoiceStatus(invoice.status),
                description=invoice.description,
                expires_at=invoice.expires_at,
                is_active=invoice.is_active,
                is_expired=invoice.is_expired,
                expiry_info=invoice.get_expiry_info(),
                created_at=invoice.created_at,
                payment_url=invoice.get_payment_url("CryptoBotClone_bot")
            )

        invoice_response = InvoiceResponse.from_orm(invoice)
        invoice_response.is_active = invoice.is_active
        invoice_response.is_expired = invoice.is_expired
        invoice_response.can_be_paid = invoice.can_be_paid
        invoice_response.expiry_info = invoice.get_expiry_info()
        invoice_response.payment_url = invoice.get_payment_url("CryptoBotClone_bot")

        return invoice_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get invoice",
            user_id=current_user.id,
            invoice_id=invoice_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get invoice"
        )


@router.post("/createInvoice", response_model=LegacyInvoiceResponse)
async def create_invoice_legacy(
    invoice_data: LegacyInvoiceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        invoice = await invoice_service.create_invoice(
            db=db,
            creator=current_user,
            currency=invoice_data.asset,
            amount=invoice_data.amount,
            description=invoice_data.description,
            payload=invoice_data.payload
        )

        bot_username = "CryptoBotClone_bot"
        bot_invoice_url = f"https://t.me/{bot_username}?start=invoice_{invoice.invoice_id}"
        mini_app_url = f"https://t.me/{bot_username}/app?startapp=invoice_{invoice.invoice_id}"

        return LegacyInvoiceResponse(
            ok=True,
            result={
                "invoice_id": invoice.invoice_id,
                "hash": invoice.id,
                "bot_invoice_url": bot_invoice_url,
                "mini_app_invoice_url": mini_app_url,
                "web_app_invoice_url": bot_invoice_url
            }
        )

    except Exception as e:
        logger.error(
            "Failed to create invoice (legacy)",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        return LegacyInvoiceResponse(
            ok=False,
            result={},
            error={
                "code": "INTERNAL_ERROR",
                "name": "Internal Server Error"
            }
        )


@router.get("/getInvoices", response_model=LegacyInvoiceResponse)
async def get_invoices_legacy(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        invoices = await invoice_service.get_user_invoices(
            db=db,
            user_id=current_user.id,
            limit=100
        )

        bot_username = "CryptoBotClone_bot"
        items = []

        for invoice in invoices:
            items.append({
                "invoice_id": invoice.invoice_id,
                "hash": invoice.id,
                "asset": invoice.currency,
                "amount": invoice.amount,
                "description": invoice.description,
                "status": invoice.status,
                "created_at": invoice.created_at.isoformat(),
                "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
                "bot_invoice_url": f"https://t.me/{bot_username}?start=invoice_{invoice.invoice_id}"
            })

        return LegacyInvoiceResponse(
            ok=True,
            result={"items": items}
        )

    except Exception as e:
        logger.error(
            "Failed to get invoices (legacy)",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        return LegacyInvoiceResponse(
            ok=False,
            result={"items": []},
            error={
                "code": "INTERNAL_ERROR",
                "name": "Internal Server Error"
            }
        )
