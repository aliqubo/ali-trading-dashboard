"""Token service interface (BACKEND_SPEC §8.1/§8.2, SYSTEM_DESIGN.md §8.3/§8.4).

Defines ``ITokenService`` as a typing Protocol — contract only for this file;
the concrete implementation is :class:`app.core.security.token.
jwt_token_service.JWTTokenService`.

Scope discipline for this phase: token issuance and verification only. No
persistence (no session/refresh-token DB row is read or written here), no
rotation, no revocation, no "current user" dependency, no authorization.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.security.token.claims import TokenClaims, TokenType


@runtime_checkable
class ITokenService(Protocol):
    """Contract for issuing and verifying JWTs."""

    def create_access_token(self, subject: str) -> str:
        """Return a signed, short-lived access token for ``subject``."""
        ...

    def create_refresh_token(self, subject: str) -> str:
        """Return a signed, long-lived refresh token for ``subject``."""
        ...

    def decode_token(self, token: str) -> TokenClaims:
        """Decode and fully validate ``token``, returning its claims.

        Verifies the signature, expiration, issuer, and audience, and that
        every required claim is present. Raises a specific
        ``InvalidTokenError`` subclass (see
        :mod:`app.core.security.token.exceptions`) on any failure — never
        returns a partially-trusted result.
        """
        ...

    def validate_token(self, token: str, expected_type: TokenType) -> TokenClaims:
        """Decode ``token`` and additionally require its type to match.

        Equivalent to :meth:`decode_token` plus a check that the token's
        ``type`` claim equals ``expected_type``, raising
        ``UnsupportedTokenTypeError`` otherwise. Used by a caller that only
        accepts one specific kind of token (e.g. "this operation requires an
        access token").
        """
        ...
