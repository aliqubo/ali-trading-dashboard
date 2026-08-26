"""Identity domain repositories.

Data-access repositories for the Identity domain tables. Each inherits the
generic :class:`BaseRepository` and adds only explicit, domain-scoped queries.
No business logic, validation, authentication or authorization here.

MVP Phase 2 note — `role_repository.py`, `permission_repository.py`,
`user_role_repository.py`, `role_permission_repository.py` are reconstructed
for this MVP (absent from every source archive, needed for RBAC to
function); the other four files are restored verbatim from files6.zip. See
RECOVERY_MANIFEST.md.
"""

from __future__ import annotations

from app.repositories.identity.api_key_repository import ApiKeyRepository
from app.repositories.identity.permission_repository import PermissionRepository
from app.repositories.identity.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.repositories.identity.role_permission_repository import (
    RolePermissionRepository,
)
from app.repositories.identity.role_repository import RoleRepository
from app.repositories.identity.session_repository import SessionRepository
from app.repositories.identity.user_repository import UserRepository
from app.repositories.identity.user_role_repository import UserRoleRepository

__all__ = [
    "UserRepository",
    "RoleRepository",
    "PermissionRepository",
    "UserRoleRepository",
    "RolePermissionRepository",
    "SessionRepository",
    "RefreshTokenRepository",
    "ApiKeyRepository",
]
