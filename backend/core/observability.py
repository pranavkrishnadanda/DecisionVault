"""Observability primitives for structured logging and tracing context."""

from __future__ import annotations

import contextvars
import json
import logging
from datetime import datetime, timezone
from typing import Any

REQUEST_ID_VAR: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
CORRELATION_ID_VAR: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)


def set_request_id(request_id: str | None):
    """Store request id in context and return token for reset."""
    return REQUEST_ID_VAR.set(request_id)


def get_request_id() -> str | None:
    """Get request id from context."""
    return REQUEST_ID_VAR.get()


def set_correlation_id(correlation_id: str | None):
    """Store correlation id in context and return token for reset."""
    return CORRELATION_ID_VAR.set(correlation_id)


def get_correlation_id() -> str | None:
    """Get correlation id from context."""
    return CORRELATION_ID_VAR.get()


def reset_context(token: contextvars.Token) -> None:
    """Reset a context variable token."""
    token.var.reset(token)


class ContextFilter(logging.Filter):
    """Inject context ids into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()
        if not hasattr(record, "correlation_id"):
            record.correlation_id = get_correlation_id()
        return True


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logs."""

    _EXTRA_FIELDS = (
        "request_id",
        "correlation_id",
        "decision_id",
        "queue",
        "path",
        "method",
        "user_id",
        "status_code",
        "duration_ms",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "correlation_id": getattr(record, "correlation_id", None),
        }

        for key in self._EXTRA_FIELDS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)
