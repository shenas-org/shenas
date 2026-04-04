"""Tests for the OpenTelemetry DuckDB exporters."""

from unittest.mock import patch

import duckdb
import pytest
from opentelemetry.sdk._logs import LoggerProvider  # type: ignore[attr-defined]
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor  # type: ignore[attr-defined]
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from app.telemetry.exporters import DuckDBLogExporter, DuckDBSpanExporter
from app.telemetry.schema import ensure_telemetry_schema


@pytest.fixture
def con() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect(":memory:")
    ensure_telemetry_schema(c)
    return c


class _NonClosingWrapper:
    """Wraps a DuckDB connection but makes close() a no-op for testing."""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def close(self) -> None:
        pass

    def __getattr__(self, name: str):
        return getattr(self._con, name)


def _mock_connect(con: duckdb.DuckDBPyConnection):
    """Return a mock _connect that returns a non-closing wrapper around the test connection."""
    wrapper = _NonClosingWrapper(con)

    def factory() -> _NonClosingWrapper:
        return wrapper

    return factory


class TestSchema:
    def test_creates_tables(self, con: duckdb.DuckDBPyConnection) -> None:
        tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'telemetry'").fetchall()
        names = {r[0] for r in tables}
        assert "spans" in names
        assert "logs" in names

    def test_idempotent(self, con: duckdb.DuckDBPyConnection) -> None:
        ensure_telemetry_schema(con)
        ensure_telemetry_schema(con)
        tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'telemetry'").fetchall()
        assert len(tables) == 2


class TestSpanExporter:
    def test_exports_span(self, con: duckdb.DuckDBPyConnection) -> None:
        with patch("app.telemetry.exporters._connect", _mock_connect(con)):
            exporter = DuckDBSpanExporter()

            resource = Resource.create({"service.name": "test-service"})
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(SimpleSpanProcessor(exporter))
            tracer = provider.get_tracer("test")

            with tracer.start_as_current_span("test-operation", attributes={"key": "value"}):
                pass

            provider.force_flush()

        rows = con.execute("SELECT * FROM telemetry.spans").fetchall()
        assert len(rows) == 1
        row = con.execute("SELECT name, service_name, duration_ms FROM telemetry.spans").fetchone()
        assert row is not None
        assert row[0] == "test-operation"
        assert row[1] == "test-service"
        assert row[2] >= 0

    def test_exports_nested_spans(self, con: duckdb.DuckDBPyConnection) -> None:
        with patch("app.telemetry.exporters._connect", _mock_connect(con)):
            exporter = DuckDBSpanExporter()

            provider = TracerProvider(resource=Resource.create({"service.name": "test"}))
            provider.add_span_processor(SimpleSpanProcessor(exporter))
            tracer = provider.get_tracer("test")

            with tracer.start_as_current_span("parent"), tracer.start_as_current_span("child"):
                pass

            provider.force_flush()

        rows = con.execute("SELECT name, parent_span_id, trace_id FROM telemetry.spans ORDER BY name").fetchall()
        assert len(rows) == 2
        child_row = rows[0]
        parent_row = rows[1]
        assert child_row[0] == "child"
        assert parent_row[0] == "parent"
        assert child_row[2] == parent_row[2]
        assert child_row[1] is not None
        assert parent_row[1] is None

    def test_exports_attributes(self, con: duckdb.DuckDBPyConnection) -> None:
        with patch("app.telemetry.exporters._connect", _mock_connect(con)):
            exporter = DuckDBSpanExporter()

            provider = TracerProvider(resource=Resource.create({"service.name": "test"}))
            provider.add_span_processor(SimpleSpanProcessor(exporter))
            tracer = provider.get_tracer("test")

            with tracer.start_as_current_span("op", attributes={"pipe.name": "garmin", "rows": 42}):
                pass

            provider.force_flush()

        import json

        result = con.execute("SELECT attributes FROM telemetry.spans").fetchone()
        assert result is not None
        attrs = result[0]
        parsed = json.loads(attrs)
        assert parsed["pipe.name"] == "garmin"
        assert parsed["rows"] == 42

    def test_empty_batch(self, con: duckdb.DuckDBPyConnection) -> None:
        with patch("app.telemetry.exporters._connect", _mock_connect(con)):
            exporter = DuckDBSpanExporter()
            from opentelemetry.sdk.trace.export import SpanExportResult

            result = exporter.export([])
            assert result == SpanExportResult.SUCCESS


class TestLogExporter:
    def test_exports_log(self, con: duckdb.DuckDBPyConnection) -> None:
        import logging

        with patch("app.telemetry.exporters._connect", _mock_connect(con)):
            exporter = DuckDBLogExporter()

            resource = Resource.create({"service.name": "test-service"})
            provider = LoggerProvider(resource=resource)
            provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))

            from opentelemetry.sdk._logs import LoggingHandler

            handler = LoggingHandler(logger_provider=provider)
            logger = logging.getLogger("test.otel")
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

            logger.info("test log message")
            provider.force_flush()

            logger.removeHandler(handler)

        rows = con.execute("SELECT * FROM telemetry.logs").fetchall()
        assert len(rows) == 1
        row = con.execute("SELECT severity, body, service_name FROM telemetry.logs").fetchone()
        assert row is not None
        assert row[0] == "INFO"
        assert "test log message" in row[1]

    def test_log_with_trace_context(self, con: duckdb.DuckDBPyConnection) -> None:
        import logging

        with patch("app.telemetry.exporters._connect", _mock_connect(con)):
            span_exporter = DuckDBSpanExporter()
            log_exporter = DuckDBLogExporter()

            resource = Resource.create({"service.name": "test"})
            trace_provider = TracerProvider(resource=resource)
            trace_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
            log_provider = LoggerProvider(resource=resource)
            log_provider.add_log_record_processor(SimpleLogRecordProcessor(log_exporter))

            from opentelemetry.sdk._logs import LoggingHandler

            handler = LoggingHandler(logger_provider=log_provider)
            logger = logging.getLogger("test.context")
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

            tracer = trace_provider.get_tracer("test")
            with tracer.start_as_current_span("my-span"):
                logger.info("inside span")

            trace_provider.force_flush()
            log_provider.force_flush()

            logger.removeHandler(handler)

        span_row = con.execute("SELECT trace_id FROM telemetry.spans").fetchone()
        log_row = con.execute("SELECT trace_id, span_id FROM telemetry.logs").fetchone()
        assert span_row is not None
        assert log_row is not None
        assert log_row[0] == span_row[0]
        assert log_row[1] is not None

    def test_empty_batch(self, con: duckdb.DuckDBPyConnection) -> None:
        with patch("app.telemetry.exporters._connect", _mock_connect(con)):
            exporter = DuckDBLogExporter()
            from opentelemetry.sdk._logs.export import LogRecordExportResult  # type: ignore[attr-defined]

            result = exporter.export([])
            assert result == LogRecordExportResult.SUCCESS
