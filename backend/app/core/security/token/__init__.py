"""JWT/token service package (BACKEND_SPEC §8.1).

Reconstructed MVP scaffolding — original source unavailable in this form.
Unlike its sibling packages, this one MUST re-export: at least one already-
restored file (app/services/authentication/refresh_token_service.py) does
`from app.core.security.token import ITokenService, TokenType` — a
package-level import, not a submodule import. See RECOVERY_MANIFEST.md.
"""

from __future__ import annotations

from app.core.security.token.claims import TokenClaims, TokenType
from app.core.security.token.exceptions import (
    ExpiredTokenError,
    InvalidClaimsError,
    InvalidSignatureError,
    InvalidTokenError,
    UnsupportedTokenTypeError,
)
from app.core.security.token.interfaces import ITokenService
from app.core.security.token.jwt_token_service import JWTTokenService

__all__ = [
    "ITokenService",
    "JWTTokenService",
    "TokenClaims",
    "TokenType",
    "ExpiredTokenError",
    "InvalidClaimsError",
    "InvalidSignatureError",
    "InvalidTokenError",
    "UnsupportedTokenTypeError",
]
