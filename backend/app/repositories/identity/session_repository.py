"""Session repository (Identity domain).

Data-access for the ``sessions`` table. No business logic — the methods here are
plain persistence operations. Deciding *when* to revoke a session is a service
concern; this repository only performs the write.
"""

from __future__ import annotations

from sqlalchemy import func, select, update

from app.models import Session
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    """Repository for :class:`Session`."""

    model = Session
    filterable_fields = frozenset({"user_id", "is_active"})
    sortable_fields = frozenset({"created_at", "expires_at", "last_seen_at"})

    async def get_active_sessions(self, user_id: object) -> list[Session]:
        """Return a user's sessions currently flagged active and not expired.

        ``active`` and ``not expired`` are read directly from stored columns; no
        policy is applied here.
        """
        stmt = (
            select(Session)
            .where(
                Session.user_id == user_id,
                Session.is_active.is_(True),
                Session.expires_at > func.now(),
            )
            .order_by(Session.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def revoke_all_user_sessions(self, user_id: object) -> int:
        """Mark all of a user's sessions inactive and stamp ``revoked_at``.

        Returns the number of rows affected. This is a bulk persistence update;
        it flushes but does not commit (the service owns the transaction).
        """
        stmt = (
            update(Session)
            .where(Session.user_id == user_id, Session.is_active.is_(True))
            .values(is_active=False, revoked_at=func.now())
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return int(result.rowcount or 0)  # type: ignore[attr-defined]
