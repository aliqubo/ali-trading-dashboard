"""Authentication exceptions.

Extends the application error hierarchy (``app.core.exceptions.AppError``)
with exceptions specific to authentication. These are error *types* raised
for exceptional/programmer-error conditions; ordinary authentication failures
(wrong password, disabled/locked account, unknown user) are represented as
data via :class:`app.services.authentication.results.AuthenticationResult`
rather than raised, so callers can handle them without exception-driven
control flow.

Phase 3.4 adds session and refresh-token persistence/lifecycle exceptions.
No JWT-decoding exceptions live here — those are
:mod:`app.core.security.token.exceptions` (Phase 3.3); this module's
exceptions are raised for the *database record's* state (not found, revoked,
expired, reused), which is a distinct concern from the *token's own*
signature/claims validity.
"""

from __future__ import annotations

from app.core.exceptions import AppError, NotFoundError, UnauthorizedError


class AuthenticationError(AppError):
    """Base class for authentication-domain errors."""

    code = "authentication_error"
    message = "An authentication error occurred."
    status_code = 401


class InactiveUserError(UnauthorizedError):
    """Raised when an operation requires an active user but the account is
    not usable (disabled, locked, or otherwise not in an active state).

    This is distinct from :class:`AuthenticationResult` carrying a
    ``USER_DISABLED``/``USER_LOCKED`` failure reason: ``authenticate()``
    itself never raises for these conditions (it returns a failed result);
    this exception exists for other call sites that need an active user as a
    precondition and choose to raise rather than branch on a result value.
    """

    code = "inactive_user"
    message = "This account is not active."


# --- Session lifecycle (Phase 3.4) -----------------------------------------


class SessionNotFoundError(NotFoundError):
    """No session record exists for the given id."""

    code = "session_not_found"
    message = "The session was not found."


class SessionRevokedError(UnauthorizedError):
    """The session is no longer usable.

    Covers both an explicitly revoked session (``revoked_at``/``is_active``)
    and an expired one (``expires_at`` in the past) — a session's own
    ``expires_at`` failing is treated as the same outcome as revocation
    rather than introducing a separate "session expired" exception, since
    both mean the same thing to a caller: this session can no longer be
    used.
    """

    code = "session_revoked"
    message = "The session has been revoked or has expired."


# --- Refresh token lifecycle (Phase 3.4) -----------------------------------


class RefreshTokenError(UnauthorizedError):
    """Base class for refresh-token persistence/lifecycle errors.

    All four subclasses below share the 401 status: whether a presented
    refresh token's record is missing, revoked, expired, or flagged as
    reused, the caller-facing outcome is uniformly "this refresh token is not
    accepted" — deliberately not distinguished by HTTP status, to avoid
    leaking which specific condition applies.
    """

    code = "refresh_token_error"
    message = "The refresh token is not valid."


class RefreshTokenNotFoundError(RefreshTokenError):
    """No refresh-token record exists for the given (hashed) token."""

    code = "refresh_token_not_found"
    message = "The refresh token was not found."


class RefreshTokenRevokedError(RefreshTokenError):
    """The refresh-token record is explicitly marked revoked."""

    code = "refresh_token_revoked"
    message = "The refresh token has been revoked."


class RefreshTokenExpiredError(RefreshTokenError):
    """The refresh-token record's stored ``expires_at`` is in the past.

    This is a database-level check, independent of the JWT's own ``exp``
    claim (which :class:`app.core.security.token.exceptions.ExpiredTokenError`
    already covers) — defense in depth per this phase's explicit requirement.
    """

    code = "refresh_token_expired"
    message = "The refresh token has expired."


class RefreshTokenReuseDetectedError(RefreshTokenError):
    """A refresh token already marked revoked was presented again.

    Per BACKEND_SPEC §8.2 ("كشف إعادة استخدام رمز مُبطل يُبطل كامل سلسلة
    الجلسة"), detecting this revokes the entire session's refresh-token chain
    and the session itself — a stronger response than any single-token
    rejection, since reuse of an already-rotated token is a signal of
    possible token theft.
    """

    code = "refresh_token_reuse_detected"
    message = "This refresh token has already been used and is no longer valid."
