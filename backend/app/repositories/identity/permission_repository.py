"""Permission repository (Identity domain).

Reconstructed MVP scaffolding — original source unavailable. This file is
absent from every source archive; it is rebuilt here following the same
BaseRepository pattern as the archived identity repositories, and the single
query method (`get_by_code`) documented for this repository in
PHASE_2_3_2_REPORT.md. See RECOVERY_MANIFEST.md.
"""

from __future__ import annotations

from sqlalchemy import select

from app.models import Permission
from app.repositories.base import BaseRepository


class PermissionRepository(BaseRepository[Permission]):
    """Repository for :class:`Permission`."""

    model = Permission
    filterable_fields = frozenset({"code", "resource", "action"})
    sortable_fields = frozenset({"code", "created_at"})

    async def get_by_code(self, code: str) -> Permission | None:
        """Return the permission with the given code, or ``None``."""
        stmt = select(Permission).where(Permission.code == code).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()
