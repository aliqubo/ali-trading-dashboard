"""Order history repository (Trading domain).

Data-access for the ``order_history`` table. No business logic — status change
rows are read and written as-is; no order lifecycle logic here.
"""

from __future__ import annotations

from sqlalchemy import select

from app.models import OrderHistory
from app.repositories.base import BaseRepository


class OrderHistoryRepository(BaseRepository[OrderHistory]):
    """Repository for :class:`OrderHistory`."""

    model = OrderHistory
    filterable_fields = frozenset({"order_id", "previous_status", "new_status"})
    sortable_fields = frozenset({"created_at"})

    async def get_for_order(self, order_id: object) -> list[OrderHistory]:
        """Return all status-change rows for an order, oldest first."""
        stmt = (
            select(OrderHistory)
            .where(OrderHistory.order_id == order_id)
            .order_by(OrderHistory.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
