"""Refresh token service (Phase 3.4).

Concrete implementation of :class:`IRefreshTokenService`: JWT issuance
(delegated to ``ITokenService``, Phase 3.3) plus persistence, validation,
rotation, and revocation of the corresponding ``refresh_tokens`` row.

Security notes:
- The raw JWT is **never** persisted or logged — only ``sha256(token)`` is
  stored, in ``token_hash`` (DATABASE_DESIGN.md: "مجزّأ، لا يُخزّن صريحاً").
  SHA-256 (not Argon2id) is the correct choice here: refresh tokens are
  high-entropy, machine-generated strings — never user-memorized — so a
  fast, *deterministic* cryptographic hash is appropriate (it also permits
  direct lookup by hash equality via the ``token_hash`` unique index, which
  a randomly-salted hash would not allow). Argon2id (Phase 3.1) is
  deliberately slow/memory-hard specifically to resist brute-forcing
  low-entropy, human-chosen passwords — a mismatched, wasteful choice for an
  already-unguessable token.
- Reuse detection (BACKEND_SPEC §8.2): presenting a refresh token whose
  record is already marked revoked revokes the *entire* session's
  refresh-token chain and the session itself, before raising
  ``RefreshTokenReuseDetectedError``.
- All mutating flows (persist, revoke, rotate, reuse-triggered cascade)
  commit exactly once, at the end, after every write has been flushed
  successfully — if any step raises, nothing commits and the unit of work's
  ``__aexit__`` rolls back automatically (Phase 2.4).
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime

from app.core.security.token import ITokenService, TokenType
from app.repositories.types import MAX_PAGE_SIZE, Filter, FilterOperator, Pagination
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork
from app.services.authentication.exceptions import (
    RefreshTokenExpiredError,
    RefreshTokenNotFoundError,
    RefreshTokenReuseDetectedError,
    SessionRevokedError,
)
from app.services.authentication.token_records import RefreshTokenResponse
from app.services.base import BaseService


def _hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a refresh token, for hashed storage.

    See the module docstring's security note for why SHA-256 (not Argon2id)
    is the correct algorithm for this specific value.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RefreshTokenService(BaseService):
    """Issues, persists, validates, rotates, and revokes refresh tokens."""

    def __init__(
        self,
        uow: SqlAlchemyUnitOfWork,
        token_service: ITokenService,
        logger: logging.Logger,
    ) -> None:
        super().__init__(uow)
        self._uow: SqlAlchemyUnitOfWork = uow
        self._token_service = token_service
        self._logger = logger

    async def persist_refresh_token(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        *,
        rotated_from: uuid.UUID | None = None,
    ) -> tuple[str, RefreshTokenResponse]:
        """Mint a new refresh JWT, extract its claims, and persist a hashed
        record linked to ``user_id``/``session_id``."""
        raw_token = self._token_service.create_refresh_token(str(user_id))
        claims = self._token_service.decode_token(raw_token)

        row = await self._uow.refresh_tokens.create(
            {
                "user_id": user_id,
                "session_id": session_id,
                "token_hash": _hash_token(raw_token),
                "expires_at": claims.exp,
                "rotated_from": rotated_from,
            }
        )
        await self._uow.commit()
        await self._uow.refresh(row)
        self._logger.info(
            "refresh token persisted",
            extra={
                "user_id": str(user_id),
                "session_id": str(session_id),
                "jti": claims.jti,
            },
        )
        return raw_token, RefreshTokenResponse.model_validate(row)

    async def get_refresh_token(self, token: str) -> RefreshTokenResponse | None:
        """Return the record for ``token`` by its hash, or ``None``."""
        row = await self._uow.refresh_tokens.get_by_token_hash(_hash_token(token))
        return RefreshTokenResponse.model_validate(row) if row is not None else None

    async def revoke_refresh_token(self, token: str) -> None:
        """Mark a single refresh token revoked."""
        row = await self._uow.refresh_tokens.get_by_token_hash(_hash_token(token))
        if row is None:
            raise RefreshTokenNotFoundError()
        await self._uow.refresh_tokens.update(
            row.id, {"is_revoked": True, "revoked_at": datetime.now(UTC)}
        )
        await self._uow.commit()
        self._logger.info(
            "refresh token revoked",
            extra={"user_id": str(row.user_id), "session_id": str(row.session_id)},
        )

    async def revoke_all_user_refresh_tokens(self, user_id: uuid.UUID) -> int:
        """Revoke every refresh token for a user. Returns rows affected."""
        count = await self._uow.refresh_tokens.revoke_all_for_user(user_id)
        await self._uow.commit()
        self._logger.info(
            "all refresh tokens revoked for user",
            extra={"user_id": str(user_id), "count": count},
        )
        return count

    async def validate_refresh_token(self, token: str) -> RefreshTokenResponse:
        """Fully validate ``token`` (JWT itself, then the database record)."""
        # 1. JWT-level validation: signature, exp, iss, aud, type=refresh,
        #    and every required claim (including jti) present.
        claims = self._token_service.validate_token(token, TokenType.REFRESH)

        # 2. Database record must exist.
        row = await self._uow.refresh_tokens.get_by_token_hash(_hash_token(token))
        if row is None:
            raise RefreshTokenNotFoundError()

        # 3. Reuse detection: an already-revoked record being presented again
        #    means it was already rotated/used — treat as possible theft and
        #    revoke the whole session chain before rejecting this attempt.
        if row.is_revoked:
            await self._revoke_session_chain(row.session_id)
            self._logger.warning(
                "refresh token reuse detected",
                extra={
                    "user_id": str(row.user_id),
                    "session_id": str(row.session_id),
                    "jti": claims.jti,
                },
            )
            raise RefreshTokenReuseDetectedError()

        # 4. Database-level expiry — independent of (defense in depth beyond)
        #    the JWT's own `exp` claim already checked in step 1.
        if row.expires_at <= datetime.now(UTC):
            raise RefreshTokenExpiredError()

        # 5. The token's own record can be perfectly valid while the session
        #    it belongs to has been revoked (e.g. via SessionService.
        #    revoke_session/revoke_all_user_sessions, which only ever touches
        #    the `sessions` row) — without this check, "log out"/"revoke all
        #    sessions" would not actually stop this refresh token from
        #    minting new access tokens.
        if row.session_id is not None:
            session = await self._uow.sessions.get_by_id(row.session_id)
            now = datetime.now(UTC)
            if (
                session is None
                or not session.is_active
                or session.revoked_at is not None
                or session.expires_at <= now
            ):
                raise SessionRevokedError()

        return RefreshTokenResponse.model_validate(row)

    async def rotate_refresh_token(
        self, token: str
    ) -> tuple[str, RefreshTokenResponse]:
        """Validate ``token``, revoke it, and issue+persist a replacement.

        One transaction: revoking the old record and creating the new one
        are committed together, or not at all.
        """
        old_record = await self.validate_refresh_token(token)

        await self._uow.refresh_tokens.update(
            old_record.id, {"is_revoked": True, "revoked_at": datetime.now(UTC)}
        )

        raw_new_token = self._token_service.create_refresh_token(
            str(old_record.user_id)
        )
        new_claims = self._token_service.decode_token(raw_new_token)
        new_row = await self._uow.refresh_tokens.create(
            {
                "user_id": old_record.user_id,
                "session_id": old_record.session_id,
                "token_hash": _hash_token(raw_new_token),
                "expires_at": new_claims.exp,
                "rotated_from": old_record.id,
            }
        )
        await self._uow.commit()
        await self._uow.refresh(new_row)
        self._logger.info(
            "refresh token rotated",
            extra={
                "user_id": str(old_record.user_id),
                "session_id": str(old_record.session_id),
                "jti": new_claims.jti,
            },
        )
        return raw_new_token, RefreshTokenResponse.model_validate(new_row)

    async def _revoke_session_chain(self, session_id: uuid.UUID | None) -> None:
        """Revoke every refresh token under ``session_id``, and the session.

        Uses only generic, already-established repository capabilities
        (``get_many`` with an allow-listed ``session_id`` filter, plus the
        generic ``update()``) — no repository contract change was needed.
        """
        if session_id is None:
            return

        page = await self._uow.refresh_tokens.get_many(
            filters=[Filter("session_id", FilterOperator.EQ, session_id)],
            pagination=Pagination(limit=MAX_PAGE_SIZE),
        )
        now = datetime.now(UTC)
        for token_row in page.items:
            if not token_row.is_revoked:
                await self._uow.refresh_tokens.update(
                    token_row.id, {"is_revoked": True, "revoked_at": now}
                )
        await self._uow.sessions.update(
            session_id, {"is_active": False, "revoked_at": now}
        )
        await self._uow.commit()
