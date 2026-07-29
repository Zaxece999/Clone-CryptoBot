from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from decimal import Decimal
import structlog

from app.database import get_db
from app.services.auth import get_current_user
from app.services.subscription import subscription_service
from app.models.user import User
from app.models.subscription import SubscriptionType, BillingPeriod
from app.schemas.subscription import (
    SubscriptionCreateRequest,
    SubscriptionUpdateRequest,
    SubscriptionActivateRequest,
    SubscriptionCancelRequest,
    SubscriptionRenewRequest,
    SubscriptionListRequest,
    SubscriptionInviteCreateRequest,
    SubscriptionInviteUseRequest,
    SubscriptionResponse,
    SubscriptionListResponse,
    SubscriptionPaymentResponse,
    SubscriptionPaymentListResponse,
    SubscriptionInviteResponse,
    SubscriptionStatsResponse,
    SubscriptionSummaryResponse,
    SubscriptionStatusEnum,
    SubscriptionTypeEnum,
    SubscriptionErrorResponse
)
from app.utils.exceptions import (
    ValidationError,
    NotFoundError,
    InsufficientFundsError,
    SubscriptionError
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("/create", response_model=SubscriptionResponse)
async def create_subscription(
    request: SubscriptionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        subscription = await subscription_service.create_subscription(
            db=db,
            user=current_user,
            title=request.title,
            description=request.description,
            subscription_type=SubscriptionType(request.subscription_type.value),
            price=request.price,
            currency=request.currency,
            billing_period=BillingPeriod(request.billing_period.value),
            chat_id=request.chat_id,
            chat_username=request.chat_username,
            chat_title=request.chat_title,
            trial_days=request.trial_days,
            auto_renew=request.auto_renew
        )

        subscription_response = SubscriptionResponse.from_orm(subscription)
        subscription_response.is_active = subscription.is_active
        subscription_response.is_expired = subscription.is_expired
        subscription_response.is_trial = subscription.is_trial
        subscription_response.days_until_expiry = subscription.days_until_expiry
        subscription_response.next_payment_amount = str(subscription.next_payment_amount)

        return subscription_response

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to create subscription",
            user_id=current_user.id,
            title=request.title,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription"
        )


@router.post("/activate", response_model=SubscriptionResponse)
async def activate_subscription(
    request: SubscriptionActivateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        subscription = await subscription_service.activate_subscription(
            db=db,
            subscription_id=request.subscription_id,
            user=current_user
        )

        subscription_response = SubscriptionResponse.from_orm(subscription)
        subscription_response.is_active = subscription.is_active
        subscription_response.is_expired = subscription.is_expired
        subscription_response.is_trial = subscription.is_trial
        subscription_response.days_until_expiry = subscription.days_until_expiry
        subscription_response.next_payment_amount = str(subscription.next_payment_amount)

        return subscription_response

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
            "Failed to activate subscription",
            user_id=current_user.id,
            subscription_id=request.subscription_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate subscription"
        )


@router.post("/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    request: SubscriptionCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        subscription = await subscription_service.cancel_subscription(
            db=db,
            subscription_id=request.subscription_id,
            user=current_user,
            reason=request.reason
        )

        subscription_response = SubscriptionResponse.from_orm(subscription)
        subscription_response.is_active = subscription.is_active
        subscription_response.is_expired = subscription.is_expired
        subscription_response.is_trial = subscription.is_trial
        subscription_response.days_until_expiry = subscription.days_until_expiry
        subscription_response.next_payment_amount = str(subscription.next_payment_amount)

        return subscription_response

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
            "Failed to cancel subscription",
            user_id=current_user.id,
            subscription_id=request.subscription_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription"
        )


