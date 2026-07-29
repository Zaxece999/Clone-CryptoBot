import uuid
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload
import structlog

from app.models.api import (
    ApiApplication, ApiKey, ApiRequest, ApiWebhook, ApiWebhookDelivery,
    ApiRateLimit, ApiKeyStatus, ApiKeyScope
)
from app.models.user import User
from app.utils.exceptions import (
    ValidationError, NotFoundError, PermissionError, RateLimitError, ApiError
)

logger = structlog.get_logger(__name__)


class ApiService:
    def __init__(self):
        self.default_rate_limits = {
            "per_minute": 60,
            "per_hour": 1000,
            "per_day": 10000
        }
        self.webhook_timeout_seconds = 30
        self.webhook_max_attempts = 3

    async def create_application(
        self,
        db: AsyncSession,
        owner: User,
        name: str,
        description: Optional[str] = None,
        website_url: Optional[str] = None,
        callback_url: Optional[str] = None
    ) -> ApiApplication:
        try:
            if len(name.strip()) < 3:
                raise ValidationError("Application name must be at least 3 characters")

            existing_apps_count = await self._get_user_applications_count(db, owner.id)
            max_apps = 10 if owner.is_premium else 3

            if existing_apps_count >= max_apps:
                raise ValidationError(f"Maximum {max_apps} applications allowed")

            application = ApiApplication(
                app_id=str(uuid.uuid4()).replace("-", ""),
                owner_id=owner.id,
                name=name.strip(),
                description=description,
                website_url=website_url,
                callback_url=callback_url,
                rate_limit_per_minute=self.default_rate_limits["per_minute"],
                rate_limit_per_hour=self.default_rate_limits["per_hour"],
                rate_limit_per_day=self.default_rate_limits["per_day"]
            )

            db.add(application)
            await db.commit()
            await db.refresh(application)

            logger.info(
                "API application created",
                app_id=application.app_id,
                owner_id=owner.id,
                name=name
            )

            return application

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to create API application",
                owner_id=owner.id,
                name=name,
                error=str(e),
                exc_info=True
            )
            raise

    async def create_api_key(
        self,
        db: AsyncSession,
        application_id: str,
        user: User,
        name: str,
        scopes: List[ApiKeyScope],
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        allowed_ips: Optional[List[str]] = None
    ) -> tuple[ApiKey, str]:
        try:
            application = await self.get_application_by_id(db, application_id)
            if not application:
                raise NotFoundError("Application not found")

            if application.owner_id != user.id:
                raise PermissionError("Access denied")

            if len(name.strip()) < 3:
                raise ValidationError("API key name must be at least 3 characters")

            if not scopes:
                raise ValidationError("At least one scope is required")

            existing_keys_count = await self._get_application_keys_count(db, application.id)
            max_keys = 20 if user.is_premium else 5

            if existing_keys_count >= max_keys:
                raise ValidationError(f"Maximum {max_keys} API keys allowed per application")

            api_key_value, key_hash = ApiKey.generate_key()
            key_prefix = api_key_value[:8]

            api_key = ApiKey(
                key_id=str(uuid.uuid4()).replace("-", ""),
                application_id=application.id,
                user_id=user.id,
                key_hash=key_hash,
                key_prefix=key_prefix,
                name=name.strip(),
                description=description,
                status=ApiKeyStatus.ACTIVE.value,
                scopes=json.dumps([scope.value for scope in scopes]),
                expires_at=expires_at,
                allowed_ips=json.dumps(allowed_ips) if allowed_ips else None
            )

            db.add(api_key)
            await db.commit()
            await db.refresh(api_key)

            logger.info(
                "API key created",
                key_id=api_key.key_id,
                application_id=application_id,
                user_id=user.id,
                name=name,
                scopes=[scope.value for scope in scopes]
            )

            return api_key, api_key_value

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to create API key",
                application_id=application_id,
                user_id=user.id,
                name=name,
                error=str(e),
                exc_info=True
            )
            raise

    async def authenticate_api_key(
        self,
        db: AsyncSession,
        api_key_value: str,
        ip_address: Optional[str] = None
    ) -> Optional[ApiKey]:
        try:
            key_hash = hashlib.sha256(api_key_value.encode()).hexdigest()

            query = select(ApiKey).where(
                and_(
                    ApiKey.key_hash == key_hash,
                    ApiKey.status == ApiKeyStatus.ACTIVE.value
                )
            ).options(selectinload(ApiKey.application))

            result = await db.execute(query)
            api_key = result.scalar_one_or_none()

            if not api_key:
                return None

            if api_key.is_expired:
                api_key.status = ApiKeyStatus.EXPIRED.value
                await db.commit()
                return None

            if api_key.allowed_ips and ip_address:
                allowed_ips = json.loads(api_key.allowed_ips)
                if ip_address not in allowed_ips:
                    logger.warning(
                        "API key access denied - IP not allowed",
                        key_id=api_key.key_id,
                        ip_address=ip_address,
                        allowed_ips=allowed_ips
                    )
                    return None

            api_key.last_used_at = datetime.utcnow()
            api_key.application.last_used_at = datetime.utcnow()
            await db.commit()

            return api_key

        except Exception as e:
            logger.error(
                "Failed to authenticate API key",
                error=str(e),
                exc_info=True
            )
            return None

    async def check_rate_limit(
        self,
        db: AsyncSession,
        api_key: ApiKey,
        endpoint: str
    ) -> bool:
        try:
            now = datetime.utcnow()

            limits_to_check = [
                ("minute", 1, api_key.rate_limit_per_minute or api_key.application.rate_limit_per_minute),
                ("hour", 60, api_key.rate_limit_per_hour or api_key.application.rate_limit_per_hour),
                ("day", 1440, api_key.rate_limit_per_day or api_key.application.rate_limit_per_day)
            ]

            for window_type, window_minutes, limit in limits_to_check:
                if limit is None:
                    continue

                if window_type == "minute":
                    window_start = now.replace(second=0, microsecond=0)
                elif window_type == "hour":
                    window_start = now.replace(minute=0, second=0, microsecond=0)
                else:
                    window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

                query = select(ApiRateLimit).where(
                    and_(
                        ApiRateLimit.api_key_id == api_key.id,
                        ApiRateLimit.window_start == window_start,
                        ApiRateLimit.window_type == window_type
                    )
                )

                result = await db.execute(query)
                rate_limit = result.scalar_one_or_none()

                if not rate_limit:
                    rate_limit = ApiRateLimit(
                        api_key_id=api_key.id,
                        window_start=window_start,
                        window_type=window_type,
                        request_count=0
                    )
                    db.add(rate_limit)

                if rate_limit.request_count >= limit:
                    logger.warning(
                        "Rate limit exceeded",
                        key_id=api_key.key_id,
                        window_type=window_type,
                        current_count=rate_limit.request_count,
                        limit=limit
                    )
                    return False

                rate_limit.request_count += 1

            await db.commit()
            return True

        except Exception as e:
            logger.error(
                "Failed to check rate limit",
                key_id=api_key.key_id,
                endpoint=endpoint,
                error=str(e),
                exc_info=True
            )
            return False

    async def log_api_request(
        self,
        db: AsyncSession,
        api_key: ApiKey,
        method: str,
        endpoint: str,
        status_code: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> ApiRequest:
        try:
            api_request = ApiRequest(
                request_id=str(uuid.uuid4()).replace("-", ""),
                application_id=api_key.application_id,
                api_key_id=api_key.id,
                user_id=api_key.user_id,
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                ip_address=ip_address,
                user_agent=user_agent,
                request_size=request_size,
                response_size=response_size,
                response_time_ms=response_time_ms,
                error_code=error_code,
                error_message=error_message
            )

            db.add(api_request)

            api_key.total_requests += 1
            api_key.application.total_requests += 1

            if api_request.is_successful:
                api_key.successful_requests += 1
                api_key.application.successful_requests += 1
            else:
                api_key.failed_requests += 1
                api_key.application.failed_requests += 1

            await db.commit()

            return api_request

        except Exception as e:
            logger.error(
                "Failed to log API request",
                key_id=api_key.key_id,
                method=method,
                endpoint=endpoint,
                error=str(e),
                exc_info=True
            )
            raise

    async def check_api_key_scope(
        self,
        api_key: ApiKey,
        required_scope: ApiKeyScope
    ) -> bool:
        try:
            key_scopes = json.loads(api_key.scopes)

            if required_scope.value in key_scopes:
                return True

            if ApiKeyScope.ADMIN.value in key_scopes:
                return True

            if required_scope.value.endswith(":read") and ApiKeyScope.WRITE.value in key_scopes:
                return True

            write_scope = required_scope.value.replace(":read", ":write")
            if write_scope in key_scopes:
                return True

            return False

        except Exception as e:
            logger.error(
                "Failed to check API key scope",
                key_id=api_key.key_id,
                required_scope=required_scope.value,
                error=str(e),
                exc_info=True
            )
            return False

    async def get_application_by_id(
        self,
        db: AsyncSession,
        app_id: str,
        include_keys: bool = False
    ) -> Optional[ApiApplication]:
        try:
            query = select(ApiApplication).where(ApiApplication.app_id == app_id)

            if include_keys:
                query = query.options(selectinload(ApiApplication.api_keys))

            result = await db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "Failed to get application by ID",
                app_id=app_id,
                error=str(e),
                exc_info=True
            )
            return None

    async def get_user_applications(
        self,
        db: AsyncSession,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[ApiApplication]:
        try:
            query = select(ApiApplication).where(
                ApiApplication.owner_id == user_id
            ).order_by(desc(ApiApplication.created_at)).limit(limit).offset(offset)

            result = await db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(
                "Failed to get user applications",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            return []

    async def get_application_api_keys(
        self,
        db: AsyncSession,
        application_id: str,
        user: User,
        limit: int = 50,
        offset: int = 0
    ) -> List[ApiKey]:
        try:
            application = await self.get_application_by_id(db, application_id)
            if not application or application.owner_id != user.id:
                raise PermissionError("Access denied")

            query = select(ApiKey).where(
                ApiKey.application_id == application.id
            ).order_by(desc(ApiKey.created_at)).limit(limit).offset(offset)

            result = await db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(
                "Failed to get application API keys",
                application_id=application_id,
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            return []

    async def revoke_api_key(
        self,
        db: AsyncSession,
        key_id: str,
        user: User
    ) -> ApiKey:
        try:
            query = select(ApiKey).where(ApiKey.key_id == key_id).options(
                selectinload(ApiKey.application)
            )
            result = await db.execute(query)
            api_key = result.scalar_one_or_none()

            if not api_key:
                raise NotFoundError("API key not found")

            if api_key.application.owner_id != user.id:
                raise PermissionError("Access denied")

            api_key.status = ApiKeyStatus.REVOKED.value
            await db.commit()

            logger.info(
                "API key revoked",
                key_id=key_id,
                user_id=user.id
            )

            return api_key

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to revoke API key",
                key_id=key_id,
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            raise

    async def get_api_statistics(
        self,
        db: AsyncSession,
        application_id: str,
        user: User,
        days: int = 30
    ) -> Dict[str, Any]:
        try:
            application = await self.get_application_by_id(db, application_id)
            if not application or application.owner_id != user.id:
                raise PermissionError("Access denied")


            return {
                "application_id": application.app_id,
                "name": application.name,
                "total_requests": application.total_requests,
                "successful_requests": application.successful_requests,
                "failed_requests": application.failed_requests,
                "success_rate": application.success_rate,
                "created_at": application.created_at.isoformat(),
                "last_used_at": application.last_used_at.isoformat() if application.last_used_at else None
            }

        except Exception as e:
            logger.error(
                "Failed to get API statistics",
                application_id=application_id,
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            return {}

    async def _get_user_applications_count(self, db: AsyncSession, user_id: int) -> int:
        query = select(func.count(ApiApplication.id)).where(ApiApplication.owner_id == user_id)
        result = await db.execute(query)
        return result.scalar() or 0

    async def _get_application_keys_count(self, db: AsyncSession, application_id: int) -> int:
        query = select(func.count(ApiKey.id)).where(ApiKey.application_id == application_id)
        result = await db.execute(query)
        return result.scalar() or 0

    async def create_webhook(
        self,
        db: AsyncSession,
        application_id: str,
        user: User,
        url: str,
        events: List[str],
        secret: Optional[str] = None
    ) -> ApiWebhook:
        try:
            application = await self.get_application_by_id(db, application_id)
            if not application or application.owner_id != user.id:
                raise PermissionError("Access denied")

            if not url.startswith(('http://', 'https://')):
                raise ValidationError("Webhook URL must start with http:// or https://")

            webhook = ApiWebhook(
                webhook_id=str(uuid.uuid4()).replace("-", ""),
                application_id=application.id,
                url=url,
                secret=secret,
                events=json.dumps(events)
            )

            db.add(webhook)
            await db.commit()
            await db.refresh(webhook)

            logger.info(
                "Webhook created",
                webhook_id=webhook.webhook_id,
                application_id=application_id,
                url=url,
                events=events
            )

            return webhook

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to create webhook",
                application_id=application_id,
                user_id=user.id,
                url=url,
                error=str(e),
                exc_info=True
            )
            raise


api_service = ApiService()
