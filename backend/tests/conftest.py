"""Pytest configuration and fixtures."""

import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_uow
from app.core.config import get_settings
from app.main import app
from app.models import Base
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    settings = get_settings()
    # Use test database - you need to create this DB first
    test_db_url = settings.database_url.replace("/ali_trading", "/ali_trading_test")
    engine = create_async_engine(test_db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def uow(db_session: AsyncSession) -> AsyncGenerator[SqlAlchemyUnitOfWork, None]:
    """Create a Unit of Work instance."""
    # Create a session factory that returns the test session
    async def get_session_factory():
        return db_session

    uow = SqlAlchemyUnitOfWork(lambda: db_session)
    yield uow


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with ASGI transport, routed at the isolated test DB.

    ``ASGITransport`` does not run the app's ``lifespan`` (no ``init_engine()``
    call — confirmed empirically: every request raised ``RuntimeError:
    Database engine not initialised``), and even if it did, the app's real
    engine points at ``ali_trading`` (from ``backend/.env``), not
    ``ali_trading_test`` — every HTTP-driven fixture would silently read/write
    the real dev database instead of the isolated one ``db_session`` just
    created. Overriding the ``get_uow`` dependency sidesteps both: every route
    that resolves a ``UnitOfWorkDep`` (all of ``/auth/*``) gets a
    ``SqlAlchemyUnitOfWork`` bound to this test's own session instead.
    """

    async def override_get_uow() -> AsyncGenerator[SqlAlchemyUnitOfWork, None]:
        yield SqlAlchemyUnitOfWork(lambda: db_session)

    app.dependency_overrides[get_uow] = override_get_uow
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_uow, None)


@pytest_asyncio.fixture
async def test_user_credentials() -> dict:
    """Return test user credentials."""
    return {
        "email": "testuser@example.com",
        "username": "testuser",
        "password": "TestPassword123!",
        "full_name": "Test User",
    }


@pytest_asyncio.fixture
async def auth_headers(
    client: AsyncClient,
    test_user_credentials: dict
) -> dict:
    """Get authentication headers by registering and logging in."""
    # Register user
    register_response = await client.post(
        "/auth/register",
        json=test_user_credentials,
    )

    # If registration fails (user might exist), try login directly
    if register_response.status_code != 201:
        # Try login
        login_response = await client.post(
            "/auth/login",
            json={
                "identifier": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}

        # Both registration and the login retry failed — fail loudly here
        # rather than handing back a fake bearer token. A fake token would
        # make this fixture look like it "succeeded", only for every test
        # that uses it to fail later with a confusing 401 on its first
        # authenticated call, far from the actual root cause.
        raise RuntimeError(
            "auth_headers fixture could not obtain a token: register() -> "
            f"{register_response.status_code} {register_response.text}, "
            f"login() -> {login_response.status_code} {login_response.text}"
        )

    # Login with registered user
    login_response = await client.post(
        "/auth/login",
        json={
            "identifier": test_user_credentials["username"],
            "password": test_user_credentials["password"],
        },
    )
    token = login_response.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_user_id(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user_credentials: dict
) -> uuid.UUID:
    """Get or create a test user and return their ID."""
    # Register user
    response = await client.post(
        "/auth/register",
        json=test_user_credentials,
    )

    if response.status_code == 201:
        return uuid.UUID(response.json()["id"])

    # If user exists, try login and get user info
    login_response = await client.post(
        "/auth/login",
        json={
            "identifier": test_user_credentials["username"],
            "password": test_user_credentials["password"],
        },
    )
    if login_response.status_code == 200:
        token = login_response.json().get("access_token")
        me_response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        if me_response.status_code == 200:
            return uuid.UUID(me_response.json()["user"]["id"])

    # Fallback: create the user directly via the repository, against this
    # test's own isolated session/database — not the real global one (the
    # provided version of this fixture used app.db.session.get_session_factory()
    # here, which is the *real* ali_trading engine, not ali_trading_test).
    uow = SqlAlchemyUnitOfWork(lambda: db_session)
    user = await uow.users.create({
        "email": test_user_credentials["email"],
        "username": test_user_credentials["username"],
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$test$hash",
        "full_name": test_user_credentials["full_name"],
        "status": "active",
    })
    await uow.commit()
    return user.id


@pytest.fixture
def test_password() -> str:
    """Return a test password."""
    return "TestPassword123!"
