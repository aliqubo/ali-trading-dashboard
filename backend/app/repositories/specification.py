"""Specification pattern (BACKEND_SPEC §6.7).

Encapsulates a reusable, composable query condition. Each specification produces
a SQLAlchemy boolean ``ColumnElement`` that the base repository applies to a
statement. Specifications compose with AND/OR/NOT so complex filters are built
from small, tested pieces instead of duplicating filter logic.

Structure only — a specification describes *what* to select, never *why*; it
holds no business rules.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy import ColumnElement, and_, not_, or_


class Specification(ABC):
    """Base class for a composable query specification."""

    @abstractmethod
    def to_expression(self) -> ColumnElement[bool]:
        """Return the SQLAlchemy boolean expression for this specification."""
        raise NotImplementedError

    def __and__(self, other: Specification) -> Specification:
        return AndSpecification(self, other)

    def __or__(self, other: Specification) -> Specification:
        return OrSpecification(self, other)

    def __invert__(self) -> Specification:
        return NotSpecification(self)


class ExpressionSpecification(Specification):
    """Wrap a ready-made SQLAlchemy boolean expression as a specification."""

    def __init__(self, expression: ColumnElement[bool]) -> None:
        self._expression = expression

    def to_expression(self) -> ColumnElement[bool]:
        return self._expression


class AndSpecification(Specification):
    """Logical AND of two or more specifications."""

    def __init__(self, *specs: Specification) -> None:
        self._specs = specs

    def to_expression(self) -> ColumnElement[bool]:
        return and_(*(spec.to_expression() for spec in self._specs))


class OrSpecification(Specification):
    """Logical OR of two or more specifications."""

    def __init__(self, *specs: Specification) -> None:
        self._specs = specs

    def to_expression(self) -> ColumnElement[bool]:
        return or_(*(spec.to_expression() for spec in self._specs))


class NotSpecification(Specification):
    """Logical negation of a specification."""

    def __init__(self, spec: Specification) -> None:
        self._spec = spec

    def to_expression(self) -> ColumnElement[bool]:
        return not_(self._spec.to_expression())
