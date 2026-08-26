"""Session service (Phase 3.4).

Concrete implementation of :class:`ISessionService`: persistence and
lifecycle for ``sessions`` rows only. No JWT issuance (that's
``RefreshTokenService``/``ITokenService``), no login flow, no API.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from app.repositories.unit_of_work import SqlAlchemyUnitOfWork
from app.services.authentication.exceptions import (
    SessionNotFoundError,
    SessionRevokedError,
)
from app.services.base import BaseService
from app.services.identity.dtos import SessionResponse


class SessionService(BaseService):
    """Creates, reads, validates, and revokes session records."""

    def __init__(
        self,
        uow: SqlAlchemyUnitOfWork,
        logger: logging.Logger,
        *,
        default_session_ttl: timedelta,
    ) -> None:
        super().__init__(uow)
        self._uow: SqlAlchemyUnitOfWork = uow
        self._logger = logger
        self._default_session_ttl = default_session_ttl

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
        now = datetime.now(UTC)
        row = await self._uow.sessions.create(
            {
                "user_id": user_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "device_label": device_label,
                "is_active": True,
                "expires_at": now
                + (self._default_session_ttl if ttl is None else ttl),
            }
        )
        await self._uow.commit()
        await self._uow.refresh(row)
        self._logger.info(
            "session created",
            extra={"user_id": str(user_id), "session_id": str(row.id)},
        )
        return SessionResponse.model_validate(row)

    async def get_session(self, session_id: uuid.UUID) -> SessionResponse | None:
        """Return the session record, or ``None`` — a raw lookup, no checks."""
        row = await self._uow.sessions.get_by_id(session_id)
        return SessionResponse.model_validate(row) if row is not None else None

    async def revoke_session(self, session_id: uuid.UUID) -> None:
        """Mark a single session revoked."""
        row = await self._uow.sessions.get_by_id(session_id)
        if row is None:
            raise SessionNotFoundError()
        await self._uow.sessions.update(
            session_id, {"is_active": False, "revoked_at": datetime.now(UTC)}
        )
        await self._uow.commit()
        self._logger.info("session revoked", extra={"session_id": str(session_id)})

    async def revoke_all_user_sessions(self, user_id: uuid.UUID) -> int:
        """Revoke every active session for a user. Returns rows affected."""
        count = await self._uow.sessions.revoke_all_user_sessions(user_id)
        await self._uow.commit()
        self._logger.info(
            "all sessions revoked for user",
            extra={"user_id": str(user_id), "count": count},
        )
        return count

    async def validate_session(self, session_id: uuid.UUID) -> SessionResponse:
        """Return the session only if it is active, not revoked, not expired."""
        row = await self._uow.sessions.get_by_id(session_id)
        if row is None:
            raise SessionNotFoundError()

        now = datetime.now(UTC)
        if not row.is_active or row.revoked_at is not None or row.expires_at <= now:
            raise SessionRevokedError()

        return SessionResponse.model_validate(row)
