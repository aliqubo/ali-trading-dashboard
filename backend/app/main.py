"""FastAPI application entry point.

Wires together configuration, logging, database connections, middlewares,
exception handlers and the API router (ARCHITECTURE.md §2, BACKEND_SPEC §3).
No business logic lives here.

Root ("/"), version and health endpoints are the only routes exposed in this
MVP.

MVP Phase 2 patch — Redis/cache wiring removed (out of this sprint's scope);
router import simplified from `app.api.v1.router` to `app.api.router` (no
v1-prefixed domain endpoints exist yet). See RECOVERY_MANIFEST.md.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db.session import dispose_engine, init_engine
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.request_id import RequestIdMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown of shared resources."""
    settings = get_settings()
    configure_logging(settings)
    logger = get_logger("app.lifespan")

    init_engine(settings)
    logger.info(
        "application.startup name=%s version=%s env=%s",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )

    try:
        yield
    finally:
        await dispose_engine()
        logger.info("application.shutdown")


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Middlewares. Request id is added last so it runs first (outermost).
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    register_exception_handlers(app)

    # Infrastructure endpoints (root, health, version) live at the root only, as
    # defined in SYSTEM_DESIGN.md / BACKEND_SPEC §2.17. The /api/v1 prefix is
    # reserved for domain resources introduced in later phases.
    app.include_router(api_router)

    return app


app = create_app()
