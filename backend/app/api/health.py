"""Health and system endpoints (BACKEND_SPEC §2.17 / SYSTEM_DESIGN.md).

Reconstructed MVP scaffolding — original source unavailable.

MVP Phase 2 note: only a database check is performed for readiness. The
original design (per PROJECT_AUDIT_REPORT.md) also checked Redis; Redis/cache
is out of scope for this sprint, so /health/ready and /health here reflect
database connectivity only. See RECOVERY_MANIFEST.md.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import DbSessionDep, SettingsDep

router = APIRouter()


@router.get("/")
async def root(settings: SettingsDep) -> dict[str, str]:
    """Service identity."""
    return {"name": settings.app_name, "version": settings.app_version}


@router.get("/version")
async def version(settings: SettingsDep) -> dict[str, str]:
    """Version and environment."""
    return {"version": settings.app_version, "environment": settings.environment}


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    """Liveness — the process is running. No external dependency checked."""
    return {"status": "ok"}


async def _database_check(session: DbSessionDep) -> JSONResponse:
    try:
        await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - readiness must not leak internal errors
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "checks": {"database": "down"}},
        )
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "checks": {"database": "up"}},
    )


@router.get("/health/ready")
async def health_ready(session: DbSessionDep) -> JSONResponse:
    """Readiness — checks the database is reachable."""
    return await _database_check(session)


@router.get("/health")
async def health(session: DbSessionDep) -> JSONResponse:
    """Overall health — currently equivalent to readiness."""
    return await _database_check(session)
