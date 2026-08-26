"""User-role assignment repository (Identity domain).

Reconstructed MVP scaffolding — original source unavailable. This file is
absent from every source archive; it is rebuilt here following the same
BaseRepository pattern as the archived identity repositories, and the two
query methods (`get_for_user`, `get_for_role`) documented for this
repository in PHASE_2_3_2_REPORT.md. See RECOVERY_MANIFEST.md.
"""

from __future__ import annotations

from sqlalchemy import select

from app.models import UserRole
from app.repositories.base import BaseRepository


class UserRoleRepository(BaseRepository[UserRole]):
    """Repository for :class:`UserRole`."""

    model = UserRole
    filterable_fields = frozenset({"user_id", "role_id"})
    sortable_fields = frozenset({"assigned_at"})

    async def get_for_user(self, user_id: object) -> list[UserRole]:
        """Return every role-assignment row for the given user."""
        stmt = select(UserRole).where(UserRole.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_role(self, role_id: object) -> list[UserRole]:
        """Return every user-assignment row for the given role."""
        stmt = select(UserRole).where(UserRole.role_id == role_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
