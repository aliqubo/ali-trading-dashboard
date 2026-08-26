"""Authentication result type.

Defines :class:`AuthenticationResult` — the outcome of an authentication
attempt (BACKEND_SPEC §2.2: Authentication domain owns credential
verification). No token, cookie, or session is issued or referenced here;
this is a plain result value.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from app.services.identity.dtos import UserResponse


class AuthenticationFailureReason(str, enum.Enum):
    """Why an authentication attempt failed.

    Values are intentionally generic (no user enumeration hints beyond what
    the caller already controls) but distinguishable enough for logging and
    for a future service layer to decide how to respond.
    """

    UNKNOWN_USER = "unknown_user"
    WRONG_PASSWORD = "wrong_password"
    USER_DISABLED = "user_disabled"
    USER_LOCKED = "user_locked"


@dataclass(frozen=True, slots=True)
class AuthenticationResult:
    """The outcome of an :meth:`IAuthenticationService.authenticate` call.

    Exactly one of ``user`` (on success) or ``failure_reason`` (on failure) is
    populated, matching ``success``. No token, refresh token, or session
    identifier is carried here — this type only answers "did the credentials
    check out, and for whom".
    """

    success: bool
    user: UserResponse | None = None
    failure_reason: AuthenticationFailureReason | None = None

    @classmethod
    def succeeded(cls, user: UserResponse) -> AuthenticationResult:
        """Build a successful result carrying the authenticated user."""
        return cls(success=True, user=user, failure_reason=None)

    @classmethod
    def failed(cls, reason: AuthenticationFailureReason) -> AuthenticationResult:
        """Build a failed result with the given reason."""
        return cls(success=False, user=None, failure_reason=reason)
