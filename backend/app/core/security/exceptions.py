"""Password security exceptions.

Extends the application error hierarchy (``app.core.exceptions.AppError``,
ARCHITECTURE.md §7 / BACKEND_SPEC §9) with exceptions specific to password
handling. These are infrastructure-level error *types* only — no policy
decision or hashing logic lives here.
"""

from __future__ import annotations

from app.core.exceptions import ConflictError, ValidationAppError


class InvalidPasswordException(ValidationAppError):
    """The supplied password does not satisfy structural requirements.

    Raised for structural/format problems (e.g. outside the configured
    length bounds) as opposed to strength (see
    :class:`WeakPasswordException`).
    """

    code = "invalid_password"
    message = "The password does not meet the required format."


class WeakPasswordException(ValidationAppError):
    """The supplied password does not meet the configured strength policy.

    Raised when a password is structurally valid but fails a strength
    criterion (missing required character classes, insufficient entropy).
    """

    code = "weak_password"
    message = "The password is not strong enough."


class PasswordReuseException(ConflictError):
    """The supplied password matches a previously used password.

    Raised when a password-change/reset attempt reuses a password the account
    has used before, per a (future) password-history policy.
    """

    code = "password_reuse"
    message = "This password has been used before; choose a different one."