@router.post("/renew", response_model=SubscriptionResponse)
async def renew_subscription(
    request: SubscriptionRenewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        subscription = await subscription_service.renew_subscription(
            db=db,
            subscription_id=request.subscription_id,
            user=current_user
        )

        subscription_response = SubscriptionResponse.from_orm(subscription)
        subscription_response.is_active = subscription.is_active
        subscription_response.is_expired = subscription.is_expired
        subscription_response.is_trial = subscription.is_trial
        subscription_response.days_until_expiry = subscription.days_until_expiry
        subscription_response.next_payment_amount = str(subscription.next_payment_amount)

        return subscription_response

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
    except Exception as e:
        logger.error(
            "Failed to renew subscription",
            user_id=current_user.id,
            subscription_id=request.subscription_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to renew subscription"
        )


@router.get("/subscriptions", response_model=SubscriptionListResponse)
async def get_user_subscriptions(
    status: Optional[SubscriptionStatusEnum] = Query(None, description="Фильтр по статусу"),
    subscription_type: Optional[SubscriptionTypeEnum] = Query(None, description="Фильтр по типу"),
    limit: int = Query(50, ge=1, le=100, description="Количество записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        subscriptions = await subscription_service.get_user_subscriptions(
            db=db,
            user_id=current_user.id,
            status=status.value if status else None,
            subscription_type=subscription_type.value if subscription_type else None,
            limit=limit,
            offset=offset
        )

        subscription_responses = []
        for subscription in subscriptions:
            subscription_response = SubscriptionResponse.from_orm(subscription)
            subscription_response.is_active = subscription.is_active
            subscription_response.is_expired = subscription.is_expired
            subscription_response.is_trial = subscription.is_trial
            subscription_response.days_until_expiry = subscription.days_until_expiry
            subscription_response.next_payment_amount = str(subscription.next_payment_amount)
            subscription_responses.append(subscription_response)

        has_more = len(subscriptions) == limit

        return SubscriptionListResponse(
            subscriptions=subscription_responses,
            total=len(subscriptions),
            has_more=has_more
        )

    except Exception as e:
        logger.error(
            "Failed to get user subscriptions",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user subscriptions"
        )


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        subscription = await subscription_service.get_subscription_by_id(db, subscription_id)

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        if subscription.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        subscription_response = SubscriptionResponse.from_orm(subscription)
        subscription_response.is_active = subscription.is_active
        subscription_response.is_expired = subscription.is_expired
        subscription_response.is_trial = subscription.is_trial
        subscription_response.days_until_expiry = subscription.days_until_expiry
        subscription_response.next_payment_amount = str(subscription.next_payment_amount)

        return subscription_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get subscription",
            user_id=current_user.id,
            subscription_id=subscription_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscription"
        )


@router.post("/invites/create", response_model=SubscriptionInviteResponse)
async def create_subscription_invite(
    request: SubscriptionInviteCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        invite = await subscription_service.create_subscription_invite(
            db=db,
            subscription_id=request.subscription_id,
            creator=current_user,
            max_uses=request.max_uses,
            expires_at=request.expires_at,
            description=request.description
        )

        invite_response = SubscriptionInviteResponse.from_orm(invite)
        invite_response.is_valid = invite.is_valid
        invite_response.invite_url = f"https://t.me/your_bot?start=invite_{invite.invite_id}"

        return invite_response

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
            "Failed to create subscription invite",
            user_id=current_user.id,
            subscription_id=request.subscription_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription invite"
        )


@router.post("/invites/use", response_model=SubscriptionResponse)
async def use_subscription_invite(
    request: SubscriptionInviteUseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        subscription = await subscription_service.use_subscription_invite(
            db=db,
            invite_id=request.invite_id,
            user=current_user
        )

        subscription_response = SubscriptionResponse.from_orm(subscription)
        subscription_response.is_active = subscription.is_active
        subscription_response.is_expired = subscription.is_expired
        subscription_response.is_trial = subscription.is_trial
        subscription_response.days_until_expiry = subscription.days_until_expiry
        subscription_response.next_payment_amount = str(subscription.next_payment_amount)

        return subscription_response

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
            "Failed to use subscription invite",
            user_id=current_user.id,
            invite_id=request.invite_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to use subscription invite"
        )


@router.get("/summary", response_model=SubscriptionSummaryResponse)
async def get_subscription_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        subscriptions = await subscription_service.get_user_subscriptions(
            db=db,
            user_id=current_user.id,
            limit=1000
        )

        total_subscriptions = len(subscriptions)
        active_subscriptions = len([s for s in subscriptions if s.is_active])
        expired_subscriptions = len([s for s in subscriptions if s.is_expired])
        cancelled_subscriptions = len([s for s in subscriptions if s.status == "cancelled"])

        total_spent = sum(s.total_amount_paid for s in subscriptions)
        currency = subscriptions[0].currency if subscriptions else "USD"

        active_subs = [s for s in subscriptions if s.is_active and s.next_billing_at]
        next_payment_date = None
        next_payment_amount = None

        if active_subs:
            next_sub = min(active_subs, key=lambda s: s.next_billing_at)
            next_payment_date = next_sub.next_billing_at
            next_payment_amount = str(next_sub.price)

        return SubscriptionSummaryResponse(
            total_subscriptions=total_subscriptions,
            active_subscriptions=active_subscriptions,
            expired_subscriptions=expired_subscriptions,
            cancelled_subscriptions=cancelled_subscriptions,
            total_spent=str(total_spent),
            currency=currency,
            next_payment_date=next_payment_date,
            next_payment_amount=next_payment_amount
        )

    except Exception as e:
        logger.error(
            "Failed to get subscription summary",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscription summary"
        )


@router.get("/stats/{subscription_id}", response_model=SubscriptionStatsResponse)
async def get_subscription_stats(
    subscription_id: str,
    days: int = Query(30, ge=1, le=365, description="Количество дней для статистики"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        subscription = await subscription_service.get_subscription_by_id(db, subscription_id)

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        if subscription.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        stats = await subscription_service.get_subscription_stats(db, subscription_id, days)

        return SubscriptionStatsResponse(
            subscription_id=subscription.subscription_id,
            title=subscription.title,
            status=subscription.status,
            total_payments=subscription.total_payments,
            total_revenue=str(subscription.total_amount_paid),
            currency=subscription.currency,
            active_subscribers=1 if subscription.is_active else 0,
            cancelled_subscribers=1 if subscription.status == "cancelled" else 0,
            revenue_this_month="0",
            revenue_last_month="0",
            growth_rate=0.0,
            churn_rate=0.0,
            created_at=subscription.created_at,
            next_billing_at=subscription.next_billing_at,
            expires_at=subscription.expires_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get subscription stats",
            user_id=current_user.id,
            subscription_id=subscription_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscription stats"
        )


@router.post("/createSubscription")
async def create_subscription_legacy(
    request: SubscriptionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await create_subscription(request, current_user, db)


@router.get("/getSubscriptions")
async def get_subscriptions_legacy(
    status: Optional[SubscriptionStatusEnum] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_user_subscriptions(status, None, limit, offset, current_user, db)


@router.post("/cancelSubscription")
async def cancel_subscription_legacy(
    request: SubscriptionCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await cancel_subscription(request, current_user, db)
