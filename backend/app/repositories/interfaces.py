"""Repository and Unit-of-Work interfaces.

Structural interfaces (typing Protocols) that support Interface Segregation and
dependency inversion (BACKEND_SPEC §16.3, ARCHITECTURE.md §2). Concrete domain
repositories depend on ``IRepository``; :class:`app.repositories.unit_of_work.
SqlAlchemyUnitOfWork` implements ``IUnitOfWork``.

- ``IRepository`` describes the generic CRUD/query surface of the base
  repository.
- ``IUnitOfWork`` is the interface for the Unit-of-Work pattern (BACKEND_SPEC
  §5.5): a single transaction, under one session, that the service layer opens,
  uses, then commits or rolls back as a whole.

Structure only — no logic.
"""

from __future__ import annotations

from collections.abc import Sequence
from types import TracebackType
from typing import Any, Protocol, TypeVar, runtime_checkable

from app.repositories.types import (
    Filter,
    Pagination,
    PaginationResult,
    Sort,
)

TModel = TypeVar("TModel")


@runtime_checkable
class IRepository(Protocol[TModel]):
    """Generic repository interface (read/write surface).

    Implementations translate these calls into safe, parameterized database
    operations. They contain no business logic and do not manage transactions
    (BACKEND_SPEC §6.1).
    """

    async def get_by_id(self, entity_id: Any) -> TModel | None: ...

    async def get_one(
        self, filters: Sequence[Filter] | None = ...
    ) -> TModel | None: ...

    async def get_many(
        self,
        filters: Sequence[Filter] | None = ...,
        sorts: Sequence[Sort] | None = ...,
        pagination: Pagination | None = ...,
    ) -> PaginationResult[TModel]: ...

    async def exists(self, filters: Sequence[Filter] | None = ...) -> bool: ...

    async def count(self, filters: Sequence[Filter] | None = ...) -> int: ...

    async def create(self, data: dict[str, Any]) -> TModel: ...

    async def create_many(self, data: Sequence[dict[str, Any]]) -> list[TModel]: ...

    async def update(self, entity_id: Any, data: dict[str, Any]) -> TModel: ...

    async def delete(self, entity_id: Any) -> None: ...


@runtime_checkable
class IUnitOfWork(Protocol):
    """Unit-of-Work interface (BACKEND_SPEC §5.5).

    Groups repository operations into a single transaction under one session.
    The service layer opens the unit of work (typically via ``async with``),
    performs operations through the registered repositories, then commits or
    rolls back as a whole. Implementations must not let a repository open or
    commit its own transaction — the unit of work (on the service's behalf)
    owns it.
    """

    async def __aenter__(self) -> IUnitOfWork: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None: ...

    async def begin(self) -> None:
        """Start the underlying session/transaction explicitly."""
        ...

    async def commit(self) -> None:
        """Commit the current transaction."""
        ...

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        ...

    async def flush(self) -> None:
        """Flush pending changes to the database without committing."""
        ...

    async def refresh(self, instance: Any) -> None:
        """Reload an instance's attributes from the database."""
        ...

    async def close(self) -> None:
        """Close the underlying session, releasing its connection."""
        ...
