"""ORM models package (MVP scope).

Reconstructed MVP scaffolding — original source unavailable in this trimmed
form. The archived version of this aggregator (files2.zip) imports 11 domain
modules covering all 55 tables; this MVP only restores identity.py and
trading.py, so only those two are aggregated here. See RECOVERY_MANIFEST.md.
"""

from __future__ import annotations

from app.models.base import Base
from app.models.identity import (
    ApiKey,
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    Session,
    User,
    UserRole,
)
from app.models.trading import (
    Execution,
    Order,
    OrderHistory,
    Position,
    PositionHistory,
    Trade,
)

__all__ = [
    "Base",
    # Identity
    "User",
    "Role",
    "Permission",
    "RolePermission",
    "UserRole",
    "Session",
    "RefreshToken",
    "ApiKey",
    # Trading
    "Order",
    "OrderHistory",
    "Execution",
    "Position",
    "PositionHistory",
    "Trade",
]
