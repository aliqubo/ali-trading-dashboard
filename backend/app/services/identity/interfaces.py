"""Identity domain service interfaces (BACKEND_SPEC §2.1, §5.1).

Defines five service interfaces as typing Protocols — contracts only. No
implementation exists in this phase.

Scope discipline (per this phase's restrictions and DATABASE_DESIGN.md §2.1
"يُمنع" notes):
- No password hashing, no JWT, no refresh-token issuance, no login/logout/
  register flows, no permission *enforcement* — those are Authentication's
  and Authorization's responsibilities, not Identity's, and none of it is
  built here regardless.
- Methods on ``IRoleService``/``IPermissionService`` manage the *data*
  relationships (which roles a user has, which permissions a role has) — they
  do not evaluate or enforce access at request time.
- ``ISessionService``/``IApiKeyService`` manage session/API-key *records*
  (list, inspect, revoke) — they do not authenticate, issue tokens, or
  generate/hash secrets.

Every interface extends :class:`app.services.interfaces.IService`, so each
carries the shared ``uow`` contract in addition to its own methods.
"""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from app.services.identity.dtos import (
    ApiKeyResponse,
    CreateUserRequest,
    PermissionResponse,
    RoleResponse,
    SessionResponse,
    UpdateUserRequest,
    UserResponse,
)
from app.services.interfaces import IService


@runtime_checkable
class IUserService(IService, Protocol):
    """Contract for user account management (Identity's own scope).

    Covers account creation and profile updates only — no credential
    verification, no token issuance.
    """

    async def create_user(self, request: CreateUserRequest) -> UserResponse: ...

    async def get_user(self, user_id: uuid.UUID) -> UserResponse | None: ...

    async def update_user(
        self, user_id: uuid.UUID, request: UpdateUserRequest
    ) -> UserResponse: ...

    async def list_users(self) -> list[UserResponse]: ...


@runtime_checkable
class IRoleService(IService, Protocol):
    """Contract for role management and role-assignment *data*.

    Assignment methods manage the ``user_roles`` relationship as data; they do
    not enforce access control (Authorization's responsibility).
    """

    async def get_role(self, role_id: uuid.UUID) -> RoleResponse | None: ...

    async def list_roles(self) -> list[RoleResponse]: ...

    async def assign_role_to_user(
        self, user_id: uuid.UUID, role_id: uuid.UUID
    ) -> None: ...

    async def revoke_role_from_user(
        self, user_id: uuid.UUID, role_id: uuid.UUID
    ) -> None: ...

    async def list_roles_for_user(self, user_id: uuid.UUID) -> list[RoleResponse]: ...


@runtime_checkable
class IPermissionService(IService, Protocol):
    """Contract for permission management and role-permission *data*.

    Manages the ``role_permissions`` relationship as data; it does not
    evaluate or enforce permissions at request time (Authorization's
    responsibility).
    """

    async def get_permission(
        self, permission_id: uuid.UUID
    ) -> PermissionResponse | None: ...

    async def list_permissions(self) -> list[PermissionResponse]: ...

    async def assign_permission_to_role(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> None: ...

    async def revoke_permission_from_role(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> None: ...

    async def list_permissions_for_role(
        self, role_id: uuid.UUID
    ) -> list[PermissionResponse]: ...


@runtime_checkable
class ISessionService(IService, Protocol):
    """Contract for session *record* management.

    Lists and revokes session records; it does not authenticate a request or
    issue a session (Authentication's responsibility).
    """

    async def list_sessions_for_user(
        self, user_id: uuid.UUID
    ) -> list[SessionResponse]: ...

    async def get_session(self, session_id: uuid.UUID) -> SessionResponse | None: ...

    async def revoke_session(self, session_id: uuid.UUID) -> None: ...

    async def revoke_all_sessions_for_user(self, user_id: uuid.UUID) -> int: ...


@runtime_checkable
class IApiKeyService(IService, Protocol):
    """Contract for API key *record* management.

    Lists and revokes API key records; it does not generate or hash a key
    secret (deferred to the Authentication domain in a later phase).
    """

    async def list_api_keys_for_user(
        self, user_id: uuid.UUID
    ) -> list[ApiKeyResponse]: ...

    async def get_api_key(self, api_key_id: uuid.UUID) -> ApiKeyResponse | None: ...

    async def revoke_api_key(self, api_key_id: uuid.UUID) -> None: ...
