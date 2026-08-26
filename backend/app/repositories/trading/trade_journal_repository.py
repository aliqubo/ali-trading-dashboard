"""Trade journal repository (Trading domain).

Data-access for the ``trade_journal`` table. No business logic.
"""

from __future__ import annotations

from sqlalchemy import select

from app.models import TradeJournal, TradeNote
from app.repositories.base import BaseRepository


class TradeJournalRepository(BaseRepository[TradeJournal]):
    """Repository for :class:`TradeJournal`."""

    model = TradeJournal
    filterable_fields = frozenset({"user_id", "trade_id", "emotion", "rating"})
    sortable_fields = frozenset({"created_at", "updated_at"})

    async def get_for_user(self, user_id: object) -> list[TradeJournal]:
        """Return all journal entries for a user, newest first."""
        stmt = (
            select(TradeJournal)
            .where(TradeJournal.user_id == user_id)
            .order_by(TradeJournal.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_trade(self, trade_id: object) -> TradeJournal | None:
        """Return the journal entry linked to a trade, if any."""
        stmt = select(TradeJournal).where(TradeJournal.trade_id == trade_id).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_trade_notes(self, journal_id: object) -> list[TradeNote]:
        """Return all notes attached to a journal entry, oldest first."""
        stmt = (
            select(TradeNote)
            .where(TradeNote.journal_id == journal_id)
            .order_by(TradeNote.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
