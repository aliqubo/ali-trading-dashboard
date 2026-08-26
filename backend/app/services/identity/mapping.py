"""Identity domain mapping contracts.

Defines the *shape* of mapping between ORM models and DTOs — structural
contracts only. No mapping logic (field-by-field conversion) is implemented
here; that is deferred to a later phase.
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from app.models import ApiKey, Permission, Role, Session, User
from app.services.identity.dtos import (
    ApiKeyResponse,
    PermissionResponse,
    RoleResponse,
    SessionResponse,
    UserResponse,
)

TSource = TypeVar("TSource", contravariant=True)
TTarget = TypeVar("TTarget", covariant=True)


@runtime_checkable
class IMapper(Protocol[TSource, TTarget]):
    """Contract for mapping a source object to a target representation.

    An implementation (added in a later phase) converts ``source`` into a
    ``TTarget`` instance. No mapping logic exists yet; this is the contract
    only.
    """

    def map(self, source: TSource) -> TTarget: ...


class IUserMapper(IMapper[User, UserResponse], Protocol):
    """Contract for mapping a :class:`User` model to :class:`UserResponse`."""


class IRoleMapper(IMapper[Role, RoleResponse], Protocol):
    """Contract for mapping a :class:`Role` model to :class:`RoleResponse`."""


class IPermissionMapper(IMapper[Permission, PermissionResponse], Protocol):
    """Contract for mapping :class:`Permission` to :class:`PermissionResponse`."""


class ISessionMapper(IMapper[Session, SessionResponse], Protocol):
    """Contract for mapping a :class:`Session` model to :class:`SessionResponse`."""


class IApiKeyMapper(IMapper[ApiKey, ApiKeyResponse], Protocol):
    """Contract for mapping an :class:`ApiKey` model to :class:`ApiKeyResponse`."""
