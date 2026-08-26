"""Execution repository (Trading domain).

Data-access for the ``executions`` table. No business logic — fills are read and
written as-is; no PnL or fee aggregation here.
"""

from __future__ import annotations

from sqlalchemy import select

from app.models import Execution, Order
from app.repositories.base import BaseRepository


class ExecutionRepository(BaseRepository[Execution]):
    """Repository for :class:`Execution`."""

    model = Execution
    filterable_fields = frozenset({"order_id", "symbol_id", "liquidity"})
    sortable_fields = frozenset({"executed_at", "created_at"})

    async def get_for_order(self, order_id: object) -> list[Execution]:
        """Return all executions (fills) for an order, oldest first."""
        stmt = (
            select(Execution)
            .where(Execution.order_id == order_id)
            .order_by(Execution.executed_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_for_user(self, user_id: object, limit: int = 50) -> list[Execution]:
        """Return a user's most recent executions, newest first.

        ``executions`` has no ``user_id`` column of its own — ownership is
        only reachable by joining through the owning ``orders`` row.
        """
        stmt = (
            select(Execution)
            .join(Order, Execution.order_id == Order.id)
            .where(Order.user_id == user_id)
            .order_by(Execution.executed_at.desc())
            .limit(min(max(limit, 1), 200))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_external_exec_id(self, external_exec_id: str) -> Execution | None:
        """Return the execution with the given external id, or ``None``."""
        stmt = (
            select(Execution)
            .where(Execution.external_exec_id == external_exec_id)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
