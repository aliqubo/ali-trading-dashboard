"""Refresh-token persistence record DTO (Phase 3.4).

Public representation of a ``refresh_tokens`` row. No ``token_hash`` and no
raw token value ever appear here — only metadata safe to hold in memory or
pass between internal callers.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RefreshTokenResponse(BaseModel):
    """Public representation of a refresh-token record (no hash, no secret)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    session_id: uuid.UUID | None
    is_revoked: bool
    expires_at: datetime
    rotated_from: uuid.UUID | None
    created_at: datetime
    revoked_at: datetime | None
