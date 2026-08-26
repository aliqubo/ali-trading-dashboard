"""Role-permission grant repository (Identity domain).

Reconstructed MVP scaffolding — original source unavailable. This file is
absent from every source archive; it is rebuilt here following the same
BaseRepository pattern as the archived identity repositories, and the two
query methods (`get_for_role`, `get_for_permission`) documented for this
repository in PHASE_2_3_2_REPORT.md. See RECOVERY_MANIFEST.md.
"""

from __future__ import annotations

from sqlalchemy import select

from app.models import RolePermission
from app.repositories.base import BaseRepository


class RolePermissionRepository(BaseRepository[RolePermission]):
    """Repository for :class:`RolePermission`."""

    model = RolePermission
    filterable_fields = frozenset({"role_id", "permission_id"})
    sortable_fields = frozenset({"created_at"})

    async def get_for_role(self, role_id: object) -> list[RolePermission]:
        """Return every permission-grant row for the given role."""
        stmt = select(RolePermission).where(RolePermission.role_id == role_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_permission(self, permission_id: object) -> list[RolePermission]:
        """Return every role-grant row for the given permission."""
        stmt = select(RolePermission).where(
            RolePermission.permission_id == permission_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
