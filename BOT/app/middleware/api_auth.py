import time
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.database import get_db
from app.services.api import api_service
from app.models.api import ApiKey, ApiKeyScope
from app.utils.exceptions import RateLimitError, ApiError

logger = structlog.get_logger(__name__)


class ApiAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.security = HTTPBearer(auto_error=False)
        self.api_endpoints = [
            "/api/v1/",
            "/crypto-pay/api/"
        ]

    async def dispatch(self, request: Request, call_next):
        if not self._requires_api_auth(request.url.path):
            return await call_next(request)

        start_time = time.time()

        try:
            api_key = await self._extract_api_key(request)

            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key required",
                    headers={"WWW-Authenticate": "Bearer"}
                )

            db = next(get_db())
            authenticated_key = await api_service.authenticate_api_key(
                db=db,
                api_key_value=api_key,
                ip_address=request.client.host if request.client else None
            )

            if not authenticated_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired API key"
                )

            if not await api_service.check_rate_limit(
                db=db,
                api_key=authenticated_key,
                endpoint=request.url.path
            ):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )

            request.state.api_key = authenticated_key
            request.state.api_application = authenticated_key.application

            response = await call_next(request)

            response_time_ms = int((time.time() - start_time) * 1000)

            await api_service.log_api_request(
                db=db,
                api_key=authenticated_key,
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                response_time_ms=response_time_ms
            )

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "API authentication error",
                path=request.url.path,
                method=request.method,
                error=str(e),
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    def _requires_api_auth(self, path: str) -> bool:
        return any(path.startswith(endpoint) for endpoint in self.api_endpoints)

    async def _extract_api_key(self, request: Request) -> Optional[str]:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]

        crypto_pay_token = request.headers.get("crypto-pay-api-token")
        if crypto_pay_token:
            return crypto_pay_token

        api_key = request.query_params.get("api_key")
        if api_key:
            return api_key

        return None


def require_api_scope(required_scope: ApiKeyScope):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )

            if not hasattr(request.state, 'api_key'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key required"
                )

            api_key = request.state.api_key

            if not await api_service.check_api_key_scope(api_key, required_scope):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient scope. Required: {required_scope.value}"
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


class ApiRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.global_rate_limits = {
            "requests_per_second": 100,
            "requests_per_minute": 1000
        }

    async def dispatch(self, request: Request, call_next):
        return await call_next(request)


class ApiLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        logger.info(
            "API request started",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
            api_key_prefix=getattr(request.state, 'api_key', {}).get('key_prefix') if hasattr(request.state, 'api_key') else None
        )

        try:
            response = await call_next(request)

            process_time = time.time() - start_time

            logger.info(
                "API request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time=process_time,
                api_key_prefix=getattr(request.state, 'api_key', {}).get('key_prefix') if hasattr(request.state, 'api_key') else None
            )

            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-RateLimit-Remaining"] = "999"

            return response

        except Exception as e:
            process_time = time.time() - start_time

            logger.error(
                "API request failed",
                method=request.method,
                path=request.url.path,
                process_time=process_time,
                error=str(e),
                api_key_prefix=getattr(request.state, 'api_key', {}).get('key_prefix') if hasattr(request.state, 'api_key') else None,
                exc_info=True
            )

            raise


class ApiCorsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.allowed_origins = ["*"]
        self.allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allowed_headers = [
            "Authorization",
            "Content-Type",
            "Crypto-Pay-API-Token",
            "X-Requested-With"
        ]

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            response = Response()
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
            response.headers["Access-Control-Max-Age"] = "86400"
            return response

        response = await call_next(request)

        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)

        return response


def get_current_api_key(request: Request) -> ApiKey:
    if not hasattr(request.state, 'api_key'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    return request.state.api_key


def get_current_api_application(request: Request):
    if not hasattr(request.state, 'api_application'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    return request.state.api_application
