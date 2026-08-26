"""JWT token service (BACKEND_SPEC §8.1/§8.2, SYSTEM_DESIGN.md §8.3/§8.4).

Concrete implementation of :class:`ITokenService` using PyJWT with a
symmetric secret (HS256 by default) — matching the documented design
("يُوقّع بمفتاح سرّي"). No persistence, no rotation, no revocation: this class
only signs and verifies self-contained tokens.

Security notes (this phase's explicit requirements):
- Every decode call passes an explicit, single-item ``algorithms=[...]``
  allow-list to PyJWT — a token whose header names any other algorithm
  (including ``none``) is rejected outright; the configured algorithm itself
  is validated against a hardcoded allow-list at construction time, so no
  amount of misconfiguration can widen it beyond {"HS256"}.
- Signature, expiration, issuer, and audience are all verified by PyJWT
  during decode; required claims are enforced via ``options={"require": ...}``
  so a token missing any of ``sub``/``jti``/``type``/``iat``/``exp``/``iss``/
  ``aud`` is rejected before any claim is read.
- This class takes no logger and contains no logging statements of any kind
  — the surest way to guarantee a token or the signing secret is never
  written to a log from here. No exception message defined in
  :mod:`exceptions` interpolates the token or the secret.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.core.security.token.claims import TokenClaims, TokenType
from app.core.security.token.exceptions import (
    ExpiredTokenError,
    InvalidClaimsError,
    InvalidSignatureError,
    InvalidTokenError,
    UnsupportedTokenTypeError,
)

#: The only algorithms this service will ever sign with or accept on decode.
#: Configuring anything outside this set fails fast at construction time.
_ALLOWED_ALGORITHMS: frozenset[str] = frozenset({"HS256"})

#: Standard claims every token issued by this service carries.
_REQUIRED_CLAIMS: list[str] = ["sub", "jti", "type", "iat", "exp", "iss", "aud"]


class JWTTokenService:
    """Issues and verifies JWTs. No persistence, no rotation, no revocation.

    All configuration (secret, algorithm, lifetimes, issuer, audience) is
    passed in explicitly by the caller — this class defines no default
    secret. The application wires these from ``Settings``
    (``app.core.config``) at startup.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str,
        access_token_expire_minutes: int,
        refresh_token_expire_days: int,
        issuer: str,
        audience: str,
    ) -> None:
        if algorithm not in _ALLOWED_ALGORITHMS:
            raise ValueError(
                f"Disallowed JWT algorithm: {algorithm!r}. "
                f"Allowed: {sorted(_ALLOWED_ALGORITHMS)}."
            )
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_ttl = timedelta(minutes=access_token_expire_minutes)
        self._refresh_ttl = timedelta(days=refresh_token_expire_days)
        self._issuer = issuer
        self._audience = audience

    # --- Issuance -----------------------------------------------------

    def create_access_token(self, subject: str) -> str:
        """Return a signed, short-lived access token for ``subject``."""
        return self._create_token(subject, TokenType.ACCESS, self._access_ttl)

    def create_refresh_token(self, subject: str) -> str:
        """Return a signed, long-lived refresh token for ``subject``."""
        return self._create_token(subject, TokenType.REFRESH, self._refresh_ttl)

    def _create_token(self, subject: str, token_type: TokenType, ttl: timedelta) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": subject,
            "jti": str(uuid.uuid4()),
            "type": token_type.value,
            "iat": now,
            "exp": now + ttl,
            "iss": self._issuer,
            "aud": self._audience,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    # --- Verification ---------------------------------------------------

    def decode_token(self, token: str) -> TokenClaims:
        """Decode and fully validate ``token``, returning its claims."""
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": _REQUIRED_CLAIMS},
            )
        except jwt.ExpiredSignatureError as exc:
            raise ExpiredTokenError() from exc
        except (jwt.InvalidSignatureError, jwt.InvalidAlgorithmError) as exc:
            raise InvalidSignatureError() from exc
        except (
            jwt.InvalidIssuerError,
            jwt.InvalidAudienceError,
            jwt.MissingRequiredClaimError,
        ) as exc:
            raise InvalidClaimsError() from exc
        except jwt.PyJWTError as exc:
            raise InvalidTokenError() from exc

        try:
            token_type = TokenType(payload["type"])
        except ValueError as exc:
            raise UnsupportedTokenTypeError() from exc

        return TokenClaims(
            sub=payload["sub"],
            jti=payload["jti"],
            type=token_type,
            iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
            exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
            iss=payload["iss"],
            aud=payload["aud"],
        )

    def validate_token(self, token: str, expected_type: TokenType) -> TokenClaims:
        """Decode ``token`` and additionally require its type to match."""
        claims = self.decode_token(token)
        if claims.type is not expected_type:
            raise UnsupportedTokenTypeError()
        return claims
