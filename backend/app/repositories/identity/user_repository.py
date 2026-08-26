"""User repository (Identity domain).

Data-access for the ``users`` table. Inherits the generic CRUD/query surface
from :class:`BaseRepository` and adds a few explicit, domain-scoped queries
(BACKEND_SPEC §6.3).

No business logic, no validation, no auth, no password hashing — persistence
and querying only.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select

from app.models import User
from app.repositories.base import BaseRepository
from app.repositories.types import Pagination, PaginationResult


class UserRepository(BaseRepository[User]):
    """Repository for :class:`User`."""

    model = User
    filterable_fields = frozenset(
        {
            "email",
            "username",
            "status",
            "is_email_verified",
            "two_factor_enabled",
            "locale",
        }
    )
    sortable_fields = frozenset(
        {"email", "username", "created_at", "updated_at", "last_login_at"}
    )

    async def get_by_email(self, email: str) -> User | None:
        """Return the user with the given email, or ``None``."""
        stmt = select(User).where(User.email == email).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_username(self, username: str) -> User | None:
        """Return the user with the given username, or ``None``."""
        stmt = select(User).where(User.username == username).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_active_users(
        self, pagination: Pagination | None = None
    ) -> PaginationResult[User]:
        """Return a page of users whose status is ``active``.

        ``active`` here is the stored status value, not an interpretation — no
        business rule is applied.
        """
        page = pagination or Pagination()
        limit = min(max(page.limit, 1), 200)
        offset = max(page.offset, 0)
        stmt = (
            select(User)
            .where(User.status == "active")
            .order_by(User.created_at.desc())
            .limit(limit + 1)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        has_more = len(rows) > limit
        return PaginationResult(
            items=rows[:limit],
            limit=limit,
            offset=offset,
            has_more=has_more,
        )

    async def search_users(
        self, term: str, pagination: Pagination | None = None
    ) -> PaginationResult[User]:
        """Return users whose email, username or full name matches ``term``.

        A simple case-insensitive substring match — no ranking or business
        logic.
        """
        page = pagination or Pagination()
        limit = min(max(page.limit, 1), 200)
        offset = max(page.offset, 0)
        pattern = f"%{term}%"
        stmt = (
            select(User)
            .where(
                User.email.ilike(pattern)
                | User.username.ilike(pattern)
                | User.full_name.ilike(pattern)
            )
            .order_by(User.created_at.desc())
            .limit(limit + 1)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        has_more = len(rows) > limit
        return PaginationResult(
            items=rows[:limit],
            limit=limit,
            offset=offset,
            has_more=has_more,
        )

    async def get_by_ids(self, ids: Sequence[object]) -> list[User]:
        """Return users matching the given ids (order not guaranteed)."""
        if not ids:
            return []
        stmt = select(User).where(User.id.in_(list(ids)))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
