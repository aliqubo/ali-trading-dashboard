"""Order repository (Trading domain).

Data-access for the ``orders`` table. Inherits the generic CRUD/query surface
from :class:`BaseRepository` and adds domain-scoped reads (BACKEND_SPEC §6.3).

No business logic — no order matching, no trading engine, no PnL. Persistence
and querying only; ``status`` values are read from stored columns, not decided
here.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select

from app.models import Order
from app.repositories.base import BaseRepository
from app.repositories.types import Pagination, PaginationResult

# Statuses that represent an order still working in the book. These mirror the
# stored enum values in DATABASE_DESIGN.md; no policy is derived from them.
_OPEN_STATUSES = ("pending", "open", "partially_filled")


class OrderRepository(BaseRepository[Order]):
    """Repository for :class:`Order`."""

    model = Order
    filterable_fields = frozenset(
        {"user_id", "symbol_id", "strategy_id", "status", "side", "order_type"}
    )
    sortable_fields = frozenset({"created_at", "submitted_at", "status"})

    async def get_open_orders(self, user_id: object) -> list[Order]:
        """Return a user's orders whose stored status is still working."""
        stmt = (
            select(Order)
            .where(
                Order.user_id == user_id,
                Order.status.in_(_OPEN_STATUSES),
            )
            .order_by(Order.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_orders_by_status(self, user_id: object, status: str) -> list[Order]:
        """Return a user's orders filtered by a single stored status value."""
        stmt = (
            select(Order)
            .where(Order.user_id == user_id, Order.status == status)
            .order_by(Order.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_orders_for_user(
        self, user_id: object, pagination: Pagination | None = None
    ) -> PaginationResult[Order]:
        """Return a paginated page of a user's orders, newest first."""
        page = pagination or Pagination()
        limit = min(max(page.limit, 1), 200)
        offset = max(page.offset, 0)
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit + 1)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        has_more = len(rows) > limit
        return PaginationResult(
            items=rows[:limit], limit=limit, offset=offset, has_more=has_more
        )

    async def get_orders_between(
        self,
        user_id: object,
        start: datetime,
        end: datetime,
    ) -> list[Order]:
        """Return a user's orders created within ``[start, end]`` (ascending)."""
        stmt = (
            select(Order)
            .where(
                Order.user_id == user_id,
                Order.created_at >= start,
                Order.created_at <= end,
            )
            .order_by(Order.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_client_order_id(self, client_order_id: str) -> Order | None:
        """Return the order with the given client order id, or ``None``."""
        stmt = select(Order).where(Order.client_order_id == client_order_id).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_ids(self, ids: Sequence[object]) -> list[Order]:
        """Return orders matching the given ids."""
        if not ids:
            return []
        stmt = select(Order).where(Order.id.in_(list(ids)))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
