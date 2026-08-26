"""Authorization service interface (ARCHITECTURE.md §9.1: "التفويض: التحقق من
الصلاحيات في طبقة الـ Dependencies قبل الوصول للمنطق").

Defines ``IAuthorizationService`` as a typing Protocol — contract only for
this file; the concrete implementation is
:class:`app.services.authorization.authorization_service.AuthorizationService`.

Scope discipline for this phase: RBAC resolution (User → Roles →
Permissions) and permission/role checks only. No REST API, no FastAPI
dependency, no HTTP middleware, no authentication concerns (login, JWT,
sessions) — those belong to other phases/modules entirely.
"""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from app.services.identity.dtos import PermissionResponse, RoleResponse
from app.services.interfaces import IService


@runtime_checkable
class IAuthorizationService(IService, Protocol):
    """Contract for RBAC resolution and permission/role checks.

    All grants are resolved strictly from the database (``user_roles`` →
    ``roles`` → ``role_permissions`` → ``permissions``) — nothing here ever
    grants a role or permission that is not represented by an actual row.
    """

    async def get_user_roles(self, user_id: uuid.UUID) -> list[RoleResponse]:
        """Return every role assigned to ``user_id``.

        An unknown user (or one with no role assignments) resolves to an
        empty list — never an error, and never a default/implicit role.
        """
        ...

    async def get_user_permissions(
        self, user_id: uuid.UUID, *, roles: list[RoleResponse] | None = None
    ) -> list[PermissionResponse]:
        """Return the de-duplicated union of permissions across every role
        assigned to ``user_id``.

        If two of the user's roles both grant the same permission, it
        appears exactly once in the result. ``roles`` lets a caller that
        already resolved the user's roles pass them in to skip a redundant
        lookup; omit it to resolve roles internally.
        """
        ...

    async def has_role(self, user_id: uuid.UUID, role_name: str) -> bool:
        """Return whether ``user_id`` has the role named ``role_name``.

        Raises ``RoleNotFoundError`` if no such role exists in the system at
        all (a caller/configuration error, distinct from the user simply not
        having it).
        """
        ...

    async def has_permission(self, user_id: uuid.UUID, permission_code: str) -> bool:
        """Return whether ``user_id`` holds the permission ``permission_code``
        (via any of their roles).

        Raises ``PermissionNotFoundError`` if no such permission exists in
        the system at all.
        """
        ...

    async def require_role(self, user_id: uuid.UUID, role_name: str) -> None:
        """Raise ``ForbiddenError`` unless ``user_id`` has ``role_name``.

        Raises ``RoleNotFoundError`` if the role concept itself does not
        exist. Never raises for a role the user simply lacks — that case is
        ``ForbiddenError``, not a "not found".
        """
        ...

    async def require_permission(
        self, user_id: uuid.UUID, permission_code: str
    ) -> None:
        """Raise ``ForbiddenError`` unless ``user_id`` holds
        ``permission_code``.

        Raises ``PermissionNotFoundError`` if the permission concept itself
        does not exist.
        """
        ...
