"""RefreshToken repository (Identity domain).

Data-access for the ``refresh_tokens`` table. No business logic — no token
generation, hashing, rotation policy or validation here; those belong to the
service layer. This repository only reads and writes rows.
"""

from __future__ import annotations

from sqlalchemy import func, select, update

from app.models import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository for :class:`RefreshToken`."""

    model = RefreshToken
    filterable_fields = frozenset({"user_id", "session_id", "is_revoked", "token_hash"})
    sortable_fields = frozenset({"created_at", "expires_at"})

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """Return the token row with the given hash, or ``None``."""
        stmt = (
            select(RefreshToken).where(RefreshToken.token_hash == token_hash).limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_for_user(self, user_id: object) -> list[RefreshToken]:
        """Return all refresh tokens belonging to a user."""
        stmt = select(RefreshToken).where(RefreshToken.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def revoke_all_for_user(self, user_id: object) -> int:
        """Mark all of a user's tokens revoked. Returns rows affected."""
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoked_at=func.now())
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return int(result.rowcount or 0)  # type: ignore[attr-defined]
