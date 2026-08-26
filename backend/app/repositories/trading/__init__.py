"""Trading domain repositories.

Data-access repositories for the Trading domain tables. Each inherits the
generic :class:`BaseRepository` and adds only explicit, domain-scoped queries.
No business logic, trading/risk engine, PnL, indicators, AI or portfolio maths
here.

MVP Phase 2 patch — PositionHistoryRepository, TradeNoteRepository,
TradeScreenshotRepository are absent from every source archive and are not
exported here (see RECOVERY_MANIFEST.md). OrderHistoryRepository
(files9.zip) is added: its file exists but was never exported by the
archived version of this __init__.py.

MVP Phase 4 patch — TradeJournalRepository removed. Its file exists in this
package (trade_journal_repository.py) but depends on TradeJournal/TradeNote
models from app/models/trade_journal.py, which is absent from every archive
(confirmed by a dependency audit — see RECOVERY_MANIFEST.md). The file
itself is left on disk, unimported, in case trade_journal.py is
reconstructed later.
"""

from __future__ import annotations

from app.repositories.trading.execution_repository import ExecutionRepository
from app.repositories.trading.order_history_repository import (
    OrderHistoryRepository,
)
from app.repositories.trading.order_repository import OrderRepository
from app.repositories.trading.position_repository import PositionRepository
from app.repositories.trading.trade_repository import TradeRepository

__all__ = [
    "OrderRepository",
    "OrderHistoryRepository",
    "ExecutionRepository",
    "PositionRepository",
    "TradeRepository",
]
