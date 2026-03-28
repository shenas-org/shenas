"""Custom OpenTelemetry exporters that write to DuckDB."""

import json
import logging
import threading
from datetime import datetime, timezone

import duckdb
from opentelemetry.sdk._logs.export import LogExporter, LogExportResult
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from telemetry.schema import ensure_telemetry_schema

# Dedicated logger that does NOT go through the OTel log bridge (only 'shenas.*'
# loggers are bridged in setup.py). This prevents recursive writes.
_logger = logging.getLogger("telemetry.exporters")

_SPAN_INSERT = """\
INSERT INTO telemetry.spans (
    trace_id, span_id, parent_span_id, name, kind, service_name,
    status_code, status_message, start_time, end_time, duration_ms,
    attributes, events
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

_LOG_INSERT = """\
INSERT INTO telemetry.logs (
    timestamp, trace_id, span_id, severity, body, attributes, service_name
) VALUES (?, ?, ?, ?, ?, ?, ?)"""


def _ns_to_iso(ns: int) -> str:
    secs, remainder = divmod(ns, 10**9)
    dt = datetime.fromtimestamp(secs, tz=timezone.utc).replace(microsecond=remainder // 1000)
    return dt.isoformat()


def _connect() -> duckdb.DuckDBPyConnection:
    from app.db import connect

    con = connect()
    ensure_telemetry_schema(con)
    return con


class DuckDBSpanExporter(SpanExporter):
    """Export OpenTelemetry spans to DuckDB telemetry.spans table."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:
        try:
            with self._lock:
                con = _connect()

                rows = []
                for span in spans:
                    ctx = span.get_span_context()
                    parent = span.parent
                    parent_id = format(parent.span_id, "032x") if parent else None
                    start_ns = span.start_time or 0
                    end_ns = span.end_time or 0
                    duration_ms = (end_ns - start_ns) / 1e6

                    service_name = None
                    if span.resource:
                        service_name = span.resource.attributes.get("service.name")

                    events_list = []
                    for event in span.events:
                        events_list.append(
                            {
                                "name": event.name,
                                "timestamp": _ns_to_iso(event.timestamp) if event.timestamp else None,
                                "attributes": dict(event.attributes) if event.attributes else {},
                            }
                        )

                    rows.append(
                        (
                            format(ctx.trace_id, "032x"),
                            format(ctx.span_id, "016x"),
                            parent_id,
                            span.name,
                            span.kind.name if span.kind else None,
                            str(service_name) if service_name else None,
                            span.status.status_code.name if span.status else None,
                            span.status.description if span.status else None,
                            _ns_to_iso(start_ns),
                            _ns_to_iso(end_ns),
                            duration_ms,
                            json.dumps(dict(span.attributes), default=str) if span.attributes else None,
                            json.dumps(events_list, default=str) if events_list else None,
                        )
                    )

                if rows:
                    con.executemany(_SPAN_INSERT, rows)
                con.close()
                return SpanExportResult.SUCCESS
        except Exception:
            _logger.warning("Failed to export spans to DuckDB", exc_info=True)
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        pass


class DuckDBLogExporter(LogExporter):
    """Export OpenTelemetry log records to DuckDB telemetry.logs table."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._exporting = threading.local()

    def export(self, batch) -> LogExportResult:  # noqa: ANN001
        # Recursion guard: if we're already inside an export call on this thread,
        # skip to prevent infinite loops (log -> export -> log -> export -> ...).
        if getattr(self._exporting, "active", False):
            return LogExportResult.SUCCESS
        self._exporting.active = True
        try:
            with self._lock:
                con = _connect()

                rows = []
                for record in batch:
                    data = json.loads(record.to_json())

                    trace_id = data.get("trace_id")
                    if trace_id and trace_id.startswith("0x"):
                        trace_id = trace_id[2:]
                    if trace_id and all(c == "0" for c in trace_id):
                        trace_id = None

                    span_id = data.get("span_id")
                    if span_id and span_id.startswith("0x"):
                        span_id = span_id[2:]
                    if span_id and all(c == "0" for c in span_id):
                        span_id = None

                    ts = data.get("timestamp") or datetime.now(timezone.utc).isoformat()
                    service_name = data.get("resource", {}).get("attributes", {}).get("service.name")
                    attributes = data.get("attributes")

                    rows.append(
                        (
                            ts,
                            trace_id,
                            span_id,
                            data.get("severity_text"),
                            data.get("body"),
                            json.dumps(attributes, default=str) if attributes else None,
                            str(service_name) if service_name else None,
                        )
                    )

                if rows:
                    con.executemany(_LOG_INSERT, rows)
                con.close()
                return LogExportResult.SUCCESS
        except Exception:
            _logger.warning("Failed to export logs to DuckDB", exc_info=True)
            return LogExportResult.FAILURE
        finally:
            self._exporting.active = False

    def shutdown(self) -> None:
        pass
