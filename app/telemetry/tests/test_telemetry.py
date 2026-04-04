"""Tests for the DuckDB OpenTelemetry exporters."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING
from unittest.mock import patch

import duckdb
import pytest
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from app.telemetry.exporters import DuckDBLogExporter, DuckDBSpanExporter
from app.telemetry.schema import ensure_telemetry_schema

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def con() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect(":memory:")
    ensure_telemetry_schema(c)
    return c


@contextmanager
def _mock_cursor(con: duckdb.DuckDBPyConnection) -> Iterator[duckdb.DuckDBPyConnection]:
    cur = con.cursor()
    try:
        yield cur
    finally:
        cur.close()


def _patches(con: duckdb.DuckDBPyConnection):
    """Return patches that route telemetry exporters to the in-memory DB."""
    import app.db  # ensure module is loaded before patching  # noqa: F401

    return (
        patch("app.db.cursor", lambda: _mock_cursor(con)),
        patch("app.telemetry.exporters._ensure_schema"),
        patch("app.telemetry.exporters._dispatch"),
    )


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
        with _patches(con)[0], _patches(con)[1], _patches(con)[2]:
            exporter = DuckDBSpanExporter()

            resource = Resource.create({"service.name": "test-service"})
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(SimpleSpanProcessor(exporter))
            tracer = provider.get_tracer("test")

            with tracer.start_as_current_span("test-operation", attributes={"key": "value"}):
                pass

            provider.shutdown()

        rows = con.execute("SELECT * FROM telemetry.spans").fetchall()
        assert len(rows) == 1
        assert rows[0][3] == "test-operation"

    def test_exports_nested_spans(self, con: duckdb.DuckDBPyConnection) -> None:
        with _patches(con)[0], _patches(con)[1], _patches(con)[2]:
            exporter = DuckDBSpanExporter()
            resource = Resource.create({"service.name": "test"})
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(SimpleSpanProcessor(exporter))
            tracer = provider.get_tracer("test")

            with tracer.start_as_current_span("parent"), tracer.start_as_current_span("child"):
                pass

            provider.shutdown()

        rows = con.execute("SELECT name, parent_span_id FROM telemetry.spans ORDER BY name").fetchall()
        assert len(rows) == 2
        child = next(r for r in rows if r[0] == "child")
        assert child[1] is not None

    def test_exports_attributes(self, con: duckdb.DuckDBPyConnection) -> None:
        with _patches(con)[0], _patches(con)[1], _patches(con)[2]:
            exporter = DuckDBSpanExporter()
            resource = Resource.create({"service.name": "test"})
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(SimpleSpanProcessor(exporter))
            tracer = provider.get_tracer("test")

            with tracer.start_as_current_span("op", attributes={"http.method": "GET", "http.url": "/api/test"}):
                pass

            provider.shutdown()

        rows = con.execute("SELECT attributes FROM telemetry.spans").fetchall()
        assert '"http.method": "GET"' in rows[0][0]

    def test_empty_batch(self, con: duckdb.DuckDBPyConnection) -> None:
        with _patches(con)[0], _patches(con)[1], _patches(con)[2]:
            exporter = DuckDBSpanExporter()
            from opentelemetry.sdk.trace.export import SpanExportResult

            result = exporter.export([])
            assert result == SpanExportResult.SUCCESS

        row = con.execute("SELECT COUNT(*) FROM telemetry.spans").fetchone()
        assert row is not None
        assert row[0] == 0


class TestLogExporter:
    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("opentelemetry.instrumentation.logging"),  # type: ignore[union-attr]
        reason="opentelemetry-instrumentation-logging not installed",
    )
    def test_exports_log(self, con: duckdb.DuckDBPyConnection) -> None:
        import logging

        with _patches(con)[0], _patches(con)[1], _patches(con)[2]:
            from opentelemetry._logs import set_logger_provider
            from opentelemetry.sdk._logs import LoggerProvider
            from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor

            exporter = DuckDBLogExporter()
            log_provider = LoggerProvider()
            log_provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
            set_logger_provider(log_provider)

            from opentelemetry.instrumentation.logging import LoggingInstrumentor

            LoggingInstrumentor().instrument(set_logging_format=False)

            logger = logging.getLogger("test.otel.log")
            logger.warning("test log message")

            log_provider.shutdown()
            LoggingInstrumentor().uninstrument()

        rows = con.execute("SELECT * FROM telemetry.logs").fetchall()
        assert len(rows) >= 1
        bodies = [r[4] for r in rows]
        assert any("test log message" in (b or "") for b in bodies)

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("opentelemetry.instrumentation.logging"),  # type: ignore[union-attr]
        reason="opentelemetry-instrumentation-logging not installed",
    )
    def test_log_with_trace_context(self, con: duckdb.DuckDBPyConnection) -> None:
        import logging

        with _patches(con)[0], _patches(con)[1], _patches(con)[2]:
            from opentelemetry._logs import set_logger_provider
            from opentelemetry.sdk._logs import LoggerProvider
            from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor

            exporter = DuckDBLogExporter()
            log_provider = LoggerProvider()
            log_provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
            set_logger_provider(log_provider)

            from opentelemetry.instrumentation.logging import LoggingInstrumentor

            LoggingInstrumentor().instrument(set_logging_format=False)

            resource = Resource.create({"service.name": "test"})
            tracer_provider = TracerProvider(resource=resource)
            tracer = tracer_provider.get_tracer("test")

            logger = logging.getLogger("test.otel.trace")
            with tracer.start_as_current_span("traced-op"):
                logger.info("log inside span")

            log_provider.shutdown()
            tracer_provider.shutdown()
            LoggingInstrumentor().uninstrument()

        rows = con.execute("SELECT trace_id, span_id, body FROM telemetry.logs").fetchall()
        traced = [r for r in rows if r[2] and "log inside span" in r[2]]
        assert len(traced) >= 1
        assert traced[0][0] is not None
        assert traced[0][1] is not None

    def test_empty_batch(self, con: duckdb.DuckDBPyConnection) -> None:
        with _patches(con)[0], _patches(con)[1], _patches(con)[2]:
            exporter = DuckDBLogExporter()
            result = exporter.export([])
            from opentelemetry.sdk._logs.export import LogRecordExportResult

            assert result == LogRecordExportResult.SUCCESS
