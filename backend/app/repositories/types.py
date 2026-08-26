"""Repository layer types.

Framework-level data types shared by the base repository and query utilities
(BACKEND_SPEC §6.4–§6.6). Pure data structures only — no business logic and no
database access here.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")

# Default and maximum page sizes. Unbounded result sets are forbidden
# (BACKEND_SPEC §6.4).
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


class SortDirection(str, enum.Enum):
    """Sort direction for an ordering clause."""

    ASC = "asc"
    DESC = "desc"


class FilterOperator(str, enum.Enum):
    """Supported, safe filter operators.

    The set is fixed (allow-list) so callers cannot express arbitrary SQL; the
    repository translates each operator into a parameterized clause
    (BACKEND_SPEC §6.5).
    """

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    LIKE = "like"
    ILIKE = "ilike"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"


@dataclass(frozen=True, slots=True)
class Filter:
    """A single filter condition.

    Attributes:
        field: Column name to filter on. It is validated against a per-repository
            allow-list before use; it is never interpolated into SQL text.
        operator: One of the safe :class:`FilterOperator` values.
        value: The comparison value (bound as a parameter). May be ``None`` for
            null checks, a sequence for ``IN``/``NOT_IN``, or a 2-tuple for
            ``BETWEEN``.
    """

    field: str
    operator: FilterOperator = FilterOperator.EQ
    value: object = None


@dataclass(frozen=True, slots=True)
class Sort:
    """A single ordering clause.

    ``field`` is validated against a per-repository allow-list (BACKEND_SPEC
    §6.6); it is never interpolated into SQL text.
    """

    field: str
    direction: SortDirection = SortDirection.ASC


@dataclass(frozen=True, slots=True)
class Pagination:
    """Offset/limit pagination request.

    ``limit`` is clamped to :data:`MAX_PAGE_SIZE` by the repository so an
    unbounded page can never be requested.
    """

    limit: int = DEFAULT_PAGE_SIZE
    offset: int = 0


@dataclass(frozen=True, slots=True)
class CursorPagination:
    """Cursor-based pagination request (BACKEND_SPEC §6.4).

    Preferred for large/time-series data. ``cursor`` is an opaque value produced
    by a previous page; ``None`` starts from the beginning.
    """

    limit: int = DEFAULT_PAGE_SIZE
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class PaginationResult(Generic[T]):
    """A page of results plus navigation metadata.

    Attributes:
        items: The rows for this page.
        total: Total number of matching rows (offset pagination only; ``None``
            for cursor pagination where a full count is intentionally skipped).
        limit: The effective page size used.
        offset: The offset used (offset pagination only).
        next_cursor: Opaque cursor for the next page (cursor pagination only).
        has_more: Whether more rows exist after this page.
    """

    items: list[T] = field(default_factory=list)
    total: int | None = None
    limit: int = DEFAULT_PAGE_SIZE
    offset: int = 0
    next_cursor: str | None = None
    has_more: bool = False
