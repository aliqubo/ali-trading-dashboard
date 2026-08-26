"""Query utilities.

Helpers that translate the framework's :mod:`types` (Filter/Sort/Pagination)
into safe SQLAlchemy clauses. All column references are validated against an
explicit allow-list and bound as parameters — never interpolated as SQL text
(BACKEND_SPEC §6.5/§6.6).

Structure only — these are mechanical translators with no business logic.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, Select, asc, desc, func, select
from sqlalchemy.orm import InstrumentedAttribute

from app.repositories.exceptions import InvalidFilterError, InvalidSortError
from app.repositories.types import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    Filter,
    FilterOperator,
    Pagination,
    Sort,
    SortDirection,
)


def clamp_limit(limit: int) -> int:
    """Clamp a page size into the allowed range (never unbounded)."""
    if limit <= 0:
        return DEFAULT_PAGE_SIZE
    return min(limit, MAX_PAGE_SIZE)


def resolve_column(
    model: type[Any],
    field: str,
    allowed_fields: frozenset[str],
    *,
    for_sort: bool = False,
) -> InstrumentedAttribute[Any]:
    """Resolve a column name against the model and an allow-list.

    Raises InvalidSortError/InvalidFilterError if the field is not allow-listed
    or not a real column, preventing access to arbitrary attributes.
    """
    if field not in allowed_fields:
        if for_sort:
            raise InvalidSortError(f"Sorting by '{field}' is not allowed.")
        raise InvalidFilterError(f"Filtering by '{field}' is not allowed.")

    column = getattr(model, field, None)
    if not isinstance(column, InstrumentedAttribute):
        if for_sort:
            raise InvalidSortError(f"'{field}' is not a valid column.")
        raise InvalidFilterError(f"'{field}' is not a valid column.")
    return column


def _build_condition(
    column: InstrumentedAttribute[Any], flt: Filter
) -> ColumnElement[bool]:
    """Build a single boolean condition from a filter (parameterized)."""
    op = flt.operator
    value = flt.value

    if op is FilterOperator.EQ:
        return column == value
    if op is FilterOperator.NE:
        return column != value
    if op is FilterOperator.GT:
        return column > value
    if op is FilterOperator.GTE:
        return column >= value
    if op is FilterOperator.LT:
        return column < value
    if op is FilterOperator.LTE:
        return column <= value
    if op is FilterOperator.IN:
        if not isinstance(value, list | tuple | set):
            raise InvalidFilterError("IN requires a sequence value.")
        return column.in_(list(value))
    if op is FilterOperator.NOT_IN:
        if not isinstance(value, list | tuple | set):
            raise InvalidFilterError("NOT_IN requires a sequence value.")
        return column.notin_(list(value))
    if op is FilterOperator.LIKE:
        return column.like(value)
    if op is FilterOperator.ILIKE:
        return column.ilike(value)
    if op is FilterOperator.IS_NULL:
        return column.is_(None)
    if op is FilterOperator.IS_NOT_NULL:
        return column.is_not(None)
    if op is FilterOperator.BETWEEN:
        if not isinstance(value, list | tuple) or len(value) != 2:
            raise InvalidFilterError("BETWEEN requires a 2-item sequence.")
        return column.between(value[0], value[1])

    raise InvalidFilterError(f"Unsupported operator: {op}.")


def apply_filters(
    stmt: Select[Any],
    model: type[Any],
    filters: Sequence[Filter] | None,
    allowed_fields: frozenset[str],
) -> Select[Any]:
    """Apply a list of filters to a select statement (AND-combined)."""
    if not filters:
        return stmt
    for flt in filters:
        column = resolve_column(model, flt.field, allowed_fields)
        stmt = stmt.where(_build_condition(column, flt))
    return stmt


def apply_sorts(
    stmt: Select[Any],
    model: type[Any],
    sorts: Sequence[Sort] | None,
    allowed_fields: frozenset[str],
) -> Select[Any]:
    """Apply ordering clauses to a select statement."""
    if not sorts:
        return stmt
    for sort in sorts:
        column = resolve_column(model, sort.field, allowed_fields, for_sort=True)
        if sort.direction is SortDirection.DESC:
            stmt = stmt.order_by(desc(column))
        else:
            stmt = stmt.order_by(asc(column))
    return stmt


def apply_pagination(stmt: Select[Any], pagination: Pagination | None) -> Select[Any]:
    """Apply offset/limit to a statement, clamping the limit."""
    if pagination is None:
        return stmt.limit(DEFAULT_PAGE_SIZE)
    limit = clamp_limit(pagination.limit)
    offset = max(pagination.offset, 0)
    return stmt.limit(limit).offset(offset)


def count_statement(
    model: type[Any],
    filters: Sequence[Filter] | None,
    allowed_fields: frozenset[str],
) -> Select[Any]:
    """Build a COUNT(*) statement with the same filters applied."""
    stmt = select(func.count()).select_from(model)
    return apply_filters(stmt, model, filters, allowed_fields)
