"""Authentication service (BACKEND_SPEC §2.2).

Concrete implementation of :class:`IAuthenticationService`: credential
verification only — no JWT, no refresh tokens, no cookies, no session
persistence, no authorization.

Dependencies (constructor-injected, per this phase's explicit scope):
- ``UserRepository`` — reached via the injected unit of work's ``.users``
  property (the Unit of Work owns the transaction and repository registry,
  per Phase 2.4; a repository is never passed around independently of it).
- ``SessionRepository`` — reachable via the unit of work's ``.sessions``
  property, for a future phase's session-persistence flow. Not called
  anywhere in this phase: none of ``authenticate()``/``verify_password()``/
  ``create_authenticated_user()`` create, read, or revoke a session record.
- ``IPasswordHasher`` — injected directly (``password_hasher``), used only to
  verify a candidate password against a stored hash.
- ``SqlAlchemyUnitOfWork`` — injected via :class:`BaseService` (stored as the
  concrete type, not the abstract ``IUnitOfWork``, because this service needs
  the repository registry — ``.users``/``.sessions`` — that only the concrete
  unit of work exposes; ``IUnitOfWork`` intentionally stays domain-agnostic).
- ``logging.Logger`` — injected directly (``logger``), used for structured,
  password-free observability of authentication outcomes.

Failed-login tracking: per DATABASE_DESIGN.md's documented login flow ("عند
النجاح: تحديث last_login_at، تصفير failed_login_count" / "عند الفشل: تحديث
failed_login_count فقط"), a successful authentication resets
``failed_login_count`` and stamps ``last_login_at``; a wrong-password attempt
increments ``failed_login_count``. No audit-log row is written here — audit
logging is not among this phase's allowed dependencies.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from app.core.security.interfaces import IPasswordHasher
from app.models import User
from app.models.enums import UserStatus
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork
from app.services.authentication.results import (
    AuthenticationFailureReason,
    AuthenticationResult,
)
from app.services.base import BaseService
from app.services.identity.dtos import UserResponse


class AuthenticationService(BaseService):
    """Verifies user credentials. Issues no token, cookie, or session."""

    #: Number of consecutive failed attempts after which an account is
    #: reported as locked. A simple, self-contained threshold — no external
    #: lockout-policy configuration exists yet.
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5

    #: How long a lockout lasts, measured from the user row's own
    #: `updated_at` (bumped by the failed-attempt update itself — there is no
    #: dedicated `locked_until` column). Without this, a locked account could
    #: never be unlocked: the lockout check runs before password
    #: verification, so even the correct password would never reach the
    #: reset-on-success path below.
    LOCKOUT_DURATION: timedelta = timedelta(minutes=15)

    #: A verify() target for the unknown-user/disabled/locked branches, which
    #: would otherwise return without ever running Argon2 — letting an
    #: attacker distinguish "no such account" / "disabled" / "locked" from a
    #: genuine wrong-password rejection purely by response latency. Computed
    #: once (first use, any instance — a new service is constructed per
    #: request) and cached at class level.
    _dummy_password_hash: ClassVar[str | None] = None

    def __init__(
        self,
        uow: SqlAlchemyUnitOfWork,
        password_hasher: IPasswordHasher,
        logger: logging.Logger,
    ) -> None:
        super().__init__(uow)
        # Concretely-typed alias for internal repository access (`.users`,
        # `.sessions`) — `self.uow` (inherited from BaseService) stays typed
        # as the abstract `IUnitOfWork` to satisfy the `IService` contract.
        self._uow: SqlAlchemyUnitOfWork = uow
        self._password_hasher = password_hasher
        self._logger = logger

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Return whether ``password`` matches ``password_hash``."""
        return self._password_hasher.verify(password, password_hash)

    def _run_dummy_verify(self, password: str) -> None:
        """Run a real Argon2 verify against a fixed dummy hash.

        Called (and its result discarded) on every early-exit failure branch
        of ``authenticate()`` so each branch costs the same CPU time as a
        genuine wrong-password check below.
        """
        if AuthenticationService._dummy_password_hash is None:
            AuthenticationService._dummy_password_hash = self._password_hasher.hash(
                "not-a-real-password-used-only-to-equalize-timing"
            )
        self.verify_password(password, AuthenticationService._dummy_password_hash)

    async def authenticate(
        self, identifier: str, password: str
    ) -> AuthenticationResult:
        """Verify credentials for the user identified by email or username."""
        user = await self._uow.users.get_by_email(identifier)
        if user is None:
            user = await self._uow.users.get_by_username(identifier)

        if user is None:
            self._run_dummy_verify(password)
            self._logger.info(
                "authentication failed: unknown user",
                extra={"identifier": identifier},
            )
            return AuthenticationResult.failed(AuthenticationFailureReason.UNKNOWN_USER)

        if user.status is not UserStatus.ACTIVE:
            self._run_dummy_verify(password)
            self._logger.warning(
                "authentication failed: user disabled",
                extra={"user_id": str(user.id), "status": user.status.value},
            )
            return AuthenticationResult.failed(
                AuthenticationFailureReason.USER_DISABLED
            )

        if (
            user.failed_login_count >= self.MAX_FAILED_LOGIN_ATTEMPTS
            and datetime.now(UTC) < user.updated_at + self.LOCKOUT_DURATION
        ):
            self._run_dummy_verify(password)
            self._logger.warning(
                "authentication failed: user locked",
                extra={
                    "user_id": str(user.id),
                    "failed_login_count": user.failed_login_count,
                },
            )
            return AuthenticationResult.failed(AuthenticationFailureReason.USER_LOCKED)

        if not self.verify_password(password, user.password_hash):
            await self._uow.users.update(
                user.id, {"failed_login_count": user.failed_login_count + 1}
            )
            await self._uow.commit()
            self._logger.info(
                "authentication failed: wrong password",
                extra={"user_id": str(user.id)},
            )
            return AuthenticationResult.failed(
                AuthenticationFailureReason.WRONG_PASSWORD
            )

        await self._uow.users.update(
            user.id,
            {"failed_login_count": 0, "last_login_at": datetime.now(UTC)},
        )
        await self._uow.commit()
        # Refresh: the update's server-side `onupdate` columns (e.g.
        # `updated_at`) are marked expired after flush/commit, and Pydantic's
        # synchronous attribute access cannot lazily await-load them itself.
        await self._uow.refresh(user)
        self._logger.info("authentication succeeded", extra={"user_id": str(user.id)})
        return self.create_authenticated_user(user)

    def create_authenticated_user(self, user: User) -> AuthenticationResult:
        """Build a successful result for an already-verified ``user``."""
        return AuthenticationResult.succeeded(UserResponse.model_validate(user))
