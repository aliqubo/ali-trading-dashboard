"""Service layer interface (BACKEND_SPEC §5.1).

Defines ``IService``, the structural marker every application service
satisfies. Domain-specific interfaces (e.g. ``IUserService`` in
:mod:`app.services.identity.interfaces`) extend this with their own methods.

Structure only — no logic, no business rules.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.repositories.interfaces import IUnitOfWork


@runtime_checkable
class IService(Protocol):
    """Structural marker for the service layer.

    Per BACKEND_SPEC §5.1, every service is stateless and receives its
    dependencies via injection; the one dependency every service shares is a
    :class:`IUnitOfWork` bound to the current request's database session.
    Domain services reach their repositories through ``self.uow.<repository>``
    and open the unit of work's transaction — ``IService`` itself declares no
    domain methods.
    """

    @property
    def uow(self) -> IUnitOfWork: ...
