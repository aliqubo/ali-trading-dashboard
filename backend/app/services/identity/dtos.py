"""Identity domain DTOs.

Data-only request/response contracts for the Identity domain, expressed as
Pydantic models. Structural (type/field) validation is whatever Pydantic
itself performs (BACKEND_SPEC §5.3); no business-rule validation and no
mapping logic live here — see :mod:`validation` and :mod:`mapping` for those
*contracts* (also structure-only in this phase).

Deliberately excluded, per DATABASE_DESIGN.md §2.1/§2.2 module boundaries and
this phase's restrictions:
- No password field anywhere (password hashing/verification is
  Authentication's responsibility, not Identity's, and is out of scope for
  this phase).
- No API key secret/creation fields (key generation and hashing are deferred
  to the Authentication domain in a later phase).
- Sensitive stored values (``password_hash``, ``two_factor_secret``,
  ``key_hash``) are never exposed on a response DTO.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from ipaddress import IPv4Address, IPv6Address

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CreateUserRequest(BaseModel):
    """Request to create a user account (Identity's own account creation).

    No password: provisioning credentials is Authentication's flow, not
    Identity's, and is out of scope for this phase.
    """

    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    locale: str = Field(default="en", max_length=10)
    timezone: str = Field(default="UTC", max_length=64)


class UpdateUserRequest(BaseModel):
    """Request to update a user's own profile fields.

    Only fields Identity owns per DATABASE_DESIGN.md §2.1 (profile, email
    activation flag, locale/timezone) — no status, no credentials, no roles.
    All fields are optional; omitted fields are left unchanged.
    """

    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    is_email_verified: bool | None = None
    locale: str | None = Field(default=None, max_length=10)
    timezone: str | None = Field(default=None, max_length=64)


class UserResponse(BaseModel):
    """Public representation of a user (no credentials or 2FA secret)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    full_name: str | None
    phone: str | None
    status: str
    is_email_verified: bool
    two_factor_enabled: bool
    locale: str
    timezone: str
    created_at: datetime
    updated_at: datetime


class RoleResponse(BaseModel):
    """Public representation of a role."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    is_system: bool
    created_at: datetime


class PermissionResponse(BaseModel):
    """Public representation of a permission."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    resource: str
    action: str
    description: str | None


class SessionResponse(BaseModel):
    """Public representation of a session record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    ip_address: str | None
    user_agent: str | None
    device_label: str | None
    is_active: bool
    expires_at: datetime
    last_seen_at: datetime | None
    created_at: datetime

    @field_validator("ip_address", mode="before")
    @classmethod
    def _coerce_ip_address(cls, value: object) -> object:
        """Coerce the driver-level INET type to ``str``.

        The ``postgresql.INET`` column decodes to an ``ipaddress.IPv4Address``/
        ``IPv6Address`` at the driver level (psycopg/asyncpg), not ``str``,
        regardless of the ORM's ``Mapped[str | None]`` annotation.
        """
        if isinstance(value, IPv4Address | IPv6Address):
            return str(value)
        return value


class ApiKeyResponse(BaseModel):
    """Public representation of an API key record (no secret/hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    key_prefix: str
    scopes: list[str] | dict[str, object] | None
    is_active: bool
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
