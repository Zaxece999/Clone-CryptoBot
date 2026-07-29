from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import structlog

from app.database import get_db
from app.services.auth import get_current_user, auth_service
from app.services.check import check_service
from app.models.user import User
from app.models.check import CheckStatus, CheckType
from app.schemas.check import (
    CheckCreateRequest,
    CheckActivateRequest,
    CheckResponse,
    CheckListResponse,
    CheckActivationResponse,
    CheckActivationListResponse,
    CheckStatsResponse,
    CheckHistoryRequest,
    CheckInfoResponse,
    CheckUrlResponse,
    CheckValidationResponse,
    CheckErrorResponse,
    LegacyCheckCreateRequest,
    LegacyCheckResponse,
    CheckBulkCreateRequest,
    CheckBulkCreateResponse
)
from app.utils.exceptions import (
    CheckError,
    InsufficientFundsError,
    ValidationError,
    NotFoundError,
    PermissionError
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/check", tags=["check"])


@router.post("/create", response_model=CheckResponse)
async def create_check(
    check_data: CheckCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        target_user_id = None
        if check_data.target_username:
            target_user = await auth_service.get_user_by_username(db, check_data.target_username)
            if not target_user:
                raise ValidationError(f"User @{check_data.target_username} not found")
            target_user_id = target_user.id

        check = await check_service.create_check(
            db=db,
            creator=current_user,
            currency=check_data.currency,
            amount=check_data.amount,
            check_type=check_data.type,
            password=check_data.password,
            target_user_id=target_user_id,
            max_activations=check_data.max_activations,
            expires_in_hours=check_data.expires_in_hours,
            description=check_data.description,
            comment=check_data.comment
        )

        check_response = CheckResponse.from_orm(check)
        check_response.is_active = check.is_active
        check_response.is_expired = check.is_expired
        check_response.expiry_info = check.get_expiry_info()

        return check_response

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
    except CheckError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to create check",
            user_id=current_user.id,
            currency=check_data.currency,
            amount=check_data.amount,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create check"
        )


@router.post("/activate", response_model=CheckActivationResponse)
async def activate_check(
    activation_data: CheckActivateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        activation = await check_service.activate_check(
            db=db,
            check_id=activation_data.check_id,
            activator=current_user,
            password=activation_data.password,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return CheckActivationResponse.from_orm(activation)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except CheckError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to activate check",
            user_id=current_user.id,
            check_id=activation_data.check_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate check"
        )


@router.delete("/{check_id}", response_model=CheckResponse)
async def cancel_check(
    check_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        check = await check_service.cancel_check(
            db=db,
            check_id=check_id,
            user=current_user
        )

        check_response = CheckResponse.from_orm(check)
        check_response.is_active = check.is_active
        check_response.is_expired = check.is_expired
        check_response.expiry_info = check.get_expiry_info()

        return check_response

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
    except CheckError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to cancel check",
            user_id=current_user.id,
            check_id=check_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel check"
        )


@router.get("/", response_model=CheckListResponse)
async def get_checks(
    status: Optional[CheckStatus] = Query(None, description="Фильтр по статусу"),
    check_type: Optional[CheckType] = Query(None, description="Фильтр по типу"),
    currency: Optional[str] = Query(None, description="Фильтр по валюте"),
    limit: int = Query(50, ge=1, le=100, description="Количество записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        checks = await check_service.get_user_checks(
            db=db,
            user_id=current_user.id,
            status=status,
            check_type=check_type,
            currency=currency,
            limit=limit,
            offset=offset
        )

        check_responses = []
        for check in checks:
            check_response = CheckResponse.from_orm(check)
            check_response.is_active = check.is_active
            check_response.is_expired = check.is_expired
            check_response.expiry_info = check.get_expiry_info()
            check_responses.append(check_response)

        has_more = len(checks) == limit

        return CheckListResponse(
            checks=check_responses,
            total=len(checks),
            has_more=has_more
        )

    except Exception as e:
        logger.error(
            "Failed to get checks",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get checks"
        )


@router.get("/activations", response_model=CheckActivationListResponse)
async def get_activations(
    limit: int = Query(50, ge=1, le=100, description="Количество записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        activations = await check_service.get_user_activations(
            db=db,
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )

        has_more = len(activations) == limit

        return CheckActivationListResponse(
            activations=[CheckActivationResponse.from_orm(activation) for activation in activations],
            total=len(activations),
            has_more=has_more
        )

    except Exception as e:
        logger.error(
            "Failed to get activations",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get activations"
        )


@router.get("/stats", response_model=CheckStatsResponse)
async def get_check_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        stats = await check_service.get_check_stats(db, current_user.id)
        return CheckStatsResponse(**stats)

    except Exception as e:
        logger.error(
            "Failed to get check stats",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get check stats"
        )


@router.post("/createCheck", response_model=LegacyCheckResponse)
async def create_check_legacy(
    check_data: LegacyCheckCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        check_type = CheckType.ONE_TIME
        target_user_id = None

        if check_data.pin_to_user_id:
            check_type = CheckType.PERSONAL
            target_user_id = check_data.pin_to_user_id
        elif check_data.pin_to_username:
            check_type = CheckType.PERSONAL
            target_user = await auth_service.get_user_by_username(db, check_data.pin_to_username)
            if target_user:
                target_user_id = target_user.id

        check = await check_service.create_check(
            db=db,
            creator=current_user,
            currency=check_data.asset,
            amount=check_data.amount,
            check_type=check_type,
            target_user_id=target_user_id
        )

        bot_username = "CryptoBotClone_bot"
        bot_check_url = f"https://t.me/{bot_username}?start=check_{check.check_id}"

        return LegacyCheckResponse(
            ok=True,
            result={
                "check_id": check.check_id,
                "hash": check.id,
                "bot_check_url": bot_check_url
            }
        )

    except Exception as e:
        logger.error(
            "Failed to create check (legacy)",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        return LegacyCheckResponse(
            ok=False,
            result={},
            error={
                "code": "INTERNAL_ERROR",
                "name": "Internal Server Error"
            }
        )


@router.post("/deleteCheck", response_model=LegacyCheckResponse)
async def delete_check_legacy(
    check_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        await check_service.cancel_check(
            db=db,
            check_id=check_id,
            user=current_user
        )

        return LegacyCheckResponse(
            ok=True,
            result=True
        )

    except Exception as e:
        logger.error(
            "Failed to delete check (legacy)",
            user_id=current_user.id,
            check_id=check_id,
            error=str(e),
            exc_info=True
        )
        return LegacyCheckResponse(
            ok=False,
            result=False,
            error={
                "code": "INTERNAL_ERROR",
                "name": "Internal Server Error"
            }
        )


@router.get("/getChecks", response_model=LegacyCheckResponse)
async def get_checks_legacy(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        checks = await check_service.get_user_checks(
            db=db,
            user_id=current_user.id,
            limit=100
        )

        bot_username = "CryptoBotClone_bot"
        items = []

        for check in checks:
            items.append({
                "check_id": check.check_id,
                "hash": check.id,
                "asset": check.currency,
                "amount": check.amount,
                "bot_check_url": f"https://t.me/{bot_username}?start=check_{check.check_id}",
                "status": check.status,
                "date": int(check.created_at.timestamp()),
                "pin_to_user_id": check.target_user_id,
                "pin_to_username": None
            })

        return LegacyCheckResponse(
            ok=True,
            result={"items": items}
        )

    except Exception as e:
        logger.error(
            "Failed to get checks (legacy)",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        return LegacyCheckResponse(
            ok=False,
            result={"items": []},
            error={
                "code": "INTERNAL_ERROR",
                "name": "Internal Server Error"
            }
        )
