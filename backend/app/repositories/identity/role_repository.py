"""Role repository (Identity domain).

Reconstructed MVP scaffolding — original source unavailable. This file is
absent from every source archive; it is rebuilt here following the same
BaseRepository pattern as the archived identity repositories
(user_repository.py, session_repository.py, etc.) and the single query
method (`get_by_name`) documented for this repository in
PHASE_2_3_2_REPORT.md. See RECOVERY_MANIFEST.md.
"""

from __future__ import annotations

from sqlalchemy import select

from app.models import Role
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """Repository for :class:`Role`."""

    model = Role
    filterable_fields = frozenset({"name", "is_system"})
    sortable_fields = frozenset({"name", "created_at"})

    async def get_by_name(self, name: str) -> Role | None:
        """Return the role with the given name, or ``None``."""
        stmt = select(Role).where(Role.name == name).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()
