"""Logging setup for shenas-net-api.

Uses the same _CloudJsonFormatter as the main app for structured JSON
logging in production (SHENAS_JSON_LOGS=1). Falls back to a concise
text format for local development.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import ClassVar


class _CloudJsonFormatter(logging.Formatter):
    """JSON formatter for Google Cloud Logging and Error Reporting."""

    _SEVERITY: ClassVar[dict[str, str]] = {
        "DEBUG": "DEBUG",
        "INFO": "INFO",
        "WARNING": "WARNING",
        "ERROR": "ERROR",
        "CRITICAL": "CRITICAL",
    }

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if record.exc_info and record.exc_info[1] is not None:
            tb = self.formatException(record.exc_info)
            message = f"{message}\n{tb}"

        entry: dict[str, object] = {
            "severity": self._SEVERITY.get(record.levelname, "DEFAULT"),
            "message": message,
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "logging.googleapis.com/sourceLocation": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            },
            "logging.googleapis.com/labels": {"logger": record.name},
        }
        return json.dumps(entry, default=str)


def init_logging() -> None:
    """Configure root logging for the API server."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Don't add duplicate handlers on reload
    if any(getattr(h, "_shenas_api", False) for h in root.handlers):
        return

    handler = logging.StreamHandler()
    handler._shenas_api = True  # type: ignore[attr-defined]

    if os.environ.get("SHENAS_JSON_LOGS", "") == "1":
        handler.setFormatter(_CloudJsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%H:%M:%S"))

    root.addHandler(handler)

    # Quiet down noisy libraries
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("authlib").setLevel(logging.WARNING)
