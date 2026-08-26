"""Request-scoped context (ARCHITECTURE.md §8).

Reconstructed MVP scaffolding — original source unavailable.

Holds the current request's id in a contextvar so logging and exception
handling can read it without threading it through every function call.
"""

from __future__ import annotations

from contextvars import ContextVar

_request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(request_id: str) -> None:
    """Bind the given request id to the current context."""
    _request_id_ctx_var.set(request_id)


def get_request_id() -> str | None:
    """Return the current request's id, or ``None`` outside a request."""
    return _request_id_ctx_var.get()
