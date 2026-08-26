"""Authorization exceptions.

Only two new exception types are defined here — ``RoleNotFoundError`` and
``PermissionNotFoundError``. The "user lacks this grant" outcome reuses the
existing ``app.core.exceptions.ForbiddenError`` (defined in Phase 1) rather
than redefining it, per this phase's explicit instruction not to duplicate
existing exceptions.

The distinction this module draws:
- **The role/permission *concept* does not exist** in the system at all
  (e.g. a typo'd role name in calling code) → ``RoleNotFoundError`` /
  ``PermissionNotFoundError``. This is a caller/configuration error, not a
  security event.
- **The role/permission concept exists, but this user was not granted it**
  → ``ForbiddenError`` (reused, unchanged). This is the actual
  authorization-denial outcome.

Per this phase's security rules, no exception here reveals which specific
role/permission was checked in its externally-visible message — that detail
is only ever written to the internal logger (see ``authorization_service``).
"""

from __future__ import annotations

from app.core.exceptions import NotFoundError


class RoleNotFoundError(NotFoundError):
    """No role with the given name exists in the system."""

    code = "role_not_found"
    message = "The role was not found."


class PermissionNotFoundError(NotFoundError):
    """No permission with the given code exists in the system."""

    code = "permission_not_found"
    message = "The permission was not found."
