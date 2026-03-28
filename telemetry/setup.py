"""Initialize OpenTelemetry with DuckDB exporters."""

import logging

from opentelemetry import trace
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from telemetry.exporters import DuckDBLogExporter, DuckDBSpanExporter

_initialized = False


def init_telemetry(service_name: str) -> None:
    """Configure OpenTelemetry with DuckDB exporters.

    Safe to call multiple times -- only the first call takes effect.
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    resource = Resource.create({"service.name": service_name})

    # Traces
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(DuckDBSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    # Logs (bridge stdlib logging to OTel -> DuckDB)
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(DuckDBLogExporter()))
    handler = LoggingHandler(logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer from the global TracerProvider."""
    return trace.get_tracer(name)
