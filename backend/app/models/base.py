"""Declarative base and metadata.

The single ``Base`` for all ORM models (ARCHITECTURE.md §6, BACKEND_SPEC §7.5).
Uses SQLAlchemy 2.x typed ORM (``DeclarativeBase`` + ``Mapped``) and an explicit
naming convention so constraints and indexes get deterministic names, which is
important for Alembic in the next phase.

This module defines structure only — no business logic, no queries.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Deterministic naming convention for constraints and indexes.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
