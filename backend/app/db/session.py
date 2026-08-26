"""Async database engine and session management (ARCHITECTURE.md §6).

Reconstructed MVP scaffolding — original source unavailable.

Owns the process-level async engine and session factory. `init_engine` is
called once at application startup (see app/main.py's lifespan) and
`dispose_engine` at shutdown. `get_session` is a FastAPI dependency yielding
a request-scoped session.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

if TYPE_CHECKING:
    from app.core.config import Settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(settings: Settings) -> None:
    """Create the module-level async engine and session factory."""
    global _engine, _session_factory
    _engine = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def dispose_engine() -> None:
    """Dispose the engine and clear module state."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory. Raises if init_engine() was not called."""
    if _session_factory is None:
        msg = "Database engine not initialised; call init_engine() first."
        raise RuntimeError(msg)
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped AsyncSession."""
    factory = get_session_factory()
    async with factory() as session:
        yield session
