"""Argon2id password hasher.

Concrete implementation of :class:`app.core.security.interfaces.
IPasswordHasher` using Argon2id (via ``argon2-cffi``) — the OWASP-recommended
default algorithm for password hashing (ARCHITECTURE.md §9.1: passwords are
hashed with a strong algorithm and never stored in plaintext). bcrypt is
intentionally not used, per this phase's explicit instruction.
"""

from __future__ import annotations

from argon2 import PasswordHasher as _Argon2PasswordHasher
from argon2 import exceptions as argon2_exceptions
from argon2.low_level import Type as _Argon2Type


class PasswordHasher:
    """Argon2id-backed password hasher.

    Wraps ``argon2.PasswordHasher`` pinned to the Argon2id variant with
    explicit cost parameters. No plaintext password is ever logged, stored,
    or returned by any method here; ``hash()`` yields a single
    self-describing string encoding the algorithm, version, and cost
    parameters, so ``verify()``/``needs_rehash()`` require no external
    parameter bookkeeping.
    """

    def __init__(
        self,
        *,
        time_cost: int = 3,
        memory_cost: int = 65536,  # 64 MiB
        parallelism: int = 4,
        hash_len: int = 32,
        salt_len: int = 16,
    ) -> None:
        self._hasher = _Argon2PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len,
            type=_Argon2Type.ID,  # Argon2id, never bcrypt.
        )

    def hash(self, password: str) -> str:
        """Return an Argon2id hash of ``password``."""
        return self._hasher.hash(password)

    def verify(self, password: str, hashed: str) -> bool:
        """Return whether ``password`` matches ``hashed``.

        Returns ``False`` for a mismatch or a malformed/unrecognized hash
        string rather than raising, so callers can treat any verification
        failure uniformly.
        """
        try:
            return self._hasher.verify(hashed, password)
        except argon2_exceptions.VerifyMismatchError:
            return False
        except argon2_exceptions.InvalidHashError:
            return False

    def needs_rehash(self, hashed: str) -> bool:
        """Return whether ``hashed`` was produced with outdated parameters.

        Lets a caller re-hash a password (after a successful ``verify()``) on
        next login when this hasher's configured cost parameters have since
        increased, without invalidating every existing hash at once.
        """
        return self._hasher.check_needs_rehash(hashed)
