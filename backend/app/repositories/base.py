"""Generic base repository (BACKEND_SPEC §6).

A reusable, typed CRUD/query surface over a single ORM model. Domain
repositories (added in later phases) subclass this and add their own explicit
queries.

Design constraints enforced here (BACKEND_SPEC §6.1):
- The repository receives an ``AsyncSession`` by injection and never opens or
  commits transactions — the service layer owns the transaction. Write methods
  ``flush`` (to obtain identities / surface constraint errors) but do not
  ``commit``.
- Column references for filtering and sorting are validated against an explicit
  per-repository allow-list and bound as parameters — no SQL text interpolation.
- No unbounded result sets: list queries always paginate.
- No business logic: this is mechanical persistence only.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Generic, NoReturn, TypeVar

from asyncpg.exceptions import CheckViolationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationAppError
from app.models.base import Base
from app.models.mixins import SoftDeleteMixin
from app.repositories.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    SoftDeleteNotSupportedError,
)
from app.repositories.query import (
    apply_filters,
    apply_sorts,
    clamp_limit,
)
from app.repositories.specification import Specification
from app.repositories.types import (
    Filter,
    Pagination,
    PaginationResult,
    Sort,
)

TModel = TypeVar("TModel", bound=Base)


class BaseRepository(Generic[TModel]):
    """Generic repository for a single ORM model.

    Subclasses set :attr:`model` and, optionally, the allow-lists
    :attr:`filterable_fields` and :attr:`sortable_fields`.
    """

    #: The ORM model this repository manages. Set by subclasses.
    model: type[TModel]

    #: Columns that may be filtered on (allow-list, BACKEND_SPEC §6.5).
    filterable_fields: frozenset[str] = frozenset()

    #: Columns that may be sorted on (allow-list, BACKEND_SPEC §6.6).
    sortable_fields: frozenset[str] = frozenset()

    def __init__(self, session: AsyncSession) -> None:
        """Store the injected session. Transactions are not managed here."""
        self.session = session

    # --- Internal helpers -------------------------------------------------

    def _supports_soft_delete(self) -> bool:
        return issubclass(self.model, SoftDeleteMixin)

    def _base_select(self) -> Any:
        return select(self.model)

    def _reraise_integrity_error(self, exc: IntegrityError) -> NoReturn:
        """Classify a flush-time IntegrityError by its PostgreSQL SQLSTATE.

        A CHECK constraint violation is a data-validation failure, not a
        conflict with existing data, so it must not be reported as
        DuplicateEntityError. Every other IntegrityError (unique violations,
        and also foreign-key/NOT NULL violations, unchanged pending further
        instruction) keeps the prior behavior.

        ``exc.orig`` is SQLAlchemy's own asyncpg DBAPI-compatibility
        exception (``AsyncAdapt_asyncpg_dbapi.IntegrityError``), not the
        concrete ``asyncpg.exceptions.CheckViolationError``/
        ``UniqueViolationError`` instance asyncpg raised — the dialect
        translates it (sqlalchemy/dialects/postgresql/asyncpg.py) but
        deliberately copies the original ``sqlstate`` onto that wrapper for
        exactly this kind of classification, so that (not an isinstance
        check against the asyncpg class, and not message-string matching) is
        the correct thing to compare against.
        """
        if getattr(exc.orig, "sqlstate", None) == CheckViolationError.sqlstate:
            raise ValidationAppError() from exc
        raise DuplicateEntityError() from exc

    # --- Read -------------------------------------------------------------

    async def get_by_id(self, entity_id: Any) -> TModel | None:
        """Return an entity by primary key, or ``None`` if absent."""
        return await self.session.get(self.model, entity_id)

    async def get_one(
        self,
        filters: Sequence[Filter] | None = None,
        *,
        specification: Specification | None = None,
    ) -> TModel | None:
        """Return the first matching entity, or ``None``."""
        stmt = apply_filters(
            self._base_select(), self.model, filters, self.filterable_fields
        )
        if specification is not None:
            stmt = stmt.where(specification.to_expression())
        stmt = stmt.limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_many(
        self,
        filters: Sequence[Filter] | None = None,
        sorts: Sequence[Sort] | None = None,
        pagination: Pagination | None = None,
        *,
        specification: Specification | None = None,
        with_total: bool = True,
    ) -> PaginationResult[TModel]:
        """Return a paginated page of matching entities.

        Always paginated — an unbounded result set cannot be requested
        (BACKEND_SPEC §6.4).
        """
        stmt = apply_filters(
            self._base_select(), self.model, filters, self.filterable_fields
        )
        if specification is not None:
            stmt = stmt.where(specification.to_expression())
        stmt = apply_sorts(stmt, self.model, sorts, self.sortable_fields)

        page = pagination or Pagination()
        limit = clamp_limit(page.limit)
        offset = max(page.offset, 0)

        # Fetch one extra row to determine has_more without a second round-trip.
        stmt = stmt.limit(limit + 1).offset(offset)
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())

        has_more = len(rows) > limit
        items = rows[:limit]

        total: int | None = None
        if with_total:
            total = await self.count(filters, specification=specification)

        return PaginationResult(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more,
        )

    async def exists(
        self,
        filters: Sequence[Filter] | None = None,
        *,
        specification: Specification | None = None,
    ) -> bool:
        """Return whether any entity matches."""
        stmt = select(func.count()).select_from(self.model)
        stmt = apply_filters(stmt, self.model, filters, self.filterable_fields)
        if specification is not None:
            stmt = stmt.where(specification.to_expression())
        stmt = stmt.limit(1)
        result = await self.session.execute(stmt)
        return int(result.scalar_one()) > 0

    async def count(
        self,
        filters: Sequence[Filter] | None = None,
        *,
        specification: Specification | None = None,
    ) -> int:
        """Return the number of matching entities."""
        stmt = select(func.count()).select_from(self.model)
        stmt = apply_filters(stmt, self.model, filters, self.filterable_fields)
        if specification is not None:
            stmt = stmt.where(specification.to_expression())
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    # --- Write ------------------------------------------------------------

    async def create(self, data: dict[str, Any]) -> TModel:
        """Insert a new entity and flush (no commit)."""
        entity = self.model(**data)
        self.session.add(entity)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            self._reraise_integrity_error(exc)
        return entity

    async def create_many(self, data: Sequence[dict[str, Any]]) -> list[TModel]:
        """Insert several entities and flush (no commit)."""
        entities = [self.model(**item) for item in data]
        self.session.add_all(entities)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            self._reraise_integrity_error(exc)
        return entities

    async def update(self, entity_id: Any, data: dict[str, Any]) -> TModel:
        """Update an entity by id and flush (no commit)."""
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise EntityNotFoundError()
        for key, value in data.items():
            setattr(entity, key, value)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            self._reraise_integrity_error(exc)
        return entity

    async def delete(self, entity_id: Any) -> None:
        """Hard-delete an entity by id and flush (no commit)."""
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise EntityNotFoundError()
        await self.session.delete(entity)
        await self.session.flush()

    # --- Soft delete (only when the model supports it) --------------------

    async def soft_delete(self, entity_id: Any) -> TModel:
        """Mark an entity deleted (sets ``deleted_at``) and flush.

        Raises SoftDeleteNotSupportedError if the model lacks the mixin.
        """
        if not self._supports_soft_delete():
            raise SoftDeleteNotSupportedError()
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise EntityNotFoundError()
        # setattr is used because TModel is generic; _supports_soft_delete has
        # already guaranteed the column exists on this model.
        entity.deleted_at = func.now()  # type: ignore[attr-defined]
        await self.session.flush()
        # Refresh so the server-evaluated timestamp is loaded back.
        await self.session.refresh(entity, attribute_names=["deleted_at"])
        return entity

    async def restore(self, entity_id: Any) -> TModel:
        """Clear ``deleted_at`` on a soft-deleted entity and flush.

        Raises SoftDeleteNotSupportedError if the model lacks the mixin.
        """
        if not self._supports_soft_delete():
            raise SoftDeleteNotSupportedError()
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise EntityNotFoundError()
        entity.deleted_at = None  # type: ignore[attr-defined]
        await self.session.flush()
        return entity
