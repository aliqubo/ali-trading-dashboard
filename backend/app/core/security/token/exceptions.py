"""Token exceptions.

Extends the application error hierarchy (``app.core.exceptions.AppError``)
with exceptions specific to JWT handling. ``InvalidTokenError`` is the base
for every token-rejection reason; the other four are specific subclasses so
callers can distinguish *why* a token was rejected without parsing messages.

No token or secret value is ever included in any exception's message or
``details`` — see the security notes in :mod:`jwt_token_service`.
"""

from __future__ import annotations

from app.core.exceptions import UnauthorizedError


class InvalidTokenError(UnauthorizedError):
    """The token is malformed, unparseable, or otherwise not acceptable.

    Base class for every more specific token-rejection reason below.
    """

    code = "invalid_token"
    message = "The token is invalid."


class ExpiredTokenError(InvalidTokenError):
    """The token's ``exp`` claim is in the past."""

    code = "expired_token"
    message = "The token has expired."


class InvalidSignatureError(InvalidTokenError):
    """The token's signature does not verify, or uses a disallowed algorithm."""

    code = "invalid_token_signature"
    message = "The token signature is invalid."


class InvalidClaimsError(InvalidTokenError):
    """A required claim is missing, or ``iss``/``aud`` does not match."""

    code = "invalid_token_claims"
    message = "The token claims are invalid."


class UnsupportedTokenTypeError(InvalidTokenError):
    """The token's ``type`` claim is unrecognized, or does not match what the
    caller required (e.g. a refresh token presented where an access token was
    expected).
    """

    code = "unsupported_token_type"
    message = "This token type is not supported for this operation."
