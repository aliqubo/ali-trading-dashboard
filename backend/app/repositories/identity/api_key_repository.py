"""ApiKey repository (Identity domain).

Data-access for the ``api_keys`` table. No business logic — no key generation,
hashing or scope evaluation; only reads and writes.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select

from app.models import ApiKey
from app.repositories.base import BaseRepository


class ApiKeyRepository(BaseRepository[ApiKey]):
    """Repository for :class:`ApiKey`."""

    model = ApiKey
    filterable_fields = frozenset({"user_id", "is_active", "key_prefix", "key_hash"})
    sortable_fields = frozenset({"created_at", "last_used_at", "expires_at"})

    async def get_by_key_hash(self, key_hash: str) -> ApiKey | None:
        """Return the API key row with the given hash, or ``None``."""
        stmt = select(ApiKey).where(ApiKey.key_hash == key_hash).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_active_keys(self, user_id: object) -> list[ApiKey]:
        """Return a user's keys flagged active and not past expiry.

        Both conditions are read from stored columns; no policy is applied.
        """
        stmt = (
            select(ApiKey)
            .where(
                ApiKey.user_id == user_id,
                ApiKey.is_active.is_(True),
                or_(ApiKey.expires_at.is_(None), ApiKey.expires_at > func.now()),
            )
            .order_by(ApiKey.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
