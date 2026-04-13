"""Initialize OpenTelemetry with DuckDB exporters."""

from __future__ import annotations

import atexit
import logging
import threading
from typing import ClassVar

from opentelemetry import trace
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler  # type: ignore[attr-defined]
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor  # type: ignore[attr-defined]
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.jobs import JobIdLogFilter
from app.telemetry.exporters import DuckDBLogExporter, DuckDBSpanExporter
from app.telemetry.processors import DispatchingLogProcessor, DispatchingSpanProcessor


class _CloudJsonFormatter(logging.Formatter):
    """JSON formatter for Google Cloud Logging and Error Reporting.

    Outputs one JSON object per line with fields that GCP services
    understand:

    - ``severity``: mapped from Python level (Cloud Logging filter)
    - ``message``: includes stack trace for errors so Cloud Error
      Reporting can auto-group by trace
    - ``logging.googleapis.com/sourceLocation``: click-to-source in
      the GCP console
    - ``logging.googleapis.com/labels``: custom filterable dimensions
      (logger name, job_id)
    """

    _SEVERITY: ClassVar[dict[str, str]] = {
        "DEBUG": "DEBUG",
        "INFO": "INFO",
        "WARNING": "WARNING",
        "ERROR": "ERROR",
        "CRITICAL": "CRITICAL",
    }

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import UTC, datetime

        message = record.getMessage()

        # Cloud Error Reporting groups by stack trace in the message field
        if record.exc_info and record.exc_info[1] is not None:
            trace = self.formatException(record.exc_info)
            message = f"{message}\n{trace}"

        entry: dict[str, object] = {
            "severity": self._SEVERITY.get(record.levelname, "DEFAULT"),
            "message": message,
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "logging.googleapis.com/sourceLocation": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            },
        }

        # Custom labels for filtering in Cloud Logging
        labels: dict[str, str] = {"logger": record.name}
        if hasattr(record, "job_id") and record.job_id:
            labels["job_id"] = str(record.job_id)
        entry["logging.googleapis.com/labels"] = labels

        return json.dumps(entry, default=str)


_lock = threading.Lock()
_initialized = False
_tracer_provider: TracerProvider | None = None
_logger_provider: LoggerProvider | None = None


def init_telemetry(service_name: str) -> None:
    """Configure OpenTelemetry with DuckDB exporters.

    Safe to call multiple times -- only the first call takes effect.
    Uses DispatchingSpanProcessor/DispatchingLogProcessor to push SSE events
    immediately when telemetry is received, while batching DB writes.

    Respects _SHENAS_SKIP_TELEMETRY=1 to skip initialization (used by tests
    to prevent background exporter threads without disabling the OTel SDK).
    """
    import os

    global _initialized, _tracer_provider, _logger_provider
    with _lock:
        if _initialized:
            return
        _initialized = True

    if os.environ.get("_SHENAS_SKIP_TELEMETRY", "") == "1":
        return

    resource = Resource.create({"service.name": service_name})

    # Traces: dispatch SSE immediately, batch DB writes
    _tracer_provider = TracerProvider(resource=resource)
    _tracer_provider.add_span_processor(DispatchingSpanProcessor(BatchSpanProcessor(DuckDBSpanExporter())))
    trace.set_tracer_provider(_tracer_provider)

    # Logs: dispatch SSE immediately, batch DB writes
    _logger_provider = LoggerProvider(resource=resource)
    _logger_provider.add_log_record_processor(DispatchingLogProcessor(BatchLogRecordProcessor(DuckDBLogExporter())))
    handler = LoggingHandler(logger_provider=_logger_provider)
    shenas_logger = logging.getLogger("shenas")
    # Inject job_id from contextvar into every LogRecord so OTel exporters can persist it.
    shenas_logger.addFilter(JobIdLogFilter())
    shenas_logger.addHandler(handler)

    # Also log to stdout for visibility in terminal/container logs
    console = logging.StreamHandler()
    if os.environ.get("SHENAS_JSON_LOGS", "") == "1" or os.environ.get("SHENAS_HEADLESS", "") == "1":
        console.setFormatter(_CloudJsonFormatter())
    else:
        console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%H:%M:%S"))
    shenas_logger.addHandler(console)
    shenas_logger.setLevel(logging.DEBUG)

    atexit.register(shutdown_telemetry)


def shutdown_telemetry() -> None:
    """Flush and shut down all OTel providers. Called automatically at exit."""
    if _tracer_provider:
        _tracer_provider.shutdown()
    if _logger_provider:
        _logger_provider.shutdown()


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer from the global TracerProvider."""
    return trace.get_tracer(name)
