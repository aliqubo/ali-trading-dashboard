"""SQLAlchemy Unit-of-Work implementation (BACKEND_SPEC §5.5).

Provides :class:`SqlAlchemyUnitOfWork`, the concrete implementation of
:class:`app.repositories.interfaces.IUnitOfWork`. It owns a single
``AsyncSession`` and exposes every available domain repository as a
lazily-created, cached property bound to that session — so ``uow.users``,
``uow.orders``, etc. all operate within the same transaction.

Design constraints (BACKEND_SPEC §5.5 / §6.1):
- The unit of work owns the transaction. Repositories never open or commit
  their own transactions; they only ``flush`` (see :mod:`app.repositories.base`).
- ``commit``/``rollback`` are explicit — nothing commits automatically except
  a clean ``async with`` exit (see below), and any exception inside the block
  triggers an automatic rollback.
- This module contains no business logic, no service orchestration, no auth,
  no API/WebSocket/event code.

MVP Phase 2 patch — the archived version of this file (files10.zip /
files11.zip) registers all 55 repositories across every domain. This MVP
only restores Identity (including the 4 RBAC repositories reconstructed for
this sprint) and Trading, so this version registers only those properties.
See RECOVERY_MANIFEST.md for the full list of omitted domains.

MVP Phase 4 patch — the `trade_journal` property and its TradeJournalRepository
import are removed. A dependency audit confirmed TradeJournalRepository's
import of TradeJournal/TradeNote from app.models fails at import time,
because app/models/trade_journal.py is absent from every archive. See
RECOVERY_MANIFEST.md.

Usage::

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        user = await uow.users.create({...})
        order = await uow.orders.create({"user_id": user.id, ...})
        await uow.commit()
    # Falling out of the block without an explicit commit rolls back;
    # raising an exception inside the block also rolls back.
"""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from typing import Any, TypeVar, cast

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.identity import (
    ApiKeyRepository,
    PermissionRepository,
    RefreshTokenRepository,
    RolePermissionRepository,
    RoleRepository,
    SessionRepository,
    UserRepository,
    UserRoleRepository,
)
from app.repositories.interfaces import IUnitOfWork
from app.repositories.trading import (
    ExecutionRepository,
    OrderHistoryRepository,
    OrderRepository,
    PositionRepository,
    TradeRepository,
)

TRepo = TypeVar("TRepo")


class SqlAlchemyUnitOfWork:
    """Concrete Unit of Work backed by a single SQLAlchemy ``AsyncSession``.

    Structurally implements :class:`app.repositories.interfaces.IUnitOfWork`
    (a ``Protocol``, matched by shape rather than explicit inheritance — the
    idiomatic way to satisfy a ``typing.Protocol``; ``isinstance`` checks still
    work because the protocol is ``@runtime_checkable``).

    One session is created per unit-of-work instance (via the injected
    ``session_factory``) and shared by every repository property, so all
    operations performed through ``uow.<repo>`` participate in the same
    transaction until :meth:`commit` or :meth:`rollback` is called.

    Repository instances are created lazily on first access and cached for the
    lifetime of the unit of work — accessing ``uow.users`` twice returns the
    same ``UserRepository`` instance bound to the same session.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._repo_cache: dict[str, Any] = {}

    # --- Session lifecycle --------------------------------------------

    @property
    def session(self) -> AsyncSession:
        """Return the active session, creating one on first access."""
        if self._session is None:
            self._session = self._session_factory()
        return self._session

    async def begin(self) -> None:
        """Start the underlying session explicitly.

        Accessing :attr:`session` already creates it lazily; this method makes
        session creation explicit for callers that want to start the unit of
        work before touching any repository.
        """
        _ = self.session

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        await self.session.rollback()

    async def flush(self) -> None:
        """Flush pending changes to the database without committing."""
        await self.session.flush()

    async def refresh(self, instance: Any) -> None:
        """Reload an instance's attributes from the database."""
        await self.session.refresh(instance)

    async def close(self) -> None:
        """Close the underlying session and release its connection."""
        if self._session is not None:
            await self._session.close()
            self._session = None
            self._repo_cache.clear()

    # --- Async context manager -----------------------------------------

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        await self.begin()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None:
        """Roll back any uncommitted work, then always close the session.

        This covers both cases uniformly:
        - An exception propagated out of the ``async with`` block: the
          transaction is rolled back (automatic rollback on failure).
        - The block exited cleanly but the caller never called
          :meth:`commit`: any pending changes are discarded rather than
          silently persisted (commit is always explicit, never implicit).

        If the caller already called :meth:`commit` before exiting, that
        transaction has already ended; the rollback here is then a safe
        no-op on the next (empty) transaction. The session is always closed
        afterwards to release its connection, regardless of outcome.
        """
        try:
            await self.rollback()
        finally:
            await self.close()
        return None

    # --- Repository registry (lazy, cached, one per session) -----------

    def _get(self, key: str, factory: Callable[[AsyncSession], TRepo]) -> TRepo:
        if key not in self._repo_cache:
            self._repo_cache[key] = factory(self.session)
        return cast(TRepo, self._repo_cache[key])

    # Identity domain
    @property
    def users(self) -> UserRepository:
        return self._get("users", UserRepository)

    @property
    def roles(self) -> RoleRepository:
        return self._get("roles", RoleRepository)

    @property
    def permissions(self) -> PermissionRepository:
        return self._get("permissions", PermissionRepository)

    @property
    def user_roles(self) -> UserRoleRepository:
        return self._get("user_roles", UserRoleRepository)

    @property
    def role_permissions(self) -> RolePermissionRepository:
        return self._get("role_permissions", RolePermissionRepository)

    @property
    def sessions(self) -> SessionRepository:
        return self._get("sessions", SessionRepository)

    @property
    def refresh_tokens(self) -> RefreshTokenRepository:
        return self._get("refresh_tokens", RefreshTokenRepository)

    @property
    def api_keys(self) -> ApiKeyRepository:
        return self._get("api_keys", ApiKeyRepository)

    # Trading domain
    @property
    def orders(self) -> OrderRepository:
        return self._get("orders", OrderRepository)

    @property
    def order_history(self) -> OrderHistoryRepository:
        return self._get("order_history", OrderHistoryRepository)

    @property
    def executions(self) -> ExecutionRepository:
        return self._get("executions", ExecutionRepository)

    @property
    def positions(self) -> PositionRepository:
        return self._get("positions", PositionRepository)

    @property
    def trades(self) -> TradeRepository:
        return self._get("trades", TradeRepository)


# Runtime proof that the class shape satisfies IUnitOfWork (the protocol is
# @runtime_checkable). This assertion runs at import time and would fail
# loudly if a required method/attribute were missing or misnamed.
assert isinstance(
    SqlAlchemyUnitOfWork(async_sessionmaker()), IUnitOfWork
), "SqlAlchemyUnitOfWork must structurally satisfy IUnitOfWork"
