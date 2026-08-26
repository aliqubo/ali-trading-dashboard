"""Reusable column mixins.

Encodes the shared conventions from DATABASE_DESIGN.md §"اصطلاحات التصميم":

- ``UUIDPrimaryKeyMixin``   : ``id UUID PK DEFAULT gen_random_uuid()`` (default PK).
- ``BigIntPrimaryKeyMixin`` : ``id BIGINT`` identity PK for high-volume/time tables.
- ``TimestampMixin``        : ``created_at`` / ``updated_at`` (TIMESTAMPTZ, now()).
- ``CreatedAtMixin``        : ``created_at`` only (for append-only/log-like tables).
- ``SoftDeleteMixin``       : nullable ``deleted_at`` for soft delete.

Structure only — no logic.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, func, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """UUID primary key defaulting to gen_random_uuid() (server-side)."""

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


class BigIntPrimaryKeyMixin:
    """BIGINT identity primary key for high-volume tables.

    Tables that are RANGE-partitioned in DATABASE_DESIGN.md override the primary
    key to be composite ``(id, <partition_key>)``; this mixin supplies the
    ``id`` identity column used in that composite key.
    """

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )


class TimestampMixin:
    """created_at / updated_at audit columns (TIMESTAMPTZ, server now())."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CreatedAtMixin:
    """created_at only, for append-only / history / log tables."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class SoftDeleteMixin:
    """Nullable deleted_at column for soft deletion."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
