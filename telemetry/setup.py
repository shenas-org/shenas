"""Initialize OpenTelemetry with DuckDB exporters."""

from __future__ import annotations

import atexit
import logging
import threading

from opentelemetry import trace
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from telemetry.exporters import DuckDBLogExporter, DuckDBSpanExporter

_lock = threading.Lock()
_initialized = False
_tracer_provider: TracerProvider | None = None
_logger_provider: LoggerProvider | None = None


def init_telemetry(service_name: str) -> None:
    """Configure OpenTelemetry with DuckDB exporters.

    Safe to call multiple times -- only the first call takes effect.
    Attaches the log handler only to the 'shenas' logger hierarchy (not root)
    to avoid recursive writes from third-party libraries.
    """
    global _initialized, _tracer_provider, _logger_provider
    with _lock:
        if _initialized:
            return
        _initialized = True

    resource = Resource.create({"service.name": service_name})

    # Traces
    _tracer_provider = TracerProvider(resource=resource)
    _tracer_provider.add_span_processor(BatchSpanProcessor(DuckDBSpanExporter()))
    trace.set_tracer_provider(_tracer_provider)

    # Logs (bridge stdlib logging to OTel -> DuckDB)
    # Attach only to 'shenas' logger to prevent recursive writes from
    # third-party libraries (e.g. DuckDB, uvicorn, httpx logging to root
    # would trigger the exporter which writes to DuckDB which logs again).
    _logger_provider = LoggerProvider(resource=resource)
    _logger_provider.add_log_record_processor(BatchLogRecordProcessor(DuckDBLogExporter()))
    handler = LoggingHandler(logger_provider=_logger_provider)
    shenas_logger = logging.getLogger("shenas")
    shenas_logger.addHandler(handler)
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
