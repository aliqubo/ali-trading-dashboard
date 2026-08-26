"""Position repository (Trading domain).

Data-access for the ``positions`` table. No business logic — position sizing,
PnL and risk are out of scope; ``status`` is read from the stored column.
"""

from __future__ import annotations

from sqlalchemy import select

from app.models import Position
from app.repositories.base import BaseRepository


class PositionRepository(BaseRepository[Position]):
    """Repository for :class:`Position`."""

    model = Position
    filterable_fields = frozenset({"user_id", "symbol_id", "status", "side"})
    sortable_fields = frozenset({"opened_at", "created_at"})

    async def get_open_positions(self, user_id: object) -> list[Position]:
        """Return a user's positions whose stored status is ``open``."""
        stmt = (
            select(Position)
            .where(Position.user_id == user_id, Position.status == "open")
            .order_by(Position.opened_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_symbol(self, user_id: object, symbol_id: object) -> list[Position]:
        """Return a user's positions for a given symbol."""
        stmt = (
            select(Position)
            .where(
                Position.user_id == user_id,
                Position.symbol_id == symbol_id,
            )
            .order_by(Position.opened_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_user(self, user_id: object) -> list[Position]:
        """Return all of a user's positions, newest first."""
        stmt = (
            select(Position)
            .where(Position.user_id == user_id)
            .order_by(Position.opened_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_open_position_for_symbol(
        self, user_id: object, symbol_id: object
    ) -> Position | None:
        """Return the user's single open position for a symbol, if any.

        The partial unique index on ``positions`` guarantees at most one open
        position per user+symbol; this simply reads it.
        """
        stmt = (
            select(Position)
            .where(
                Position.user_id == user_id,
                Position.symbol_id == symbol_id,
                Position.status == "open",
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
