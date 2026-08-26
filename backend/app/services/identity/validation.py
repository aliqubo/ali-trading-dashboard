"""Identity domain validation contracts (BACKEND_SPEC §5.3).

Defines the *shape* of business validation for identity DTOs — structural
contracts only. No concrete rule is implemented here.

Structural (type/field) validation — required fields, string lengths, email
format — is already handled by Pydantic on the DTOs in :mod:`dtos`
(BACKEND_SPEC §5.3, "تحقق بنيوي"). These contracts are for the *business*-level
checks that belong in the service layer ("تحقق منطقي") — e.g. uniqueness,
cross-field rules — which have no implementation yet and are deferred to a
later phase.
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from app.services.identity.dtos import CreateUserRequest, UpdateUserRequest

T = TypeVar("T", contravariant=True)


@runtime_checkable
class IValidator(Protocol[T]):
    """Contract for a business validator of a given input type.

    An implementation (added in a later phase) inspects ``data`` and raises a
    business exception if a rule that cannot be expressed by the DTO's field
    types is violated. No implementation exists yet; this is the contract
    only.
    """

    def validate(self, data: T) -> None: ...


class ICreateUserValidator(IValidator[CreateUserRequest], Protocol):
    """Contract for business validation of :class:`CreateUserRequest`.

    Example of a future business rule this would enforce: email/username
    uniqueness — not implemented here.
    """


class IUpdateUserValidator(IValidator[UpdateUserRequest], Protocol):
    """Contract for business validation of :class:`UpdateUserRequest`."""
