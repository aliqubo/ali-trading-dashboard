"""Authentication routes: register, login, refresh, logout, me.

Reconstructed MVP scaffolding — original source unavailable for this route
file's wiring. The services it calls (AuthenticationService, SessionService,
RefreshTokenService, JWTTokenService, AuthorizationService) are restored or
reconstructed elsewhere — see RECOVERY_MANIFEST.md.

`/auth/register` is new glue code with no archived source anywhere: no
IUserService implementation exists in any of the 18 archives (only its
unimplemented Phase 3.0 interface does). It hashes the password and inserts
a user row directly. It also sets `status=ACTIVE` explicitly, bypassing the
implied-but-unbuilt email-verification flow (the column's own server default
is `pending`, which `AuthenticationService.authenticate()` would then treat
as `USER_DISABLED` and refuse to log in) — done deliberately so the
register -> login round trip is actually testable in this MVP.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import (
    AuthenticationServiceDep,
    AuthorizationServiceDep,
    CurrentUserDep,
    PasswordHasherDep,
    RefreshTokenServiceDep,
    SessionServiceDep,
    TokenServiceDep,
    UnitOfWorkDep,
)
from app.core.exceptions import ConflictError
from app.models.enums import UserStatus
from app.services.authentication.exceptions import AuthenticationError
from app.services.identity.dtos import PermissionResponse, RoleResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    identifier: str
    password: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginResponse(TokenPairResponse):
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class MeResponse(BaseModel):
    user: UserResponse
    roles: list[RoleResponse]
    permissions: list[PermissionResponse]


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    uow: UnitOfWorkDep,
    password_hasher: PasswordHasherDep,
) -> UserResponse:
    """Create a user account. New MVP glue code — not archived anywhere."""
    if await uow.users.get_by_email(body.email) is not None:
        raise ConflictError("A user with this email already exists.")
    if await uow.users.get_by_username(body.username) is not None:
        raise ConflictError("A user with this username already exists.")

    user = await uow.users.create(
        {
            "email": body.email,
            "username": body.username,
            "password_hash": password_hasher.hash(body.password),
            "full_name": body.full_name,
            "status": UserStatus.ACTIVE,
        }
    )
    await uow.commit()
    await uow.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    auth_service: AuthenticationServiceDep,
    session_service: SessionServiceDep,
    refresh_token_service: RefreshTokenServiceDep,
    token_service: TokenServiceDep,
) -> LoginResponse:
    """Verify credentials, then issue a session and a token pair."""
    result = await auth_service.authenticate(body.identifier, body.password)
    if not result.success or result.user is None:
        # Generic failure — the service already logged the specific reason
        # (unknown user / wrong password / disabled / locked) server-side.
        raise AuthenticationError()

    session = await session_service.create_session(
        result.user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    try:
        access_token = token_service.create_access_token(str(result.user.id))
        refresh_token, _ = await refresh_token_service.persist_refresh_token(
            result.user.id, session.id
        )
    except Exception:
        # create_session() above already committed independently (each
        # service method commits its own unit of work) — if minting the
        # token pair then fails, revoke the now-orphaned session rather than
        # leaving an active session behind with no token ever delivered.
        await session_service.revoke_session(session.id)
        raise
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=result.user,
    )


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    refresh_token_service: RefreshTokenServiceDep,
    token_service: TokenServiceDep,
) -> TokenPairResponse:
    """Rotate a refresh token and mint a fresh access token."""
    new_raw_token, new_record = await refresh_token_service.rotate_refresh_token(
        body.refresh_token
    )
    access_token = token_service.create_access_token(str(new_record.user_id))
    return TokenPairResponse(access_token=access_token, refresh_token=new_raw_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout(
    body: LogoutRequest,
    session_service: SessionServiceDep,
    refresh_token_service: RefreshTokenServiceDep,
) -> None:
    """Revoke the session and refresh token behind the given token, if any."""
    record = await refresh_token_service.get_refresh_token(body.refresh_token)
    if record is not None and not record.is_revoked:
        # A stale, already-rotated/revoked token must not be able to tear
        # down the session's *current* live token — only an as-yet-unused
        # token proves the caller still holds a currently valid credential.
        if record.session_id is not None:
            await session_service.revoke_session(record.session_id)
        await refresh_token_service.revoke_refresh_token(body.refresh_token)


@router.get("/me")
async def me(
    current_user: CurrentUserDep,
    authorization_service: AuthorizationServiceDep,
) -> MeResponse:
    """Return the current user plus their roles and permissions (RBAC)."""
    roles = await authorization_service.get_user_roles(current_user.id)
    permissions = await authorization_service.get_user_permissions(
        current_user.id, roles=roles
    )
    return MeResponse(
        user=UserResponse.model_validate(current_user),
        roles=roles,
        permissions=permissions,
    )
