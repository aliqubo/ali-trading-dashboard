"""Application error hierarchy (ARCHITECTURE.md §7, BACKEND_SPEC §9).

Reconstructed MVP scaffolding — original source unavailable. This file does
not exist in any source archive, but its class names (AppError, NotFoundError,
UnauthorizedError, ForbiddenError, ConflictError, ValidationAppError) are
proven to have existed by their use across already-restored files
(core/security/exceptions.py, core/security/token/exceptions.py,
services/authentication/exceptions.py, services/authorization/exceptions.py)
and by the unified error envelope shape described in PROJECT_AUDIT_REPORT.md
(``error.code/message/details/request_id``). See RECOVERY_MANIFEST.md.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for every known application error.

    Subclasses set ``code``, ``message`` and ``status_code`` as class
    attributes. ``message`` and ``details`` may optionally be overridden per
    instance at raise time.
    """

    code: str = "app_error"
    message: str = "An application error occurred."
    status_code: int = 500

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message or self.message)
        if message is not None:
            self.message = message
        self.details = details


class NotFoundError(AppError):
    """The requested resource does not exist."""

    code = "not_found"
    message = "The requested resource was not found."
    status_code = 404


class UnauthorizedError(AppError):
    """The request lacks valid authentication."""

    code = "unauthorized"
    message = "Authentication is required."
    status_code = 401


class ForbiddenError(AppError):
    """The caller is authenticated but not permitted to do this."""

    code = "forbidden"
    message = "You do not have permission to perform this action."
    status_code = 403


class ConflictError(AppError):
    """The request conflicts with the current state of the resource."""

    code = "conflict"
    message = "The request conflicts with the current state."
    status_code = 409


class ValidationAppError(AppError):
    """The request failed a validation rule."""

    code = "validation_error"
    message = "The request failed validation."
    status_code = 422
