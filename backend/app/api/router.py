"""API router aggregator.

Reconstructed MVP scaffolding — original source unavailable.

MVP Phase 2 scope: health endpoints, mounted at the root (no /api/v1
prefix — there are no versioned domain endpoints to reserve it for). Phase 3
adds the /auth/* routes (register/login/refresh/logout/me).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.trading import router as trading_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(trading_router)
