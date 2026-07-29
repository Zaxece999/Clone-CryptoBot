import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient
from decimal import Decimal

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.wallet import WalletBalance
from app.config import settings


TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        language_code="ru",
        is_active=True
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
async def test_user_with_balance(db_session: AsyncSession, test_user: User) -> User:
    balances = [
        WalletBalance(
            user_id=test_user.id,
            currency="BTC",
            balance=Decimal("1.0"),
            frozen_balance=Decimal("0.0")
        ),
        WalletBalance(
            user_id=test_user.id,
            currency="ETH",
            balance=Decimal("10.0"),
            frozen_balance=Decimal("0.0")
        ),
        WalletBalance(
            user_id=test_user.id,
            currency="USDT",
            balance=Decimal("1000.0"),
            frozen_balance=Decimal("0.0")
        )
    ]

    for balance in balances:
        db_session.add(balance)

    await db_session.commit()

    return test_user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    from app.models.admin import AdminUser, AdminRole, AdminPermission

    user = User(
        telegram_id=987654321,
        username="admin",
        first_name="Admin",
        last_name="User",
        language_code="ru",
        is_active=True
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    admin = AdminUser(
        user_id=user.id,
        role=AdminRole.SUPER_ADMIN,
        permissions=[perm.value for perm in AdminPermission],
        is_active=True,
        is_super_admin=True
    )

    db_session.add(admin)
    await db_session.commit()

    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    return {
        "Authorization": f"Bearer test_token_{test_user.id}"
    }


@pytest.fixture
def api_key_headers() -> dict:
    return {
        "Crypto-Pay-API-Token": "test_api_key_123"
    }


def assert_response_success(response, expected_status: int = 200):
    assert response.status_code == expected_status
    if response.headers.get("content-type", "").startswith("application/json"):
        data = response.json()
        if "ok" in data:
            assert data["ok"] is True


def assert_response_error(response, expected_status: int = 400):
    assert response.status_code == expected_status
    if response.headers.get("content-type", "").startswith("application/json"):
        data = response.json()
        if "ok" in data:
            assert data["ok"] is False


def create_test_data(db_session: AsyncSession, model_class, **kwargs):
    instance = model_class(**kwargs)
    db_session.add(instance)
    return instance


pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.api = pytest.mark.api
pytest.mark.bot = pytest.mark.bot
pytest.mark.slow = pytest.mark.slow
