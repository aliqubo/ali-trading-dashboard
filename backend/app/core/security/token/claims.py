"""Token claims and type (SYSTEM_DESIGN.md §8.3/§8.4, BACKEND_SPEC §8.1/§8.2).

Defines :class:`TokenType` (the ``type`` claim's allowed values) and
:class:`TokenClaims` — the fully-validated, decoded representation of a JWT's
standard claims. No signing, encoding, or verification logic lives here;
:mod:`jwt_token_service` produces and consumes these.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime


class TokenType(str, enum.Enum):
    """The ``type`` claim: which kind of token this is.

    Distinguishing access from refresh tokens by claim (not just by which
    endpoint issued them) lets :meth:`ITokenService.validate_token` reject a
    refresh token presented where an access token is required, and vice
    versa — even though both are structurally valid, signed JWTs.
    """

    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """The decoded, fully-validated claims of a JWT.

    Every field here corresponds to a required claim (this phase's explicit
    list): ``sub``, ``jti``, ``type``, ``iat``, ``exp``, ``iss``, ``aud``. No
    additional claims are defined — permissions/roles are deliberately out of
    scope for this phase (Authorization/RBAC is explicitly forbidden here).

    Attributes:
        sub: Subject — the identifier this token represents (a user id, as a
            string).
        jti: JWT ID — a unique identifier for this specific token instance.
        type: Which kind of token this is (:class:`TokenType`).
        iat: Issued-at timestamp (UTC).
        exp: Expiration timestamp (UTC).
        iss: Issuer — identifies the party that issued the token.
        aud: Audience — identifies the intended recipient(s) of the token.
    """

    sub: str
    jti: str
    type: TokenType
    iat: datetime
    exp: datetime
    iss: str
    aud: str
