"""Trade repository (Trading domain).

Data-access for the ``trades`` table. No business logic — the "profitable" and
"losing" queries read the *stored* ``net_pnl`` column; they do not compute PnL.
No risk, portfolio or AI logic here.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.models import Trade
from app.repositories.base import BaseRepository
from app.repositories.types import Pagination, PaginationResult


class TradeRepository(BaseRepository[Trade]):
    """Repository for :class:`Trade`."""

    model = Trade
    filterable_fields = frozenset(
        {"user_id", "symbol_id", "position_id", "strategy_id", "status", "side"}
    )
    sortable_fields = frozenset({"entry_at", "exit_at", "created_at"})

    async def get_closed_trades(
        self, user_id: object, pagination: Pagination | None = None
    ) -> PaginationResult[Trade]:
        """Return a page of a user's trades whose stored status is ``closed``."""
        page = pagination or Pagination()
        limit = min(max(page.limit, 1), 200)
        offset = max(page.offset, 0)
        stmt = (
            select(Trade)
            .where(Trade.user_id == user_id, Trade.status == "closed")
            .order_by(Trade.exit_at.desc())
            .limit(limit + 1)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        has_more = len(rows) > limit
        return PaginationResult(
            items=rows[:limit], limit=limit, offset=offset, has_more=has_more
        )

    async def get_profitable_trades(self, user_id: object) -> list[Trade]:
        """Return a user's trades whose stored ``net_pnl`` is greater than 0.

        This reads the persisted value; it performs no PnL calculation.
        """
        stmt = (
            select(Trade)
            .where(Trade.user_id == user_id, Trade.net_pnl > 0)
            .order_by(Trade.exit_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_losing_trades(self, user_id: object) -> list[Trade]:
        """Return a user's trades whose stored ``net_pnl`` is less than 0.

        This reads the persisted value; it performs no PnL calculation.
        """
        stmt = (
            select(Trade)
            .where(Trade.user_id == user_id, Trade.net_pnl < 0)
            .order_by(Trade.exit_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_user(self, user_id: object) -> list[Trade]:
        """Return all of a user's trades, newest first by entry time."""
        stmt = (
            select(Trade)
            .where(Trade.user_id == user_id)
            .order_by(Trade.entry_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_trades_between(
        self, user_id: object, start: datetime, end: datetime
    ) -> list[Trade]:
        """Return a user's trades entered within ``[start, end]`` (ascending)."""
        stmt = (
            select(Trade)
            .where(
                Trade.user_id == user_id,
                Trade.entry_at >= start,
                Trade.entry_at <= end,
            )
            .order_by(Trade.entry_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
