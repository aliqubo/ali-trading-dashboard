"""Repository layer exceptions.

Infrastructure-level errors raised by the base repository. They extend the
application error hierarchy (BACKEND_SPEC §9) so the global handlers can map them
to a unified response. No business semantics here.
"""

from __future__ import annotations

from app.core.exceptions import AppError, ConflictError, NotFoundError


class RepositoryError(AppError):
    """Base class for repository-layer errors."""

    code = "repository_error"
    message = "A repository error occurred."
    status_code = 500


class EntityNotFoundError(NotFoundError):
    """A requested entity does not exist."""

    code = "entity_not_found"
    message = "The requested entity was not found."


class DuplicateEntityError(ConflictError):
    """An entity violates a unique constraint."""

    code = "duplicate_entity"
    message = "The entity conflicts with an existing one."


class InvalidFilterError(RepositoryError):
    """A filter references a field or operator that is not allowed."""

    code = "invalid_filter"
    message = "The provided filter is not allowed."
    status_code = 400


class InvalidSortError(RepositoryError):
    """A sort references a field that is not allowed."""

    code = "invalid_sort"
    message = "The provided sort field is not allowed."
    status_code = 400


class SoftDeleteNotSupportedError(RepositoryError):
    """Soft delete/restore requested on a model that does not support it."""

    code = "soft_delete_not_supported"
    message = "This entity does not support soft deletion."
    status_code = 400
