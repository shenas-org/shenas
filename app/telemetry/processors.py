"""Custom OTel processors that dispatch SSE events immediately.

Wraps a delegate processor (typically BatchSpanProcessor / BatchLogRecordProcessor)
for DB writes, while pushing real-time events to the SSE dispatcher on every emit.
"""

from __future__ import annotations

import json
from typing import Any

from opentelemetry.sdk._logs import LogRecordProcessor, ReadableLogRecord  # type: ignore[attr-defined]
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor


def _dispatch_span(span: ReadableSpan) -> None:
    """Push a single span to SSE subscribers."""
    from app.telemetry.dispatcher import notify
    from app.telemetry.exporters import _ns_to_iso

    try:
        ctx = span.get_span_context()
        parent = span.parent
        start_ns = span.start_time or 0
        end_ns = span.end_time or 0
        service_name = None
        if span.resource:
            service_name = span.resource.attributes.get("service.name")

        data = {
            "trace_id": format(ctx.trace_id, "032x"),
            "span_id": format(ctx.span_id, "016x"),
            "parent_span_id": format(parent.span_id, "032x") if parent else None,
            "name": span.name,
            "kind": span.kind.name if span.kind else None,
            "service_name": str(service_name) if service_name else None,
            "status_code": span.status.status_code.name if span.status else None,
            "start_time": _ns_to_iso(start_ns),
            "end_time": _ns_to_iso(end_ns),
            "duration_ms": (end_ns - start_ns) / 1e6,
            "attributes": json.dumps(dict(span.attributes), default=str) if span.attributes else None,
        }
        notify("span", [data])
    except Exception:
        pass


def _dispatch_log(record: ReadableLogRecord) -> None:
    """Push a single log record to SSE subscribers."""
    from datetime import UTC, datetime

    from app.telemetry.dispatcher import notify

    try:
        raw = json.loads(record.to_json())

        trace_id = raw.get("trace_id")
        if trace_id and trace_id.startswith("0x"):
            trace_id = trace_id[2:]
        if trace_id and all(c == "0" for c in trace_id):
            trace_id = None

        span_id = raw.get("span_id")
        if span_id and span_id.startswith("0x"):
            span_id = span_id[2:]
        if span_id and all(c == "0" for c in span_id):
            span_id = None

        ts = raw.get("timestamp") or datetime.now(UTC).isoformat()
        service_name = raw.get("resource", {}).get("attributes", {}).get("service.name")
        attributes = raw.get("attributes")

        data = {
            "timestamp": ts,
            "trace_id": trace_id,
            "span_id": span_id,
            "severity": raw.get("severity_text"),
            "body": raw.get("body"),
            "attributes": json.dumps(attributes, default=str) if attributes else None,
            "service_name": str(service_name) if service_name else None,
        }
        notify("log", [data])
    except Exception:
        pass


class DispatchingSpanProcessor(SpanProcessor):
    """Dispatches SSE events on span end, delegates to a wrapped processor for DB writes."""

    def __init__(self, delegate: SpanProcessor) -> None:
        self._delegate = delegate

    def on_start(self, span: Any, parent_context: Any = None) -> None:
        self._delegate.on_start(span, parent_context)

    def on_end(self, span: ReadableSpan) -> None:
        _dispatch_span(span)
        self._delegate.on_end(span)

    def shutdown(self) -> None:
        self._delegate.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self._delegate.force_flush(timeout_millis)


class DispatchingLogProcessor(LogRecordProcessor):
    """Dispatches SSE events on log emit, delegates to a wrapped processor for DB writes."""

    def __init__(self, delegate: LogRecordProcessor) -> None:
        self._delegate = delegate

    def emit(self, log_data: Any) -> None:
        _dispatch_log(log_data)
        if hasattr(self._delegate, "emit"):
            self._delegate.emit(log_data)  # ty: ignore[call-non-callable]

    def on_emit(self, log_data: Any) -> None:  # ty: ignore[invalid-method-override]
        _dispatch_log(log_data)
        if hasattr(self._delegate, "on_emit"):
            self._delegate.on_emit(log_data)

    def shutdown(self) -> None:
        self._delegate.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self._delegate.force_flush(timeout_millis)
