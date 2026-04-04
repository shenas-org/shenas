"""DuckDB schema for OpenTelemetry spans and logs."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import duckdb

CREATE_SPANS = """\
CREATE TABLE IF NOT EXISTS telemetry.spans (
    trace_id VARCHAR NOT NULL,
    span_id VARCHAR NOT NULL,
    parent_span_id VARCHAR,
    name VARCHAR NOT NULL,
    kind VARCHAR,
    service_name VARCHAR,
    status_code VARCHAR,
    status_message VARCHAR,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    duration_ms DOUBLE,
    attributes JSON,
    events JSON,
    PRIMARY KEY (trace_id, span_id)
)"""

CREATE_LOGS = """\
CREATE TABLE IF NOT EXISTS telemetry.logs (
    timestamp TIMESTAMP NOT NULL,
    trace_id VARCHAR,
    span_id VARCHAR,
    severity VARCHAR,
    body VARCHAR,
    attributes JSON,
    service_name VARCHAR
)"""


def ensure_telemetry_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create the telemetry schema and tables if they don't exist."""
    con.execute("CREATE SCHEMA IF NOT EXISTS telemetry")
    con.execute(CREATE_SPANS)
    con.execute(CREATE_LOGS)
