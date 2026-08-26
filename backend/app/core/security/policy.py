"""Password policy framework.

Defines :class:`PasswordPolicy` — a pure configuration/data holder describing
length bounds, required character classes, and a minimum entropy threshold —
plus :func:`estimate_entropy_bits`, a generic (non-domain-specific) entropy
calculation utility.

This module is a *framework*, not a business policy: ``PasswordPolicy``
ships with fully permissive defaults (nothing required) so that no particular
strength requirement is imposed here. A concrete business policy (e.g. "at
least 12 characters for trading accounts") is a decision for a later phase /
the configuration layer, not for this framework class. Likewise, this module
makes no pass/fail decision — that is the responsibility of the (unimplemented
in this phase) ``IPasswordValidator``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


class CharacterClass(str, Enum):
    """A category of character a password may be required to contain."""

    UPPERCASE = "uppercase"
    LOWERCASE = "lowercase"
    DIGIT = "digit"
    SPECIAL = "special"


@dataclass(frozen=True, slots=True)
class PasswordPolicy:
    """Configurable password policy parameters.

    A plain data holder — it does not validate or enforce anything itself.
    Every field defaults to the most permissive value (no length limit beyond
    a generous ceiling, no required character class, no entropy floor), so
    using the framework's defaults imposes no business policy of its own;
    callers set the fields that reflect their actual requirements.

    Attributes:
        minimum_length: Smallest acceptable password length, in characters.
        maximum_length: Largest acceptable password length, in characters
            (a ceiling exists because most hashing algorithms, including
            Argon2id, have practical/DoS-safety input-length limits).
        required_classes: Character classes that must each appear at least
            once. Empty means no class is required.
        minimum_entropy_bits: Minimum estimated entropy (see
            :func:`estimate_entropy_bits`) a password must reach, or ``None``
            to not enforce an entropy floor.
    """

    minimum_length: int = 1
    maximum_length: int = 128
    required_classes: frozenset[CharacterClass] = field(default_factory=frozenset)
    minimum_entropy_bits: float | None = None


def estimate_entropy_bits(password: str) -> float:
    """Estimate a password's entropy in bits from its character-pool size.

    Generic, domain-independent formula: ``length * log2(pool_size)``, where
    ``pool_size`` is the size of the union of character classes actually
    present in ``password`` (lowercase, uppercase, digits, a fixed-size
    "special/other" pool). This is a standard, well-known estimation method,
    not a business rule — it makes no accept/reject decision.

    Returns 0.0 for an empty password.
    """
    if not password:
        return 0.0

    pool_size = 0
    if any(c.islower() for c in password):
        pool_size += 26
    if any(c.isupper() for c in password):
        pool_size += 26
    if any(c.isdigit() for c in password):
        pool_size += 10
    if any(not c.isalnum() for c in password):
        pool_size += 32  # common punctuation/symbol pool

    if pool_size == 0:
        return 0.0

    return len(password) * math.log2(pool_size)
