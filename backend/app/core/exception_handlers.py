"""Global exception handlers.

Convert every exception into the unified error envelope
(ARCHITECTURE.md §7.1, BACKEND_SPEC §9). Internal details of unexpected errors
are never leaked to the client.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.context import get_request_id
from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger("app.errors")


def _error_body(
    code: str,
    message: str,
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": get_request_id(),
        }
    }


async def app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Handle known application errors."""
    if not isinstance(exc, AppError):
        # Defensive fallback: this handler is only registered for AppError, but
        # narrow the type explicitly rather than relying on `assert` (which is
        # stripped under `python -O`).
        return await unhandled_error_handler(_, exc)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, exc.details),
    )


async def validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Handle request validation errors as 422."""
    if not isinstance(exc, RequestValidationError):
        return await unhandled_error_handler(_, exc)
    return JSONResponse(
        status_code=422,
        content=_error_body(
            "validation_error",
            "The request failed validation.",
            {"errors": exc.errors()},
        ),
    )


async def http_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Handle framework HTTP exceptions in the unified shape."""
    if not isinstance(exc, StarletteHTTPException):
        return await unhandled_error_handler(_, exc)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body("http_error", str(exc.detail)),
    )


async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Handle any unexpected error as 500 without leaking internals."""
    logger.exception("unhandled.exception")
    return JSONResponse(
        status_code=500,
        content=_error_body(
            "internal_error",
            "An internal error occurred.",
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the app."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
