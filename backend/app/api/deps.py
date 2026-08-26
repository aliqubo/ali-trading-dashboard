"""FastAPI dependency providers (ARCHITECTURE.md §7).

Reconstructed MVP scaffolding — original source unavailable.

MVP Phase 3 adds: password hasher, JWT token service, the three
authentication-domain services (AuthenticationService, SessionService,
RefreshTokenService), AuthorizationService, and get_current_user for
JWT-protected routes. See RECOVERY_MANIFEST.md.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError
from app.core.logging import get_logger
from app.core.security.password_hasher import PasswordHasher
from app.core.security.token import ITokenService, JWTTokenService, TokenType
from app.db.session import get_session, get_session_factory
from app.models import User
from app.models.enums import UserStatus
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork
from app.services.authentication.authentication_service import AuthenticationService
from app.services.authentication.refresh_token_service import RefreshTokenService
from app.services.authentication.session_service import SessionService
from app.services.authorization.authorization_service import AuthorizationService

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbSessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_uow() -> AsyncIterator[SqlAlchemyUnitOfWork]:
    """Yield a request-scoped Unit of Work bound to its own session."""
    uow = SqlAlchemyUnitOfWork(get_session_factory())
    try:
        yield uow
    finally:
        await uow.close()


UnitOfWorkDep = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]


def get_password_hasher() -> PasswordHasher:
    """Return an Argon2id password hasher (default cost parameters)."""
    return PasswordHasher()


PasswordHasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]


def get_token_service(settings: SettingsDep) -> ITokenService:
    """Return a JWT token service configured from Settings."""
    return JWTTokenService(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
        refresh_token_expire_days=settings.jwt_refresh_token_expire_days,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )


TokenServiceDep = Annotated[ITokenService, Depends(get_token_service)]


def get_authentication_service(
    uow: UnitOfWorkDep, password_hasher: PasswordHasherDep
) -> AuthenticationService:
    return AuthenticationService(
        uow, password_hasher, get_logger("app.services.authentication")
    )


AuthenticationServiceDep = Annotated[
    AuthenticationService, Depends(get_authentication_service)
]


def get_session_service(uow: UnitOfWorkDep, settings: SettingsDep) -> SessionService:
    return SessionService(
        uow,
        get_logger("app.services.session"),
        default_session_ttl=timedelta(days=settings.jwt_refresh_token_expire_days),
    )


SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]


def get_refresh_token_service(
    uow: UnitOfWorkDep, token_service: TokenServiceDep
) -> RefreshTokenService:
    return RefreshTokenService(
        uow, token_service, get_logger("app.services.refresh_token")
    )


RefreshTokenServiceDep = Annotated[
    RefreshTokenService, Depends(get_refresh_token_service)
]


def get_authorization_service(uow: UnitOfWorkDep) -> AuthorizationService:
    return AuthorizationService(uow, get_logger("app.services.authorization"))


AuthorizationServiceDep = Annotated[
    AuthorizationService, Depends(get_authorization_service)
]


_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
    uow: UnitOfWorkDep,
    token_service: TokenServiceDep,
) -> User:
    """Resolve the current user from a Bearer access token, or raise 401."""
    if credentials is None:
        raise UnauthorizedError("Missing bearer token.")

    claims = token_service.validate_token(credentials.credentials, TokenType.ACCESS)
    try:
        user_id = uuid.UUID(claims.sub)
    except ValueError as exc:
        raise UnauthorizedError() from exc

    user = await uow.users.get_by_id(user_id)
    if user is None or user.status is not UserStatus.ACTIVE:
        raise UnauthorizedError()
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
