"""Authorization service (RBAC).

Concrete implementation of :class:`IAuthorizationService`. Resolves grants
strictly by walking the existing model relationships — ``user_roles`` →
``roles`` → ``role_permissions`` → ``permissions`` — through repository
methods only. Never touches a SQLAlchemy ``Session`` directly (only
``self._uow.<repository>`` calls); never grants a role or permission that is
not represented by an actual database row; never special-cases any
user/email/username as implicitly privileged.

Security notes (this phase's explicit rules):
- No default/implicit grants: an unknown user, or a user with no role rows,
  resolves to an empty role/permission set — never an error, never a
  fallback "admin" or "default" role.
- No client-supplied data determines a grant: every check re-queries the
  database via ``user_id`` (an already-established internal identifier);
  nothing here accepts or trusts a caller-asserted list of roles/
  permissions.
- ``ForbiddenError`` (reused from ``app.core.exceptions``, defined in Phase
  1 — not redefined here) is always raised with its bare, generic default
  message; the specific role/permission that was checked is written only to
  the internal logger, never into the exception's externally-visible
  message or details, per this phase's "no sensitive RBAC structure in
  external error messages" rule.
- The logger records only ``user_id``, ``role``/``permission_code``, and
  event type — never a secret, token, or password (none exist in this
  domain regardless).

No caching layer (Redis or otherwise) is introduced: nothing in the frozen
reference documents mandates an authorization cache for this phase, so none
was built, per the explicit instruction not to invent one without a
documented requirement.
"""

from __future__ import annotations

import logging
import uuid

from app.core.exceptions import ForbiddenError
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork
from app.services.authorization.exceptions import (
    PermissionNotFoundError,
    RoleNotFoundError,
)
from app.services.base import BaseService
from app.services.identity.dtos import PermissionResponse, RoleResponse


class AuthorizationService(BaseService):
    """Resolves RBAC grants and enforces role/permission checks."""

    def __init__(self, uow: SqlAlchemyUnitOfWork, logger: logging.Logger) -> None:
        super().__init__(uow)
        self._uow: SqlAlchemyUnitOfWork = uow
        self._logger = logger

    async def get_user_roles(self, user_id: uuid.UUID) -> list[RoleResponse]:
        """Return every role assigned to ``user_id`` (empty if none/unknown)."""
        user = await self._uow.users.get_by_id(user_id)
        if user is None:
            return []

        assignments = await self._uow.user_roles.get_for_user(user_id)
        roles: list[RoleResponse] = []
        seen_role_ids: set[uuid.UUID] = set()
        for assignment in assignments:
            if assignment.role_id in seen_role_ids:
                continue
            seen_role_ids.add(assignment.role_id)
            role = await self._uow.roles.get_by_id(assignment.role_id)
            if role is not None:
                roles.append(RoleResponse.model_validate(role))
        return roles

    async def get_user_permissions(
        self, user_id: uuid.UUID, *, roles: list[RoleResponse] | None = None
    ) -> list[PermissionResponse]:
        """Return the de-duplicated union of permissions across the user's
        roles.

        ``roles`` lets a caller that already resolved the user's roles (e.g.
        via ``get_user_roles()``) pass them in directly, avoiding a second,
        redundant role-resolution query; omit it to resolve roles internally
        as before.
        """
        if roles is None:
            roles = await self.get_user_roles(user_id)

        permissions: list[PermissionResponse] = []
        seen_permission_ids: set[uuid.UUID] = set()
        for role in roles:
            grants = await self._uow.role_permissions.get_for_role(role.id)
            for grant in grants:
                if grant.permission_id in seen_permission_ids:
                    continue
                seen_permission_ids.add(grant.permission_id)
                permission = await self._uow.permissions.get_by_id(grant.permission_id)
                if permission is not None:
                    permissions.append(PermissionResponse.model_validate(permission))
        return permissions

    async def has_role(self, user_id: uuid.UUID, role_name: str) -> bool:
        """Return whether ``user_id`` has the role named ``role_name``."""
        role = await self._uow.roles.get_by_name(role_name)
        if role is None:
            raise RoleNotFoundError()

        roles = await self.get_user_roles(user_id)
        return any(r.id == role.id for r in roles)

    async def has_permission(self, user_id: uuid.UUID, permission_code: str) -> bool:
        """Return whether ``user_id`` holds ``permission_code`` via any role."""
        permission = await self._uow.permissions.get_by_code(permission_code)
        if permission is None:
            raise PermissionNotFoundError()

        permissions = await self.get_user_permissions(user_id)
        return any(p.id == permission.id for p in permissions)

    async def require_role(self, user_id: uuid.UUID, role_name: str) -> None:
        """Raise ``ForbiddenError`` unless ``user_id`` has ``role_name``."""
        if not await self.has_role(user_id, role_name):
            self._logger.warning(
                "role check denied",
                extra={"user_id": str(user_id), "role": role_name},
            )
            raise ForbiddenError()

    async def require_permission(
        self, user_id: uuid.UUID, permission_code: str
    ) -> None:
        """Raise ``ForbiddenError`` unless ``user_id`` holds
        ``permission_code``."""
        if not await self.has_permission(user_id, permission_code):
            self._logger.warning(
                "permission check denied",
                extra={
                    "user_id": str(user_id),
                    "permission_code": permission_code,
                },
            )
            raise ForbiddenError()
