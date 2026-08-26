"""Authentication service interface (BACKEND_SPEC §2.2).

Defines ``IAuthenticationService`` (Phase 3.2), and ``ISessionService`` /
``IRefreshTokenService`` (Phase 3.4) as typing Protocols — contracts only for
this file; concrete implementations live in
:mod:`app.services.authentication.authentication_service`,
:mod:`app.services.authentication.session_service`, and
:mod:`app.services.authentication.refresh_token_service` respectively.

Naming note: ``app.services.identity.interfaces`` (Phase 3.0) already defines
a different ``ISessionService`` — a read/administrative view over session
records (``list_sessions_for_user``, ``get_session``, ``revoke_session``,
``revoke_all_sessions_for_user``) built on generic repository queries alone.
The ``ISessionService`` defined *here* is a distinct contract for the
Authentication domain's session *lifecycle* (creation tied to a login,
validation as part of the refresh flow) and is not a replacement for, nor
modifies, the Phase 3.0 interface. The two are disambiguated by their full
module path; this duplication is intentional and documented in
``PHASE_3_4_REPORT.md`` rather than silently resolved by editing the
already-approved Phase 3.0 file.

Scope discipline for this phase: session/refresh-token *persistence and
lifecycle* only. No REST API, no login/logout/register endpoint, no
"current user" dependency, no authorization/RBAC.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.services.authentication.results import AuthenticationResult
from app.services.authentication.token_records import RefreshTokenResponse
from app.services.identity.dtos import SessionResponse
from app.services.interfaces import IService

if TYPE_CHECKING:
    from app.models import User


@runtime_checkable
class IAuthenticationService(IService, Protocol):
    """Contract for credential verification (no tokens, no sessions)."""

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Return whether ``password`` matches ``password_hash``.

        A thin, side-effect-free delegate to the injected password hasher —
        no user lookup, no logging, no state change.
        """
        ...

    async def authenticate(
        self, identifier: str, password: str
    ) -> AuthenticationResult:
        """Verify credentials for the user identified by ``identifier``.

        ``identifier`` may be an email or a username. Looks the user up,
        checks that the account is usable, and verifies the password —
        returning a failed :class:`AuthenticationResult` (never raising) for
        an unknown user, wrong password, disabled account, or locked
        account. Issues no token, cookie, or session.
        """
        ...

    def create_authenticated_user(self, user: User) -> AuthenticationResult:
        """Build a successful result for an already-verified ``user``.

        Assembles the authenticated-user context (a successful
        ``AuthenticationResult`` carrying the user's public representation)
        without re-checking credentials — usable by any verification path
        (password-based today; a future 2FA step could reuse it). Performs no
        database write and creates no session.
        """
        ...


@runtime_checkable
class ISessionService(IService, Protocol):
    """Contract for session record persistence and lifecycle (Phase 3.4)."""

    async def create_session(
        self,
        user_id: uuid.UUID,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_label: str | None = None,
        ttl: timedelta | None = None,
    ) -> SessionResponse:
        """Create and persist a new session row for ``user_id``."""
        ...

    async def get_session(self, session_id: uuid.UUID) -> SessionResponse | None:
        """Return the session record, or ``None`` — a raw lookup, no checks."""
        ...

    async def revoke_session(self, session_id: uuid.UUID) -> None:
        """Mark a single session revoked. Raises ``SessionNotFoundError``."""
        ...

    async def revoke_all_user_sessions(self, user_id: uuid.UUID) -> int:
        """Revoke every active session for a user. Returns rows affected."""
        ...

    async def validate_session(self, session_id: uuid.UUID) -> SessionResponse:
        """Return the session only if it is usable.

        Raises ``SessionNotFoundError`` if it doesn't exist, or
        ``SessionRevokedError`` if it is revoked or expired.
        """
        ...


@runtime_checkable
class IRefreshTokenService(IService, Protocol):
    """Contract for refresh-token persistence and lifecycle (Phase 3.4)."""

    async def persist_refresh_token(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        *,
        rotated_from: uuid.UUID | None = None,
    ) -> tuple[str, RefreshTokenResponse]:
        """Mint a new refresh JWT, extract its claims, and persist a hashed
        record linked to ``user_id``/``session_id``.

        Returns ``(raw_token, record)`` — the raw JWT is handed back to the
        caller but never itself stored or logged; only its hash is
        persisted.
        """
        ...

    async def get_refresh_token(self, token: str) -> RefreshTokenResponse | None:
        """Return the record for ``token`` by its hash, or ``None``."""
        ...

    async def revoke_refresh_token(self, token: str) -> None:
        """Mark a single refresh token revoked. Raises
        ``RefreshTokenNotFoundError``."""
        ...

    async def revoke_all_user_refresh_tokens(self, user_id: uuid.UUID) -> int:
        """Revoke every refresh token for a user. Returns rows affected."""
        ...

    async def validate_refresh_token(self, token: str) -> RefreshTokenResponse:
        """Fully validate ``token`` (JWT + database record state).

        Verifies the JWT itself (signature, expiration, issuer, audience,
        ``type == refresh``, required claims including ``jti``) via the
        injected token service, then checks the database record exists, is
        not revoked, and has not expired at the database level. A revoked
        record being presented again triggers reuse detection, which revokes
        the entire session's token chain before raising
        ``RefreshTokenReuseDetectedError``.
        """
        ...

    async def rotate_refresh_token(
        self, token: str
    ) -> tuple[str, RefreshTokenResponse]:
        """Validate ``token``, revoke it, and issue+persist a replacement.

        One transaction: the old token's revocation and the new token's
        creation are committed together, or not at all.
        """
        ...
