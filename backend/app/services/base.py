"""Base service (BACKEND_SPEC §5.1).

Generic infrastructure shared by every application service: injection of a
:class:`IUnitOfWork` and nothing else. Services are stateless — ``BaseService``
stores only the injected unit of work as an instance attribute. It implements
no business logic, no validation, and no domain methods; domain services (e.g.
``UserService``, added in a later phase) subclass it and implement a
domain-specific interface such as ``IUserService``.

Structure only — no logic.
"""

from __future__ import annotations

from app.repositories.interfaces import IUnitOfWork


class BaseService:
    """Common base for all application services.

    Stores the injected :class:`IUnitOfWork` as ``self.uow``. Subclasses reach
    domain repositories through ``self.uow.<repository>`` and are responsible
    for calling ``commit``/``rollback`` on it as their business flow requires.
    ``BaseService`` itself performs no reads/writes and contains no business
    rules — it only wires the dependency.
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        self.uow = uow
