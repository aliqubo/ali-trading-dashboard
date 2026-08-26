"""Application logging (ARCHITECTURE.md §8).

Reconstructed MVP scaffolding — original source unavailable.

Configures structured JSON logging with the current request id attached to
every record via a filter reading from app.core.context.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import TYPE_CHECKING, Any

from app.core.context import get_request_id

if TYPE_CHECKING:
    from app.core.config import Settings


class RequestIdFilter(logging.Filter):
    """Attach the current request id (if any) to each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()  # type: ignore[attr-defined]
        return True


class JsonFormatter(logging.Formatter):
    """Render each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


_configured = False


def configure_logging(settings: Settings) -> None:
    """Configure the root logger once per process."""
    global _configured
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    if settings.log_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )

    root.addHandler(handler)
    root.setLevel(settings.log_level)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger."""
    return logging.getLogger(name)
