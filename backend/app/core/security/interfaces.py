"""Password security interfaces.

Structural contracts (typing Protocols) for password hashing and password
validation. ``IPasswordHasher`` has a concrete implementation in this phase
(:class:`app.core.security.password_hasher.PasswordHasher`);
``IPasswordValidator`` is contract-only — no implementation exists yet, and
none is added until a later phase.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.security.policy import PasswordPolicy


@runtime_checkable
class IPasswordHasher(Protocol):
    """Contract for hashing and verifying passwords.

    Implementations never store or return plaintext; ``hash()`` returns an
    opaque, self-describing hash string that ``verify()``/``needs_rehash()``
    can later interpret without any external parameter tracking.
    """

    def hash(self, password: str) -> str:
        """Return a salted hash of ``password``."""
        ...

    def verify(self, password: str, hashed: str) -> bool:
        """Return whether ``password`` matches the given ``hashed`` value."""
        ...

    def needs_rehash(self, hashed: str) -> bool:
        """Return whether ``hashed`` was produced with outdated parameters.

        Lets a caller re-hash a verified password on next successful login
        when the hasher's configured cost parameters have since increased,
        without forcing every existing hash to be invalidated at once.
        """
        ...


@runtime_checkable
class IPasswordValidator(Protocol):
    """Contract for validating a password against a policy.

    An implementation (added in a later phase) inspects a candidate password
    against a :class:`PasswordPolicy` and raises a password exception
    (``InvalidPasswordException``, ``WeakPasswordException``) when a rule is
    violated. No implementation exists yet — this is the contract only.
    """

    def validate(self, password: str, policy: PasswordPolicy) -> None:
        """Validate ``password`` against ``policy``, raising on failure."""
        ...
